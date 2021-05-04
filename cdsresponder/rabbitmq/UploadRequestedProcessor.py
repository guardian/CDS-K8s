from .messageprocessor import MessageProcessor
import logging

logger = logging.getLogger(__name__)


class UploadRequestedProcessor(MessageProcessor):
    routing_key = "deliverables.syndication.*.upload"
    schema = {
        "type": "object",
        "properties": {
            "deliverable_asset": {
                "type": "integer"
            },
            "deliverable_bundle": {
                "type": "integer"
            },
            "online_id": {
                "type": "string"
            },
            "nearline_id": {
                "type": "string"
            },
            "archive_id": {
                "type": "string"
            },
            "inmeta": {
                "type": "string"
            },
            "routename": {
                "type": "string"
            }
        },
        "required": ["inmeta","routename"]
    }

    def valid_message_receive(self, exchange_name, routing_key, delivery_tag, body):
        logger.info("Received upload request from {0} with key {1} and delivery tag {2}".format(exchange_name, routing_key, delivery_tag))