from .messageprocessor import MessageProcessor
import logging
import lxml.etree as xml
import os
import pathlib
import random
import string
from cds.cds_launcher import CDSLauncher

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
            "filename": {
                "type": "string"
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

    def __init__(self):
        self.xsd_validator = xml.XMLSchema(file=UploadRequestedProcessor.find_inmeta_xsd())
        self.launcher = CDSLauncher(os.getenv("NAMESPACE")) #NAMESPACE arg is only used if we are not in-cluster

    @staticmethod
    def find_inmeta_xsd():
        from_config = os.getenv("INMETA_XSD")
        if from_config is not None:
            return from_config

        return os.path.join(
            pathlib.Path(__file__).parent.parent.absolute(),
            "inmeta.xsd"
        )

    def validate_inmeta(self, content:str)->bool:
        try:
            parsed_xml = xml.fromstring(content)
            return self.xsd_validator.validate(parsed_xml)
        except xml.ParseError as e:
            logger.error("Incoming inmeta data did not parse as XML: {}".format(str(e)),e)
            return False

    def build_filename(self, path:str, filename_hint:str)->str:
        initial_filename = os.path.join(path, filename_hint + ".inmeta")
        if not os.path.exists(initial_filename):
            return initial_filename

        i=1
        while True:
            test_filename = os.path.join(path, filename_hint + str(i) + ".inmeta")
            if not os.path.exists(test_filename):
                return test_filename
            if i>=1000:
                logger.error("Reached 1,000 iterations and the file {0} still exists, something must have gone wrong".format(test_filename))
                raise RuntimeError("Could not build target filename")

    def write_out_inmeta(self, filename_hint:str, content:str)->str:
        basepath = os.getenv("INMETA_PATH")
        if basepath is None:
            logger.error("INMETA_PATH is not set, can't output content")
            raise RuntimeError("INMETA_PATH was not set")

        without_extensions = filename_hint.split(".")
        if len(without_extensions)==0:
            logger.error("Incoming filename '{0}' appears blank".format(filename_hint))
            raise RuntimeError("Could not build target filename")

        target_filename = self.build_filename(basepath, without_extensions[0])
        logger.info("Writing inmeta content to {0}".format(filename_hint))
        with open(target_filename, "w") as f:
            f.write(content)
        return target_filename

    @staticmethod
    def randomstring(length:int)->str:
        letters = string.ascii_letters + string.digits
        return "".join(random.choice(letters) for i in range(length))

    def valid_message_receive(self, exchange_name:str, routing_key:str, delivery_tag:str, body:dict):
        logger.info("Received upload request from {0} with key {1} and delivery tag {2}".format(exchange_name, routing_key, delivery_tag))

        if not self.validate_inmeta(body["inmeta"]):
            logger.error("Offending content was {0}".format(body["inmeta"]))
            raise MessageProcessor.NackMessage

        if "filename" in body:
            filename_hint = body["filename"]
        elif "online_id" in body:
            filename_hint = body["online_id"]
        elif "nearline_id" in body:
            filename_hint = body["nearline_id"]
        elif "archive_id" in body:
            filename_hint = body["archive_id"]
        else:
            filename_hint = self.randomstring(10)

        inmeta_file = self.write_out_inmeta(filename_hint, body["inmeta"])

        try:
            self.launcher.launch_cds_job(inmeta_file, "cds-{0}-{1}".format(filename_hint, self.randomstring(4)), body["route"])
        except Exception as e:
            logger.error("Could not launch job: {0}".format(str(e)))
            raise self.NackWithRetry
