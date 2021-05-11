from unittest import TestCase
from unittest.mock import MagicMock, patch
from jobwatcher import JobWatcher
from kubernetes.client.models.v1_job_condition import V1JobCondition
from kubernetes.client.models.v1_job_status import V1JobStatus
from kubernetes.client.models.v1_job import V1Job
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.api.batch_v1_api import BatchV1Api
from datetime import datetime, timedelta


class TestJobWatcher(TestCase):
    def test_get_most_recent_condition(self):
        """
        get_most_recent_condition should return the V1JobContition of the provided list with the latest time
        :return:
        """
        mock_status = MagicMock(target=V1JobStatus)
        conditions_list = [
            V1JobCondition(last_probe_time=datetime(2021,5,2,3,4,5), message="number 5",status=mock_status, type="test"),
            V1JobCondition(last_probe_time=datetime(2021,3,2,3,4,5), message="number 3",status=mock_status, type="test"),
            V1JobCondition(last_probe_time=datetime(2021,1,2,3,4,5), message="number 1",status=mock_status, type="test"),
            V1JobCondition(last_probe_time=datetime(2021,2,2,3,4,5), message="number 2",status=mock_status, type="test"),
            V1JobCondition(last_probe_time=datetime(2021,4,2,3,4,5), message="number 4",status=mock_status, type="test"),
        ]

        result = JobWatcher.get_most_recent_condition(conditions_list)
        self.assertEqual(result.message, "number 5")

    def test_get_most_recent_condition_empty(self):
        """
        get_most_recent_condition should return None when there are no conditions in the list
        :return:
        """
        result = JobWatcher.get_most_recent_condition([])
        self.assertIsNone(result)

    def test_check_job(self):
        """
        check_job should request a message send with details of the provided job
        :return:
        """
        from messagesender import MessageSender
        from journal import Journal
        fake_job = MagicMock(target=V1Job)
        fake_job.metadata = MagicMock()
        fake_job.metadata.uid = "some-uid"
        fake_job.metadata.name = "job-name"
        fake_job.metadata.namespace = "some-namespace"
        fake_job.status = V1JobStatus(active=0, completion_time=datetime.now(), conditions=None, failed=None,succeeded=1)

        mock_sender = MagicMock(target=MessageSender)
        mock_journal = MagicMock(target=Journal)
        mock_sender.notify = MagicMock(return_value=True)

        w = JobWatcher(MagicMock(target=BatchV1Api), mock_sender, mock_journal, "some-namespace")
        result = w.check_job(fake_job)

        expected_content = {
            "job-id": "some-uid",
            "job-name": "job-name",
            "job-namespace": "some-namespace",
            "retry-count": 0
        }
        mock_sender.notify.assert_called_once_with("cds.job.success", expected_content)
        self.assertTrue(result)

    def test_check_job_on_failure(self):
        """
        check_job should send job failure details too if it failed
        :return:
        """
        from messagesender import MessageSender
        from journal import Journal
        mock_status = MagicMock(target=V1JobStatus)

        fake_job = MagicMock(target=V1Job)
        fake_job.metadata = MagicMock()
        fake_job.metadata.uid = "some-uid"
        fake_job.metadata.name = "job-name"
        fake_job.metadata.namespace = "some-namespace"
        fake_job.status = V1JobStatus(active=0,
                                      completion_time=datetime.now(),
                                      start_time=datetime.now() - timedelta(minutes=3),
                                      conditions=[
                                          V1JobCondition(last_probe_time=datetime(2021,1,2,3,4,5),
                                                         message="it went splat",
                                                         reason="it hit the ground falling",
                                                         status=mock_status,
                                                         type="test"),
                                      ],
                                      failed=1,
                                      succeeded=None)

        mock_sender = MagicMock(target=MessageSender)
        mock_journal = MagicMock(target=Journal)
        mock_sender.notify = MagicMock(return_value=True)

        w = JobWatcher(MagicMock(target=BatchV1Api), mock_sender, mock_journal, "some-namespace")
        result = w.check_job(fake_job)

        expected_content = {
            "job-id": "some-uid",
            "job-name": "job-name",
            "job-namespace": "some-namespace",
            "retry-count": 1,
            "failure-reason": "it hit the ground falling - it went splat"
        }
        mock_sender.notify.assert_called_once_with("cds.job.failed", expected_content)
        self.assertTrue(result)