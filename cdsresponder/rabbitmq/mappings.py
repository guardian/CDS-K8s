from .UploadRequestedProcessor import UploadRequestedProcessor

##This structure is imported by name in the run_rabbitmq_responder
EXCHANGE_MAPPINGS = [
    {
        "exchange": 'pluto-deliverables',
        "handler": UploadRequestedProcessor(),
    },
]
