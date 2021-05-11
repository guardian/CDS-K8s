from unittest import TestCase
from unittest.mock import MagicMock, patch
import logging


class TestJournal(TestCase):
    def test_setup_ping(self):
        """
        Journal should initiate a redis connection and ping the server on startup
        :return:
        """
        import redis
        mock_client = MagicMock(target=redis.Redis)
        mock_client.ping = MagicMock()

        with patch("redis.Redis", return_value=mock_client) as mock_constructor:
            from journal import Journal
            j = Journal("somehost",6379, 1, "somepassword",1)
            mock_constructor.assert_called_once_with("somehost", 6379,1,password="somepassword")
            mock_client.ping.assert_called_once()

    def test_setup_ping_failed(self):
        """
        journal should retry connection the specified number of times before failing
        :return:
        """
        import redis
        mock_client = MagicMock(target=redis.Redis)
        mock_client.ping = MagicMock(side_effect=ConnectionError)

        with patch("redis.Redis", return_value=mock_client) as mock_constructor:
            from journal import Journal
            with self.assertRaises(ConnectionError):
                j = Journal("somehost",6379, 1, "somepassword",2)
            mock_constructor.assert_called_with("somehost", 6379,1,password="somepassword")
            self.assertEqual(mock_client.ping.call_count, 2)
            self.assertEqual(mock_constructor.call_count, 2)

    def test_get_most_recent(self):
        """
        get_most_recent_event should lift the current value of the event key
        and return it as a number
        :return:
        """
        import redis
        mock_client = MagicMock(target=redis.Redis)
        mock_client.ping = MagicMock()
        mock_client.get = MagicMock(return_value="123456")
        mock_client.delete = MagicMock()

        with patch("redis.Redis", return_value=mock_client) as mock_constructor:
            from journal import Journal
            j = Journal("somehost",6379, 1, "somepassword",1)
            result = j.get_most_recent_event()
            self.assertEqual(result, 123456)
            mock_client.get.assert_called_once_with(Journal.EVENT_KEY)
            mock_client.delete.assert_not_called()

    def test_get_most_recent_absent(self):
        """
        get_most_recent_event should return None if there is no event to find
        :return:
        """
        import redis
        mock_client = MagicMock(target=redis.Redis)
        mock_client.ping = MagicMock()
        mock_client.get = MagicMock(return_value=None)
        mock_client.delete = MagicMock()

        with patch("redis.Redis", return_value=mock_client) as mock_constructor:
            from journal import Journal
            j = Journal("somehost",6379, 1, "somepassword",1)
            result = j.get_most_recent_event()
            self.assertEqual(result, None)
            mock_client.get.assert_called_once_with(Journal.EVENT_KEY)
            mock_client.delete.assert_not_called()

    def test_get_most_recent_invalid(self):
        """
        get_most_recent_event should return None if the data is invalid, and delete the incorrect content
        :return:
        """
        import redis
        mock_client = MagicMock(target=redis.Redis)
        mock_client.ping = MagicMock()
        mock_client.get = MagicMock(return_value="abcde")
        mock_client.delete = MagicMock()

        with patch("redis.Redis", return_value=mock_client) as mock_constructor:
            from journal import Journal
            j = Journal("somehost", 6379, 1, "somepassword",1)
            result = j.get_most_recent_event()
            self.assertEqual(result, None)
            mock_client.get.assert_called_once_with(Journal.EVENT_KEY)
            mock_client.delete.assert_called_once_with(Journal.EVENT_KEY)

    def test_record_processed(self):
        """
        record_processed should set the event key to the provided value
        :return:
        """
        import redis
        mock_client = MagicMock(target=redis.Redis)
        mock_client.ping = MagicMock()
        mock_client.set = MagicMock()
        mock_client.delete = MagicMock()

        with patch("redis.Redis", return_value=mock_client) as mock_constructor:
            from journal import Journal
            j = Journal("somehost",6379, 1, "somepassword",1)
            j.record_processed(5678)
            mock_client.set.assert_called_once_with(Journal.EVENT_KEY, 5678)
            mock_client.delete.assert_not_called()

    def test_clear_journal(self):
        """
        clear_journal should delete the event key contents
        :return:
        """
        import redis
        mock_client = MagicMock(target=redis.Redis)
        mock_client.ping = MagicMock()
        mock_client.set = MagicMock()
        mock_client.delete = MagicMock()

        with patch("redis.Redis", return_value=mock_client) as mock_constructor:
            from journal import Journal
            j = Journal("somehost",6379, 1, "somepassword",1)
            j.clear_journal()
            mock_client.delete.assert_called_once_with(Journal.EVENT_KEY)