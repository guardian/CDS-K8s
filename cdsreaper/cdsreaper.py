#!/usr/bin/env python
import kubernetes
import os
import logging
from jobwatcher import JobWatcher
import sys
from messagesender import MessageSender
import pika

logging.basicConfig(format="{asctime} {name}|{funcName} [{levelname}] {message}",level=logging.DEBUG,style='{')
pikaLogger = logging.getLogger("pika")
pikaLogger.level=logging.WARN
logger = logging.getLogger(__name__)


def init_k8s_client():
    try:
        kubernetes.config.load_incluster_config()
    except kubernetes.config.config_exception.ConfigException as e:
        kube_config_file = os.getenv("KUBE_CONFIG", os.path.join(os.getenv("HOME"), ".kube", "config"))
        logger.warning("Could not load in-cluster configuration: {0}. Trying external connection from {1}...".format(str(e), kube_config_file))
        kubernetes.config.load_kube_config(kube_config_file)


def get_current_namespace():
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read()
    except IOError as e:
        logger.debug("Could not open namespace secret file: {0}".format(e))
        return None

#
# def init_redis_client():
#     return redis.Redis(host=os.getenv("REDIS_HOST"),
#                        port=int(os.getenv("REDIS_PORT",6379)),
#                        db=int(os.getenv("REDIS_DB_NUM", 0))
#                        )


if __name__ == "__main__":
    init_k8s_client()

    namespace = get_current_namespace()
    if namespace is None:
        namespace = os.getenv("NAMESPACE")

    if namespace is None:
        logger.error("Could not determine namespace from inside cluster, and NAMESPACE was not set in the environment")
        sys.exit(1)

    logger.info("CDSReaper started up, namespace is '{0}'".format(namespace))

    rmq_setup = pika.connection.ConnectionParameters(
        host=os.environ.get("RABBITMQ_HOST"),
        port=int(os.environ.get("RABBITMQ_PORT", 5672)),
        virtual_host=os.environ.get("RABBITMQ_VHOST", "/"),
        credentials=pika.PlainCredentials(username=os.environ.get("RABBITMQ_USER"), password=os.environ.get("RABBITMQ_PASSWD")),
        connection_attempts=int(os.environ.get("RABBITMQ_CONNECTION_ATTEMPTS", 3)),
        retry_delay=int(os.environ.get("RABBITMQ_RETRY_DELAY", 3))
    )

    sender = MessageSender(rmq_setup, os.environ.get("MY_EXCHANGE", "cdsresponder"))

    job_watcher = JobWatcher(kubernetes.client.BatchV1Api(), sender, namespace)
    job_watcher.run_sync()
