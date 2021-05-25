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