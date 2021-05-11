import redis
import logging
import time
logger = logging.getLogger(__name__)


class Journal(object):
    """
    implements a journalling function, whereby the most recent sequence number of the k8s watcher is stored in redis.
    this allows us to pick up from where we left off in the event of crashes/failure
    """
    EVENT_KEY = "cdsreaper:most-recent-event"

    def __init__(self, redis_host:str, redis_port:int, redis_db:int, redis_pw:str, max_retries=10):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_pw = redis_pw

        self.max_retries = max_retries

        self._establish_connection()

    def _establish_connection(self, attempt=1):
        """
        internal method that sets up a connection object and pings the server to check we can talk to it.
        called automatically during construction
        retries if a connection can't be established
        can raise redis exceptions or python base connection exceptions
        :param attempt: don't set this, it's used internally to count retries
        :return: nothing
        """
        try:
            self._conn = redis.Redis(self.redis_host, self.redis_port, self.redis_db, password=self.redis_pw)
            self._conn.ping()
        except (redis.RedisError, ConnectionError) as err:
            if attempt>=self.max_retries:
                logger.error("Could not connect to redis at {0}:{1} after {2} attempts: {3}".format(self.redis_host, self.redis_port, attempt, str(err)))
                raise

            retry_delay = 2*attempt
            logger.warning("Could not connect to redis at {0}:{1} on attempt {2}, retrying in {3}s...".format(self.redis_host, self.redis_port, attempt, retry_delay))
            time.sleep(retry_delay)
            return self._establish_connection(attempt+1)

    def get_most_recent_event(self)->int:
        """
        gets the most recent journalled event id
        :return: the id, or None if nothing was set.
        """
        maybe_value = self._conn.get(Journal.EVENT_KEY)
        if maybe_value is None:
            return None
        else:
            try:
                return int(maybe_value)
            except (TypeError, ValueError) as e:
                logger.error("Invalid value {0} at cdsreaper:most-recent-event could not be converted to int. Processing will start from latest event.".format(maybe_value))
                self._conn.delete(Journal.EVENT_KEY)
                return None

    def record_processed(self, id:int):
        """
        record in the journal that the given event has been processed
        :param id:
        :return:
        """
        self._conn.set(Journal.EVENT_KEY, id)

    def clear_journal(self):
        """
        clears the most recent journalled event id so a subsequent call to get_most_recent_event will return None.
        this can be used if we have gone over the event horizon of the cluster and must start listing afresh
        :return:
        """
        self._conn.delete(Journal.EVENT_KEY)