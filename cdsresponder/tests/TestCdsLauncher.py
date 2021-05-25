from unittest import TestCase
import re


class TestCDSLauncher(TestCase):
    def test_sanitise_job_name_length(self):
        """
        sanitise_job_name should never return more than 63 characters and should strip spaces
        """
        from cds.cds_launcher import CDSLauncher
        long_test_name = "this is a very long test name which is not going to make it in its entirety, because it is really too long"
        sanitised = CDSLauncher.sanitise_job_name(long_test_name)

        self.assertLessEqual(len(sanitised), 59)
        self.assertFalse(re.match(r"\s", sanitised))

    def test_sanitise_job_name_startend(self):
        """
        a valid job name must start and end with an alphanumeric char
        :return:
        """
        from cds.cds_launcher import CDSLauncher
        test_name = "! Read this, because it's very important! "
        sanitised = CDSLauncher.sanitise_job_name(test_name)
        self.assertEqual(sanitised, "read-this-because-its-very-important")

        another_test_name = "! Read this again, time 2.  "
        self.assertEqual(CDSLauncher.sanitise_job_name(another_test_name), "read-this-again-time-2")

        long_test_name = "this is a very long test name which is not going to get th in its entirety, because it is really too long"
        sanitised = CDSLauncher.sanitise_job_name(long_test_name)

        self.assertEqual(sanitised, "this-is-a-very-long-test-name-which-is-not-going-to-get-th")