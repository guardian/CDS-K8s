import os

from .UploadRequestedProcessor import UploadRequestedProcessor
from .K8MessageProcessor import K8MessageProcessor

##This structure is imported by name in the run_rabbitmq_responder
EXCHANGE_MAPPINGS = [
    {
        "exchange": 'pluto-deliverables',
        "handler": UploadRequestedProcessor(),
    },
    {
        "exchange": 'cdsresponder',
        "handler": K8MessageProcessor(os.getenv("NAMESPACE")),
    }
]
