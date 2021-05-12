import jsonschema
import json
import logging
import pika.spec

logger = logging.getLogger(__name__)


class MessageProcessor(object):
    """
    MessageProcessor describes the interface that all message processor classes should implement
    """
    schema = None       # override this in a subclass
    routing_key = None  # override this in a subclass

    class NackMessage(Exception):
        pass
    class NackWithRetry(Exception):
        pass

    def valid_message_receive(self, channel:pika.spec.Channel, exchange_name, routing_key, delivery_tag, body):
        """
        override this method in a subclass in order to receive information
        :param channel: the open pika channel, for sending messages back to our exchange
        :param exchange_name:
        :param routing_key:
        :param delivery_tag:
        :param body:
        :return:
        """
        logger.debug("Received validated message from {0} via {1} with {2}: {3}".format(exchange_name, routing_key, delivery_tag, body))
        pass

    def validate_with_schema(self, body):
        content = json.loads(body.decode('UTF-8'))
        jsonschema.validate(content, self.schema)   # throws an exception if the content does not validate
        return content  #if we get to this line, then validation was successful

    def raw_message_receive(self, channel, method:pika.spec.Basic.Deliver, properties:pika.spec.BasicProperties, body:bytes):
        """
        called from the pika library when data is received on our channel -
        see https://pika.readthedocs.io/en/stable/modules/channel.html#pika.channel.Channel.basic_consume
        the implementation will attempt to decode the body as JSON and validate it using jsonschema against
        the schema provided by the `schema` member before passing it on to valid_message_receive
        normally you DON'T want to over-ride this, you want valid_message_receive
        :param channel: pika.channel.Channel object
        :param method: pika.spec.Basic.Deliver object - basic metadata about the deliver
        :param properties: pika.spec.BasicProperties object
        :param body: byte array of the message content
        :return:
        """
        tag = method.delivery_tag
        validated_content = None
        try:
            logger.debug("Received message with delivery tag {2} from {0}: {1}".format(channel, body.decode('UTF-8'), tag))

            if self.schema:
                validated_content = self.validate_with_schema(body)
            else:
                logger.warning("No schema nor serializer resent for validation in {0}, cannot continue".format(self.__class__.__name__))
                channel.basic_nack(delivery_tag=tag, requeue=True)

        except Exception as e:
            logger.exception("Message from {0} via {1} with delivery tag {2} did not validate: {3}"
                             .format(method.routing_key, method.exchange, method.delivery_tag, str(e)), exc_info=e)
            logger.error("Offending message content from {0} via {1} with delivery tag {2} was {3}"
                         .format(method.routing_key, method.exchange, method.delivery_tag, body.decode('UTF-8')))

            channel.basic_nack(delivery_tag=tag, requeue=False)
            return

        if validated_content is not None:
            try:
                self.valid_message_receive(channel, method.exchange, method.routing_key, method.delivery_tag, validated_content)
                channel.basic_ack(delivery_tag=tag)
            except self.NackMessage:
                logger.warning("Message was indicated to be un-processable, nacking without requeue")
                channel.basic_nack(delivery_tag=tag, requeue=False)
            except self.NackWithRetry:
                logger.warning("Message could not be processed but should be requeued")
                channel.basic_nack(delivery_tag=tag, requeue=True)
            except Exception as e:
                logger.error("Could not process message: {0}".format(str(e)))
                channel.basic_nack(delivery_tag=tag, requeue=False)
                # channel.basic_cancel(method.consumer_tag)
                # raise ValueError("Could not process message")
        else:
            logger.error("Validated content was empty but no validation error? There must be a bug")
            channel.basic_nack(delivery_tag=tag, requeue=True)
            channel.basic_cancel(method.consumer_tag)
            raise ValueError("Validated content empty but no validation error")