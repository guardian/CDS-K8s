import os
from unittest import TestCase
from unittest.mock import MagicMock, patch
import logging
import pathlib
import pika

import cds.cds_launcher

logging.basicConfig(level=logging.FATAL)


class TestUploadRequestedProcessor(TestCase):
    def test_find_inmeta_xsd_environ(self):
        """
        find_inmeta_xsd should return a value preset in the environment if it exists
        :return:
        """
        from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
        os.environ["INMETA_XSD"] = "path/to/some/file"
        self.assertEqual(UploadRequestedProcessor.find_inmeta_xsd(), "path/to/some/file")
        del os.environ["INMETA_XSD"]

    def test_find_inmeta_xsd(self):
        """
        find_inmeta_xsd should return path within the source bundle to the xsd file
        :return:
        """
        from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
        bundle_path = pathlib.Path(__file__).parent.parent
        expected_path = os.path.join(bundle_path, "inmeta.xsd")
        self.assertEqual(expected_path, UploadRequestedProcessor.find_inmeta_xsd())

    def test_validate_inmeta_valid(self):
        """
        validate_inmeta should return true for a valid document
        :return:
        """
        mocked_launcher = MagicMock(target=cds.cds_launcher.CDSLauncher)
        testdoc = """<?xml version="1.0"?>
        <meta-data><meta-group type="movie meta"><meta name="itemId" value="VX-1234"/></meta-group></meta-data>"""

        with patch("cds.cds_launcher.CDSLauncher", return_value=mocked_launcher):
            from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
            to_test = UploadRequestedProcessor()
            self.assertTrue(to_test.validate_inmeta(testdoc))

    def test_validate_inmeta_invalid(self):
        """
        validate_inmeta should return false for an invalid document
        :return:
        """
        mocked_launcher = MagicMock(target=cds.cds_launcher.CDSLauncher)
        testdoc = """<?xml version="1.0"?>
            <meta-data><meta-group type="movie meta"><meta name="itemId" vilue="VX-1234"/></meta-group></meta-data>"""

        with patch("cds.cds_launcher.CDSLauncher", return_value=mocked_launcher):
            from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
            to_test = UploadRequestedProcessor()
            self.assertFalse(to_test.validate_inmeta(testdoc))

    def test_validate_inmeta_notxml(self):
        """
        validate_inmeta should return false and not an exception if the document is not valid xml
        :return:
        """
        mocked_launcher = MagicMock(target=cds.cds_launcher.CDSLauncher)
        testdoc = """<?xml version="1.0"?>
            <meta-data><meta-group type="movie meta"><meta name="itemId" vilue="VX-1234"/></meta-group>"""

        with patch("cds.cds_launcher.CDSLauncher", return_value=mocked_launcher):
            from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
            to_test = UploadRequestedProcessor()
            self.assertFalse(to_test.validate_inmeta(testdoc))

    def test_build_filename(self):
        """
        build_filename should return the suggested filename/path if it does not exist
        :return:
        """
        mocked_launcher = MagicMock(target=cds.cds_launcher.CDSLauncher)
        with patch("cds.cds_launcher.CDSLauncher", return_value=mocked_launcher):
            with patch("os.path.exists", return_value=False) as mock_exists:
                from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
                to_test = UploadRequestedProcessor()
                result = to_test.build_filename("/path/for/inmetas","VX-1234")
                self.assertEqual(result, "/path/for/inmetas/VX-1234.inmeta")
                mock_exists.assert_called_once_with("/path/for/inmetas/VX-1234.inmeta")

    def test_build_filename_incremental(self):
        """
        build_filename should keep generating new filenames until one does not exist
        :return:
        """
        mocked_launcher = MagicMock(target=cds.cds_launcher.CDSLauncher)
        with patch("cds.cds_launcher.CDSLauncher", return_value=mocked_launcher):
            with patch("os.path.exists", side_effect=[True, True, True, True, False]) as mock_exists:
                from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
                to_test = UploadRequestedProcessor()
                result = to_test.build_filename("/path/for/inmetas","VX-1234")
                self.assertEqual(result, "/path/for/inmetas/VX-1234-4.inmeta")
                self.assertEqual(mock_exists.call_count, 5)

    def test_build_filename_notworking(self):
        """
        build_filename should raise a runtime error if it's tried 1,000 times to make a filename
        :return:
        """
        mocked_launcher = MagicMock(target=cds.cds_launcher.CDSLauncher)
        with patch("cds.cds_launcher.CDSLauncher", return_value=mocked_launcher):
            with patch("os.path.exists", return_value=True) as mock_exists:
                from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
                to_test = UploadRequestedProcessor()
                with self.assertRaises(RuntimeError):
                    to_test.build_filename("/path/for/inmetas","VX-1234")
                self.assertEqual(mock_exists.call_count, 1000)

    def test_write_out_inmeta(self):
        """
        write_out_inmeta should dump content to a file given §by build_filename
        :return:
        """
        mocked_launcher = MagicMock(target=cds.cds_launcher.CDSLauncher)
        with patch("cds.cds_launcher.CDSLauncher", return_value=mocked_launcher):
            from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
            os.environ["INMETA_PATH"] = "/tmp"
            to_test = UploadRequestedProcessor()
            to_test.build_filename = MagicMock(return_value="/tmp/responder-rabbitmq-test.inmeta")

            result = to_test.write_out_inmeta("filename-hint.mxf","actual content should go here")

            self.assertTrue(os.path.exists("/tmp/responder-rabbitmq-test.inmeta"))
            with open("/tmp/responder-rabbitmq-test.inmeta", "r") as f:
                read_back_content = f.read()
            os.remove("/tmp/responder-rabbitmq-test.inmeta")

            self.assertEqual(read_back_content, "actual content should go here")
            self.assertEqual(result, "/tmp/responder-rabbitmq-test.inmeta")

            to_test.build_filename.assert_called_once_with("/tmp","filename-hint")

    def test_randomstring(self):
        """
        randomstring should return a string of the requested length consisting of letters and numbers
        :return:
        """
        import re
        from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor

        result = UploadRequestedProcessor.randomstring(100)
        self.assertEqual(len(result), 100)

        checkRE = re.compile(r'^[A-Za-z0-9]{100}$')
        self.assertTrue(checkRE.match(result))

    def test_valid_message_receive(self):
        """
        valid_message_receive should write out the inmeta and call the launcher to start the job
        :return:
        """
        mocked_launcher = MagicMock(target=cds.cds_launcher.CDSLauncher)
        mocked_launcher.launch_cds_job = MagicMock()
        mocked_channel = MagicMock(target=pika.channel.Channel)
        mocked_channel.basic_publish = MagicMock()

        with patch("cds.cds_launcher.CDSLauncher", return_value=mocked_launcher):
            from rabbitmq.UploadRequestedProcessor import UploadRequestedProcessor
            to_test = UploadRequestedProcessor()
            to_test.validate_inmeta = MagicMock(return_value=True)
            to_test.write_out_inmeta = MagicMock(return_value="/path/to/mdpacket.inmeta")
            to_test.inform_job_status = MagicMock()

            fake_message = {
                "inmeta": "metdata-goes-here",
                "filename": "somefile.mxf",
                "routename": "someroute.xml"
            }

            to_test.valid_message_receive(mocked_channel, "some-exchange","routing.key","2345",fake_message)
            to_test.validate_inmeta.assert_called_once_with(fake_message["inmeta"])
            to_test.write_out_inmeta.assert_called_once_with("somefile.mxf", fake_message["inmeta"])
            mocked_launcher.launch_cds_job.assert_called_once()
            self.assertEqual(mocked_launcher.launch_cds_job.call_args[0][0], "/path/to/mdpacket.inmeta")
            self.assertEqual(mocked_launcher.launch_cds_job.call_args[0][2], fake_message["routename"])
            to_test.inform_job_status.assert_called_once()