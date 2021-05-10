import pika
import pika.exceptions
import logging
import json
import time

logger = logging.getLogger(__name__)

### NOTE: It may be more appropriate to use an async delivery mechanism, in order to prevent rabbitmq issues from
### making us miss k8s notifications.  But, if we have rmq issues, would we just miss those messages _anyway_? Would it
### do any good to hold them in memory? Should we buffer them to redis or something? What if something happens to that?
### Therefore this is currently a simple, blocking implementation that won't return until a delivery confirmation has been
### received from the broker


class MessageSender(object):
    """
    Object that maintains a rabbitmq connection and sends messages to a given exchange
    """
    def __init__(self, params: pika.connection.ConnectionParameters, exchange_name:str, max_retry_attempts=10):
        self._params = params
        self.max_retry_attempts = max_retry_attempts
        self.exchange = exchange_name
        self._setup_channel()

    def _setup_channel(self, attempt=1):
        """
        sets up a channel via the given connection and ensures that the exchange is declared.
        this is called at construction so you shouldn't need to call manually, and it is called again if the
        connection is dropped.
        this can throw any AMQP exceptions.
        :return:
        """
        try:
            self._conn = pika.BlockingConnection(self._params)
            self._channel = self._conn.channel()
            self._channel.exchange_declare(self.exchange, exchange_type="topic",durable=True,auto_delete=False)
            self._channel.confirm_delivery()
        except pika.exceptions.AMQPError as e:
            if attempt >= self.max_retry_attempts:
                raise

            retry_delay = 2*attempt
            logger.error("Could not establish rabbitmq connection on attempt {0}: {1}. Retrying in {2}s".format(attempt, str(e), retry_delay))
            time.sleep(retry_delay)
            return self._setup_channel(attempt+1)

    def notify(self, routing_key: str, msg_content: dict, attempt=1)->bool:
        """
        send the given message (formatted to json) to the given routing key on the exchange configured at construction.
        this will wait for a delivery confirmation to be received from the broker before returning.
        This can raise a JSON encoding exception if the message is not serializable, or a RuntimeError if the sending retries have
        been exceeded
        :param routing_key:
        :param msg_content:
        :param attempt: don't set this, it is ussed internally as a retry counter
        :return: boolean indicating if the message was sent or not. Assume unrecoverable error if false.
        """
        error_exit = False
        try:
            logger.debug("Sending {0} via {1} to {2}".format(msg_content, routing_key, self.exchange))
            string_content = json.dumps(msg_content)
            self._channel.basic_publish(self.exchange, routing_key, string_content.encode(encoding="UTF-8"))
            return True
        except pika.exceptions.BodyTooLongError as e:
            logger.error("Could not send message {0} as the body is too long for the server".format(msg_content))
            return False

        except pika.exceptions.UnroutableError as e:
            if attempt >= self.max_retry_attempts:
                logger.error("Could not deliver message after {0} attempts: {1}, exiting".format(attempt, str(e)))
                error_exit = True
            else:
                retry_delay = 5*attempt
                logger.error("Could not send message on attempt {0}: {1}. Retrying in {2} seconds".format(attempt, str(e), retry_delay))
                time.sleep(retry_delay)
                return self.notify(routing_key, msg_content, attempt+1)
        except (pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPHeartbeatTimeout) as e:
            if attempt >= self.max_retry_attempts:
                logger.error("Could not deliver message after {0} attempts: {1}, exiting".format(attempt, str(e)))
                error_exit = True
            else:
                logger.error("Connection error: {0}. Attempting to re-open....".format(str(e)))
                self._setup_channel()
                return self.notify(routing_key, msg_content, attempt+1)

        if error_exit:  #avoid ugly "exception handling this exception" messages
            raise RuntimeError("Could not deliver message after {0} retries".format(self.max_retry_attempts))