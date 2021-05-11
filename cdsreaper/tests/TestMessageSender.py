from unittest import TestCase
from unittest.mock import MagicMock, patch
import pika
import pika.channel
import pika.exceptions
from messagesender import MessageSender


class TestMessageSender(TestCase):
    def test_messagesender_init(self):
        """
        MessageSender should establish a connection and declare the exchange on startup
        :return:
        """
        mock_channel = MagicMock(target=pika.channel.Channel)
        mock_channel.exchange_declare = MagicMock()
        mock_channel.confirm_delivery = MagicMock()

        mock_connection = MagicMock(target=pika.BlockingConnection)
        mock_connection.channel = MagicMock(return_value=mock_channel)

        params = pika.ConnectionParameters(host="somehost",port=5672, virtual_host="/")

        with patch("pika.BlockingConnection", return_value=mock_connection) as mock_constructor:
            MessageSender(params,"some-exchange",2)

            mock_constructor.assert_called_once_with(params)
            mock_channel.exchange_declare.assert_called_once_with("some-exchange",exchange_type="topic",durable=True,auto_delete=False)
            mock_channel.confirm_delivery.assert_called_once_with()

    def test_messagesender_notify(self):
        """
        MessageSender.notify should send a message on the given channel and return True when successful
        :return:
        """
        mock_channel = MagicMock(target=pika.channel.Channel)
        mock_channel.basic_publish = MagicMock()
        mock_setup_called = MagicMock()
        params = pika.ConnectionParameters(host="somehost",port=5672, virtual_host="/")

        class SenderToTest(MessageSender):
            def _setup_channel(self, attempt=1):
                self._channel = mock_channel
                mock_setup_called()

        s = SenderToTest(params, "some-exchange", 2)

        result = s.notify("some-key", {"key":"value","otherkey":["value1","value2"]})
        self.assertTrue(result)

        mock_channel.basic_publish.assert_called_once_with("some-exchange","some-key",
                                                           b"""{"key": "value", "otherkey": ["value1", "value2"]}""")

    def test_messagesender_toolong(self):
        """
        MessageSender.notify should return false if the message body is too long
        :return:
        """
        mock_channel = MagicMock(target=pika.channel.Channel)
        mock_channel.basic_publish = MagicMock(side_effect=pika.exceptions.BodyTooLongError)
        mock_setup_called = MagicMock()
        params = pika.ConnectionParameters(host="somehost",port=5672, virtual_host="/")

        class SenderToTest(MessageSender):
            def _setup_channel(self, attempt=1):
                self._channel = mock_channel
                mock_setup_called()

        s = SenderToTest(params, "some-exchange", 2)

        result = s.notify("some-key", {"key":"value","otherkey":["value1","value2"]})
        self.assertFalse(result)

        mock_channel.basic_publish.assert_called_once_with("some-exchange","some-key",
                                                           b"""{"key": "value", "otherkey": ["value1", "value2"]}""")

    def test_messagesender_notdelivered(self):
        """
        MessageSender.notify should retry and then raise an exception if it runs out of retries
        :return:
        """
        mock_channel = MagicMock(target=pika.channel.Channel)
        mock_channel.basic_publish = MagicMock(side_effect=pika.exceptions.UnroutableError(list()))
        mock_setup_called = MagicMock()
        params = pika.ConnectionParameters(host="somehost",port=5672, virtual_host="/")

        class SenderToTest(MessageSender):
            DELAY_SECONDS_PER_RETRY = 1
            def _setup_channel(self, attempt=1):
                self._channel = mock_channel
                mock_setup_called()

        s = SenderToTest(params, "some-exchange", 2)

        with self.assertRaises(RuntimeError):
            s.notify("some-key", {"key":"value","otherkey":["value1","value2"]})

        self.assertEqual(mock_channel.basic_publish.call_count, 2)
        mock_channel.basic_publish.assert_called_with("some-exchange","some-key",
                                                           b"""{"key": "value", "otherkey": ["value1", "value2"]}""")

    def test_messagesender_connection_drop(self):
        """
        MessageSender.notify should try to re-establish the connection if it drops
        :return:
        """
        mock_channel = MagicMock(target=pika.channel.Channel)
        mock_channel.basic_publish = MagicMock(side_effect=[pika.exceptions.AMQPConnectionError, None])
        mock_setup_called = MagicMock()
        params = pika.ConnectionParameters(host="somehost",port=5672, virtual_host="/")

        class SenderToTest(MessageSender):
            DELAY_SECONDS_PER_RETRY = 1
            def _setup_channel(self, attempt=1):
                self._channel = mock_channel
                mock_setup_called()

        s = SenderToTest(params, "some-exchange", 2)

        result = s.notify("some-key", {"key":"value","otherkey":["value1","value2"]})

        self.assertEqual(mock_channel.basic_publish.call_count, 2)
        self.assertEqual(mock_setup_called.call_count, 2)
        mock_channel.basic_publish.assert_called_with("some-exchange","some-key",
                                                      b"""{"key": "value", "otherkey": ["value1", "value2"]}""")
        self.assertEqual(result, True)

