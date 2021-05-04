from kubernetes import client, config
import logging
from hikaru import load_full_yaml, Job, get_json
import pathlib
import os

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
        self.namespace = self.get_current_namespace()
        if self.namespace is None and namespace is not None:
            logger.info("Not running in cluster, falling back to configured namespace {0}", namespace)
            self.namespace = namespace
        elif self.namespace is None and namespace is None:
            logger.error("If we are not running in a cluster you must specify a namespace within which to start jobs")
            raise ValueError("No namespace configured")

    def get_current_namespace(self):
        try:
            with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
                return f.read()
        except IOError as e:
            logger.debug("Could not open namespace secret file: {0}".format(e))
            return None

    def load_job_template(self):
        filepath = os.path.join(pathlib.Path(__name__).parent.absolute(), "templates","cdsjob.yaml")
        if os.path.exists(filepath):
            return filepath
        filepath = os.path.join(os.getenv("TEMPLATES_PATH"), "cdsjob.yaml")
        if os.path.exists(filepath):
            return filepath
        filepath = "/etc/cdsresponder/templates/cdsjob.yaml"
        if os.path.exists(filepath):
            return filepath
        raise RuntimeError("No path to cdsjob could be found")

    def build_job_doc(self, job_name:str, cmd:list,):
        content_template = self.load_job_template()
        if not isinstance(content_template, Job):
            raise TypeError("cdsjob template must be for a Job!")

        content_template.metadata.name=job_name
        content_template.spec.template.spec.containers[0].command = cmd
        return get_json(content_template)

    def launch_cds_job(self, inmeta_path:str, job_name:str, route_name:str):
        command_parts = [
            "/usr/local/bin/cds_run.pl",
            "--input-inmeta",
            inmeta_path,
            "--route",
            route_name
        ]
        jobdoc = self.build_job_doc(job_name, command_parts)
        logger.debug("Built job doc for submission: {0}".format(jobdoc))
        self.batch.create_namespaced_job(
            body=jobdoc,
            namespace=self.namespace
        )
