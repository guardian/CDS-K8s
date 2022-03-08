from .messageprocessor import MessageProcessor
import pika
from typing import Optional, List
import logging
from kubernetes import client, config
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_list import V1PodList
import os
import k8s.k8utils
import pathlib

logger = logging.getLogger(__name__)


class K8Message(object):
    schema = {
        "type": "object",
        "properties": {
            "job-id": {"type": "string"},
            "job-name": {"type": "string"},
            "job-namespace": {"type": "string"},
            "retry-count": {"type": "number"},
            "failure-reason": {"type": "string"}
        },
        "required": ["job-id","job-name","job-namespace"]
    }

    def __init__(self, source:dict):
        self._content = source

    @property
    def job_id(self)->str:
        return self._content["job-id"]

    @property
    def job_name(self)->str:
        return self._content["job-name"]

    @property
    def job_namespace(self)->str:
        return self._content["job-namespace"]

    @property
    def retry_count(self)->Optional[int]:
        value = self._content["retry-count"]
        if value is not None:
            try:
                return int(value)
            except ValueError:
                logger.warning("invalid retry count data '{0}' is not a number".format(value))
                return None
        else:
            return None

    @property
    def failure_reason(self)->Optional[str]:
        return self._content["failure-reason"]


class K8MessageProcessor(MessageProcessor):
    schema = K8Message.schema
    routing_key = "cds.job.*"
    pod_log_basepath = os.getenv("POD_LOGS_BASEPATH")   #if this is not set then no pod logs will be written
    pod_names_basepath = os.getenv("POD_NAMES_BASEPATH")

    @staticmethod
    def get_should_keep_jobs():
        value = os.getenv("KEEP_JOBS")
        if value is None or value.lower()=="false" or value.lower()=="no":
            return False
        elif value.lower()=="true" or value.lower()=="yes":
            return True
        else:
            raise ValueError("You must set KEEP_JOBS to either 'yes' or 'no'. Remember to quote these strings in a yaml document.")

    def __init__(self, namespace:str):
        try:
            config.load_incluster_config()
        except config.config_exception.ConfigException as e:
            kube_config_file = os.getenv("KUBE_CONFIG", os.path.join(os.getenv("HOME"), ".kube", "config"))
            logger.warning("Could not load in-cluster configuration: {0}. Trying external connection from {1}...".format(str(e), kube_config_file))
            config.load_kube_config(kube_config_file)

        self.should_keep_jobs = self.get_should_keep_jobs()
        self.batch = client.BatchV1Api()
        self.k8core = client.CoreV1Api()
        self.namespace = k8s.k8utils.get_current_namespace()
        if self.namespace is None and namespace is not None:
            logger.info("Not running in cluster, falling back to configured namespace {0}", namespace)
            self.namespace = namespace
        elif self.namespace is None and namespace is None:
            logger.error("If we are not running in a cluster you must specify a namespace within which to start jobs")
            raise ValueError("No namespace configured")
        logger.info("Startup - we are in namespace {0}".format(self.namespace))

    def read_logs(self, job_name:str, job_namespace:str, job_id:str)->int:
        if self.pod_log_basepath is None:
            logger.warning("If you want pod logs to be saved, then you must set POD_LOGS_BASEPATH to a valid writable filepath")
            return 0

        pod_list:V1PodList = self.k8core.list_namespaced_pod(job_namespace, label_selector="job-name={0}".format(job_name))

        # ensure path exists
        destpath = os.path.join(self.pod_log_basepath, job_name)
        pathlib.Path(destpath).mkdir(parents=True, exist_ok=True)

        for pod in pod_list.items:
            filename = os.path.join(self.pod_log_basepath, job_name, pod.metadata.name + ".log")
            k8s.k8utils.dump_pod_logs(pod.metadata.name, pod.metadata.namespace, filename)
            name_filename = os.path.join(self.pod_names_basepath, job_id + ".txt")
            k8s.k8utils.write_pod_name(pod.metadata.name, name_filename)

        return len(pod_list.items)

    def safe_delete_job(self, job_name:str, job_namespace:str):
        try:
            self.batch.delete_namespaced_job(job_name, job_namespace, propagation_policy='Foreground')
        except Exception as e:
            logger.error("Could not remove the job {0} from namespace {1}: {2}".format(job_name, job_namespace, str(e)))

    def valid_message_receive(self, channel: pika.spec.Channel, exchange_name, routing_key, delivery_tag, body):
            msg = K8Message(body)

            logger.debug("Got a {0} message for job {1} ({2}) from exchange {3}".format(routing_key, msg.job_name, msg.job_id, exchange_name))

            if routing_key == "cds.job.failed" or routing_key == "cds.job.success":
                try:
                    saved_logs = self.read_logs(msg.job_name, msg.job_namespace, msg.job_id)
                    logger.info("Job {0} terminated, saved {1} pod logs".format(msg.job_name, saved_logs))
                except Exception as e:
                    logger.error("Could not save job logs for {0}: {1}".format(msg.job_name, str(e)), exc_info=e)

                if self.should_keep_jobs:
                    logger.info("Retaining job information {0} in cluster as KEEP_JOBS is set to 'true' or 'yes'. Remove it or set to 'no' in order to remove completed jobs.")
                else:
                    logger.info("Removing completed job {0}...".format(msg.job_name))
                    self.safe_delete_job(msg.job_name, msg.job_namespace)
            else:
                logger.info("Job {0} is in progress".format(msg.job_name))