from unittest import TestCase
from unittest.mock import MagicMock, patch, call
import os
from kubernetes import client
from rabbitmq.K8MessageProcessor import K8MessageProcessor
import pika.channel
from kubernetes.client.models.v1_pod_list import V1PodList
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_object_meta import V1ObjectMeta


class TestK8MessageProcessor(TestCase):
    class ToTest(K8MessageProcessor):
        """
        mocks out the initialization of K8MessageProcessor so it does not attempt to contact the cluster and internal methods
        are spies
        """
        def __init__(self, ns:str, should_keep_jobs:bool):
            self.should_keep_jobs = should_keep_jobs
            self.batch = MagicMock(target=client.BatchV1Api)
            self.k8core = MagicMock(target=client.CoreV1Api)
            self.namespace = ns

            self.read_logs = MagicMock()
            self.safe_delete_job = MagicMock()

    class ToTestNoK8mocks(K8MessageProcessor):
        """
        mocks out the initialization of K8MessageProcessor so it does not attempt to contact the cluster but leaves
        internal methods unmocked
        """
        def __init__(self, ns:str, should_keep_jobs:bool):
            self.should_keep_jobs = should_keep_jobs
            self.batch = MagicMock(target=client.BatchV1Api)
            self.k8core = MagicMock(target=client.CoreV1Api)
            self.namespace = ns

    def test_valid_message_receive_success(self):
        """
        valid_message_receive should try to download logs then delete the pod if the status is successful
        :return:
        """
        test_msg = {
            "job-id": "some-id",
            "job-name": "some-job",
            "job-namespace": "job-namespace",
        }

        processor = self.ToTest("test-namespace", False)
        processor.valid_message_receive(MagicMock(pika.channel.Channel), "some-exchange","cds.job.success",1,test_msg)

        processor.read_logs.assert_called_once_with("some-job","job-namespace")
        processor.safe_delete_job.assert_called_once_with("some-job","job-namespace")

    def test_valid_message_receive_failure(self):
        """
        valid_message_receive should try to download logs then delete the pod if the status is successful
        :return:
        """
        test_msg = {
            "job-id": "some-id",
            "job-name": "some-job",
            "job-namespace": "job-namespace",
        }

        processor = self.ToTest("test-namespace", False)
        processor.valid_message_receive(MagicMock(pika.channel.Channel), "some-exchange", "cds.job.failed", 1, test_msg)

        processor.read_logs.assert_called_once_with("some-job","job-namespace")
        processor.safe_delete_job.assert_called_once_with("some-job","job-namespace")

    def test_valid_message_receive_success_nodel(self):
        """
        valid_message_receive should try to delete the pod if it was asked not to
        :return:
        """
        test_msg = {
            "job-id": "some-id",
            "job-name": "some-job",
            "job-namespace": "job-namespace",
        }

        processor = self.ToTest("test-namespace", True)
        processor.valid_message_receive(MagicMock(pika.channel.Channel), "some-exchange","cds.job.success",1,test_msg)

        processor.read_logs.assert_called_once_with("some-job","job-namespace")
        processor.safe_delete_job.assert_not_called()

    def test_valid_message_receive_running(self):
        """
        valid_message_receive should not try to download logs then delete the pod if the status is running
        :return:
        """
        test_msg = {
            "job-id": "some-id",
            "job-name": "some-job",
            "job-namespace": "job-namespace",
        }

        processor = self.ToTest("test-namespace", False)
        processor.valid_message_receive(MagicMock(pika.channel.Channel), "some-exchange","cds.job.running",1,test_msg)

        processor.read_logs.assert_not_called()
        processor.safe_delete_job.assert_not_called()

    def test_valid_message_receive_retry(self):
        """
        valid_message_receive should not try to download logs then delete the pod if the status is retry
        :return:
        """
        test_msg = {
            "job-id": "some-id",
            "job-name": "some-job",
            "job-namespace": "job-namespace",
        }

        processor = self.ToTest("test-namespace", False)
        processor.valid_message_receive(MagicMock(pika.channel.Channel), "some-exchange","cds.job.retry",1,test_msg)

        processor.read_logs.assert_not_called()
        processor.safe_delete_job.assert_not_called()

    def test_read_logs(self):
        """
        read_logs should list all the pods associated with the given job and call out to k8s.k8utils.dump_pod_logs to
        write the data to disk
        :return:
        """
        processor = self.ToTestNoK8mocks("test-namespace", False)
        processor.pod_log_basepath = "/tmp"
        mock_pod_one = MagicMock(target=V1Pod)
        mock_pod_one.metadata = MagicMock(target=V1ObjectMeta)
        mock_pod_one.metadata.uid="pod-id-1"
        mock_pod_one.metadata.name="pod-name-1"
        mock_pod_one.metadata.namespace="some-namespace"
        mock_pod_two = MagicMock(target=V1Pod)
        mock_pod_two.metadata = MagicMock(target=V1ObjectMeta)
        mock_pod_two.metadata.uid="pod-id-2"
        mock_pod_two.metadata.name="pod-name-2"
        mock_pod_two.metadata.namespace="some-namespace"
        pods_list = V1PodList(items=[
            mock_pod_one,
            mock_pod_two
        ])

        processor.k8core.list_namespaced_pod = MagicMock(return_value=pods_list)

        with patch("k8s.k8utils.dump_pod_logs") as mock_dump_pod_logs:
            log_count = processor.read_logs("some-job", "some-namespace")
            processor.k8core.list_namespaced_pod.assert_called_once_with("some-namespace", label_selector="job-name=some-job")
            mock_dump_pod_logs.assert_has_calls([
                call("pod-name-1","some-namespace","/tmp/some-job/pod-name-1.log"),
                call("pod-name-2","some-namespace","/tmp/some-job/pod-name-2.log")
            ])
            self.assertEqual(mock_dump_pod_logs.call_count, 2)
            self.assertEqual(log_count, 2)

    def test_read_logs_notrequired(self):
        """
        read_logs should not read anything if pod_log_basepath is not set
        :return:
        """
        processor = self.ToTestNoK8mocks("test-namespace", False)
        processor.pod_log_basepath = None

        processor.k8core.list_namespaced_pod = MagicMock()

        with patch("k8s.k8utils.dump_pod_logs") as mock_dump_pod_logs:
            log_count = processor.read_logs("some-job", "some-namespace")
            processor.k8core.list_namespaced_pod.assert_not_called()

            mock_dump_pod_logs.assert_not_called()
            self.assertEqual(log_count, 0)

    def test_safe_delete_job(self):
        """
        safe delete job should request deletion of the given job
        :return:
        """
        processor = self.ToTestNoK8mocks("test-namespace", False)
        processor.batch.delete_namespaced_job = MagicMock()

        processor.safe_delete_job("some-job", "some-namespace")
        processor.batch.delete_namespaced_job.assert_called_once_with("some-job", "some-namespace")

    def test_safe_delete_job_error(self):
        """
        safe delete job should not raise an exception if the delete operation does
        :return:
        """
        import kubernetes.client.exceptions
        processor = self.ToTestNoK8mocks("test-namespace", False)
        processor.batch.delete_namespaced_job = MagicMock(side_effect=kubernetes.client.exceptions.ApiException)

        processor.safe_delete_job("some-job", "some-namespace")
        processor.batch.delete_namespaced_job.assert_called_once_with("some-job", "some-namespace")