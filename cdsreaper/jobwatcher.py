from kubernetes import client, config, watch
import kubernetes.client.exceptions
from kubernetes.client.models.v1_job import V1Job
from kubernetes.client.models.v1_job_status import V1JobStatus
from kubernetes.client.models.v1_job_condition import V1JobCondition
from kubernetes.client.models.v1_job_list import V1JobList
from messagesender import MessageSender
from journal import Journal

import sys
from models import *

logger = logging.getLogger(__name__)


class JobWatcher(object):
    def __init__(self, api_client: client.BatchV1Api, sender: MessageSender, journal: Journal, namespace: str):
        self._batchv1 = api_client
        self._namespace = namespace
        self._sender = sender
        self._journal = journal

    @staticmethod
    def job_is_starting(s: V1JobStatus)->bool:
        """
        returns true if the given job is just starting up, i.e. it has a blank start_time, succeeded and failed counts
        :param s: V1JobStatus object to be interrogated
        :return: boolean
        """
        return s.start_time is None and s.active is None and s.failed is None and s.succeeded is None

    @staticmethod
    def job_is_running(s: V1JobStatus)->bool:
        """
        returns true if the given job has more than one active pod, i.e. it is running now
        :param s: V1JobStatus object to be interrogated
        :return: boolean
        """
        return s.active is not None and s.active>0 and (s.failed is None or s.failed==0)

    @staticmethod
    def job_is_retry(s: V1JobStatus)->bool:
        """
        returns true if the given job is retrying, i.e. it's active and has at least one failure
        :param s:
        :return:
        """
        return s.active is not None and s.active>0 and s.failed>0

    @staticmethod
    def job_is_failed(s:V1JobStatus)->bool:
        """
        returns true if the given job is NOT running and it has no successful completions
        :param s: V1JobStatus object to be interrogated
        :return: boolean
        """
        return (s.active is None or s.active==0) and (s.succeeded is None or s.succeeded==0) and s.start_time is not None

    @staticmethod
    def job_is_success(s:V1JobStatus)->bool:
        """
        returns true if the given job is NOT running and it has successful completions
        :param s: V1JobStatus object to be interrogated
        :return: boolean
        """
        return (s.active is None or s.active==0) and (s.succeeded is not None and s.succeeded>0)

    @staticmethod
    def get_job_status_string(j:V1Job)->str:
        logger.debug("Current job status dump: {0}".format(j.status))

        if JobWatcher.job_is_running(j.status):
            return "running"
        elif JobWatcher.job_is_retry(j.status):
            return "retry"
        elif JobWatcher.job_is_starting(j.status):
            return "starting"
        elif JobWatcher.job_is_failed(j.status):
            return "failed"
        elif JobWatcher.job_is_success(j.status):
            return "success"

    @staticmethod
    def get_most_recent_condition(conditions:list) -> V1JobCondition:
        if len(conditions)==0:
            return None

        sorted_conditions = sorted(conditions, key=lambda c: c.last_probe_time, reverse=True)
        return sorted_conditions[0]

    @staticmethod
    def get_job_failure_reason(s: V1JobStatus) -> str:
        maybe_cond = JobWatcher.get_most_recent_condition(s.conditions)
        if maybe_cond is None:
            return "Unknown"

        return "{0} - {1}".format(maybe_cond.reason, maybe_cond.message)

    def check_job(self, j:V1Job):
        status = self.get_job_status_string(j)
        logger.info("Job {0} ({1}) is in status {2}".format(j.metadata.name, j.metadata.uid, status))
        routing_key = "cds.job.{0}".format(status)
        message_body = {
            "job-id": j.metadata.uid,
            "job-name": j.metadata.name,
            "job-namespace": j.metadata.namespace,
            "retry-count": j.status.failed if j.status.failed is not None else 0
        }

        if status=="failed":
            message_body["failure-reason"] = JobWatcher.get_job_failure_reason(j.status)

        return self._sender.notify(routing_key, message_body)

    def _watcher(self):
        """
        internal method, forming the job watcher loop. Does not return.
        :return:
        """
        watcher = watch.Watch()

        resource_version = self._journal.get_most_recent_event()
        if resource_version is None:
            logger.info("Could not find a journalled resource version to start watch at, starting from most recent")
            initial_status:V1JobList = self._batchv1.list_namespaced_job(self._namespace)
            resource_version = initial_status.metadata.resource_version

        logger.info("Initiating job watch at resource version {0}".format(resource_version))

        try:
            for event in watcher.stream(self._batchv1.list_namespaced_job,
                                        self._namespace,
                                        resource_version=resource_version):
                logger.debug("Received job event: {0}".format(event['type']))
                if isinstance(event["object"], V1Job):
                    if not event["object"].metadata.name.startswith("cds-"):
                        logger.info("Job {0} is not a cds job, ignoring".format(event["object"].metadata.name))
                        continue
                    if event["type"]=="DELETED":
                        # we are not interested in the job object being deleted,
                        # it will have already been registered as succeeded/failed at this point.
                        continue

                    self.check_job(event["object"])
                    self._journal.record_processed(event["object"].metadata.resource_version)
                else:
                    logger.warning("received notification with unexpected type {0}".format(type(event["object"])))

        except kubernetes.client.exceptions.ApiException as err:
            logger.warning("Could not watch resource: cluster said {0}".format(str(err)))
            if err.status==410:
                logger.warning("Restarting from the most recent event")
                self._journal.clear_journal()
                return self._watcher()
            else:
                logger.error("Can't recover from {0} error".format(err.status))
                raise

    def run_sync(self):
        """
        runs the job watcher synchronously. Does not return.
        :return:
        """
        try:
            self._watcher()
        except Exception as e:
            logger.exception("Could not run the watcher: {0}".format(e))
            sys.exit(2)
