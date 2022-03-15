import logging
from kubernetes import client

logger = logging.getLogger(__name__)


def get_current_namespace():
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read()
    except IOError as e:
        logger.debug("Could not open namespace secret file: {0}".format(e))
        return None


def dump_pod_logs(pod_name:str, pod_namespace:str, filename:str)->int:
    """
    writes the contents of the given pod logs to a file at filename.
    can raise exceptions if either the read or write operations fail
    :param pod_name: pod name whose logs to dump
    :param pod_namespace: namespace the pod is in
    :param filename: name of the file to write to
    :return: number of bytes written
    """
    corev1 = client.CoreV1Api()

    with open(filename, "w") as f:
        log_content = corev1.read_namespaced_pod_log(pod_name, pod_namespace)
        logger.debug("Downloaded {0} bytes of log data from {1} in {2}".format(len(log_content), pod_name, pod_namespace))
        return f.write(log_content)
