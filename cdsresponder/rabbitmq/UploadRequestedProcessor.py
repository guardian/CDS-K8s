from .messageprocessor import MessageProcessor
import logging
import lxml.etree as xml
import os
import pathlib
import random
import string
import pika
import traceback
import re
logger = logging.getLogger(__name__)


class UploadRequestedProcessor(MessageProcessor):
    my_exchange = "cdsresponder"
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
                "type": ["string","null"]
            },
            "online_id": {
                "type": ["string","null"]
            },
            "nearline_id": {
                "type": ["string","null"]
            },
            "archive_id": {
                "type": ["string","null"]
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
        from cds.cds_launcher import CDSLauncher    #imported here so that it can be patched out during testing
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
            logger.error("Incoming inmeta data did not parse as XML: {0}".format(str(e)))
            return False

    def build_filename(self, path:str, filename_hint:str)->str:
        initial_filename = os.path.join(path, filename_hint + ".inmeta")
        if not os.path.exists(initial_filename):
            return initial_filename

        i=1
        while True:
            test_filename = os.path.join(path, filename_hint + "-" + str(i) + ".inmeta")
            if not os.path.exists(test_filename):
                return test_filename
            i+=1
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

    def inform_job_status(self, channel: pika.channel.Channel, status: str, body: dict):
        import json
        channel.basic_publish(
            exchange=self.my_exchange,
            routing_key="cds.job.{0}".format(status),
            body=json.dumps(body),
            mandatory=True
        )

    sanitizer = re.compile(r'[^A-Za-z0-9\-_.]')

    @staticmethod
    def make_safe_label(content:str)->str:
        """
        kubernetes labels can't be longer than 63 chars or contain anything non-alphanumeric, _ - and .
        :param content: string to sanitise
        :return: sanitised string
        """
        sanitised = UploadRequestedProcessor.sanitizer.sub("", content)
        if len(sanitised)<63:
            return sanitised
        else:
            abbreviated=sanitised[0:60]
            return abbreviated+"..."

    def valid_message_receive(self, channel: pika.channel.Channel, exchange_name:str, routing_key:str, delivery_tag:str, body:dict):
        logger.info("Received upload request from {0} with key {1} and delivery tag {2}".format(exchange_name, routing_key, delivery_tag))

        if not self.validate_inmeta(body["inmeta"]):
            logger.error("inmeta term did not validate as an xml inmeta document: {0}".format(self.xsd_validator.error_log))
            logger.error("Offending content was {0}".format(body["inmeta"]))
            body["error"] = self.xsd_validator.error_log
            self.inform_job_status(channel, "invalid", body)
            raise MessageProcessor.NackMessage

        if "filename" in body and body["filename"] is not None:
            filename_hint = body["filename"]
        elif "online_id" in body and body["online_id"] is not None:
            filename_hint = body["online_id"]
        elif "nearline_id" in body and body["nearline_id"] is not None:
            filename_hint = body["nearline_id"]
        elif "archive_id" in body and body["archive_id"] is not None:
            filename_hint = body["archive_id"]
        else:
            filename_hint = self.randomstring(10)

        labels = {
            "deliverable-asset-id": str(body["deliverable_asset"]) if "deliverable_asset" in body else "None",
            "deliverable-bundle-id": str(body["deliverable_bundle"]) if "deliverable_bundle" in body else "None",
            "online-id": self.make_safe_label(str(body["online_id"])) if "online_id" in body else "None",
            "nearline-id": self.make_safe_label(str(body["nearline_id"])) if "nearline_id" in body else "None",
            "archive-id": self.make_safe_label(str(body["archive_id"])) if "archive_id" in body else "None",
        }

        inmeta_file = self.write_out_inmeta(self.launcher.sanitise_job_name(filename_hint), body["inmeta"])
        job_name = "cds-{0}-{1}".format(filename_hint, self.randomstring(4))
        try:
            result = self.launcher.launch_cds_job(inmeta_file, job_name, body["routename"], labels)
            body["job-id"] = result.metadata.uid
            body["job-name"] = result.metadata.name
            body["job-namespace"] = result.metadata.namespace
        except Exception as e:
            logger.error("Could not launch job for {0}: {1}".format(body, str(e)))
            os.remove(inmeta_file)
            try:
                body["job-name"] = job_name
                body["error"] = str(e)
                body["traceback"] = traceback.format_exc()
                self.inform_job_status(channel, "invalid", body)
            except Exception as e:
                logger.error("Could not inform exchange of job failure: {0}".format(e))
            raise MessageProcessor.NackMessage

        try:
            self.inform_job_status(channel, "started", body)
        except Exception as e:
            logger.error("Job started but could not inform exchange: {0}".format(e))
            raise MessageProcessor.NackMessage
