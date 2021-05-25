from kubernetes import client, config
import kubernetes.client.models
import logging
from hikaru import load_full_yaml, Job, get_clean_dict
import pathlib
import os
import re
from k8s.k8utils import get_current_namespace

logger = logging.getLogger(__name__)


class NotInCluster(Exception):
    pass


class CDSLauncher(object):
    def __init__(self, namespace:str):
        try:
            config.load_incluster_config()
        except config.config_exception.ConfigException as e:
            kube_config_file = os.getenv("KUBE_CONFIG", os.path.join(os.getenv("HOME"), ".kube", "config"))
            logger.warning("Could not load in-cluster configuration: {0}. Trying external connection from {1}...".format(str(e), kube_config_file))
            config.load_kube_config(kube_config_file)

        self.batch = client.BatchV1Api()
        self.namespace = get_current_namespace()
        if self.namespace is None and namespace is not None:
            logger.info("Not running in cluster, falling back to configured namespace {0}", namespace)
            self.namespace = namespace
        elif self.namespace is None and namespace is None:
            logger.error("If we are not running in a cluster you must specify a namespace within which to start jobs")
            raise ValueError("No namespace configured")
        logger.info("Startup - we are in namespace {0}".format(self.namespace))

    def find_job_template(self):
        filepath = os.path.join(os.getenv("TEMPLATES_PATH"), "cdsjob.yaml")
        if os.path.exists(filepath):
            return filepath
        filepath = os.path.join(pathlib.Path(__name__).parent.absolute(), "templates","cdsjob.yaml")
        if os.path.exists(filepath):
            return filepath
        filepath = "/etc/cdsresponder/templates/cdsjob.yaml"
        if os.path.exists(filepath):
            return filepath
        raise RuntimeError("No path to cdsjob could be found")

    def load_job_template(self):
        filepath = self.find_job_template()
        logger.debug("Loading job template from {0}".format(filepath))
        loaded = load_full_yaml(filepath)
        if len(loaded)==0:
            raise ValueError("Nothing was defined in cdsjob.yaml")
        jobs = [x for x in loaded if isinstance(x, Job)]
        if len(jobs)==0:
            raise ValueError("Of {0} objects defined in cdsjob.yaml, none of them was a Job".format(len(loaded)))
        return jobs[0]

    def build_job_doc(self, job_name:str, cmd:list, labels:dict):
        content_template = self.load_job_template()
        if not isinstance(content_template, Job):
            raise TypeError("cdsjob template must be for a Job, we got a {0}!".format(content_template.__class__.__name__))

        content_template.metadata.name = self.sanitise_job_name(job_name)
        content_template.spec.template.spec.containers[0].command = cmd
        existing_labels = content_template.metadata.labels
        if existing_labels is None:
            existing_labels = {}
        existing_labels.update(labels)
        content_template.metadata.labels = existing_labels

        return get_clean_dict(content_template)

    @staticmethod
    def sanitise_job_name(job_name:str) -> str:
        first_sub = re.sub(r"\s+","-", job_name)
        second_sub = re.sub(r'[^A-Za-z0-9-]', "", first_sub).lower()
        if len(second_sub) <= 59:   #kubernetes name length is 63 chars, we prepend "cds-" so take that off
            return second_sub
        else:
            return second_sub[0:59]

    def launch_cds_job(self, inmeta_path: str, job_name: str, route_name: str, labels:dict) -> kubernetes.client.models.V1Job:
        command_parts = [
            "/usr/local/bin/cds_run.pl",
            "--input-inmeta",
            inmeta_path,
            "--route",
            route_name
        ]
        jobdoc = self.build_job_doc(job_name, command_parts, labels)
        logger.debug("Built job doc for submission: {0}".format(jobdoc))
        return self.batch.create_namespaced_job(
            body=jobdoc,
            namespace=self.namespace
        )
