#!/usr/bin/env python
## This is mostly taken from pluto-deliverables's rabbitmq responder
import logging
import os

import pika
import re
from functools import partial
import sys
import signal

logging.basicConfig(format="{asctime} {name}|{funcName} [{levelname}] {message}",level=logging.DEBUG,style='{')
pikaLogger = logging.getLogger("pika")
pikaLogger.level=logging.WARN
logger = logging.getLogger(__name__)


class Command(object):
    @staticmethod
    def declare_rabbitmq_setup(channel:pika.channel.Channel):
        channel.exchange_declare(exchange="cdsresponder-dlx", exchange_type="direct")
        channel.exchange_declare(exchange="cdsresponder", exchange_type="topic")

    @staticmethod
    def connect_channel(exchange_name, handler, channel):
        """
        async callback that is used to connect a channel once it has been declared
        :param channel: channel to set up
        :param exchange_name: str name of the exchange to connect to
        :param handler: a MessageProcessor class (NOT instance)
        :return:
        """
        logger.info("Establishing connection to exchange {0} from {1}...".format(exchange_name, handler.__class__.__name__))
        sanitised_routingkey = re.sub(r'[^\w\d]', '', handler.routing_key)

        Command.declare_rabbitmq_setup(channel)
        queuename = "cdsresponder-{0}".format(sanitised_routingkey)
        channel.queue_declare("cdsresponder-dlq", durable=True)
        channel.queue_bind("cdsresponder-dlq","cdsresponder-dlx")

        channel.queue_declare(queuename, arguments={
            'x-dead-letter-exchange': "cdsresponder-dlx"
        })
        channel.queue_bind(queuename, exchange_name, routing_key=handler.routing_key)
        channel.basic_consume(queuename,
                              handler.raw_message_receive,
                              auto_ack=False,
                              exclusive=False,
                              callback=lambda consumer: logger.info("Consumer started for {0} from {1}".format(queuename, exchange_name)),
                              )

    def channel_opened(self, connection):
        """
        async callback that is invoked when the connection is ready.
        it is used to connect up the channels
        :param connection: rabbitmq connection
        :return:
        """
        from rabbitmq.mappings import EXCHANGE_MAPPINGS
        logger.info("Connection opened")
        for i in range(0, len(EXCHANGE_MAPPINGS)):
            # partial adjusts the argument list, adding the args here onto the _start_ of the list
            # so the args are (exchange, handler, channel) not (channel, exchange, handler)
            chl = connection.channel(on_open_callback=partial(Command.connect_channel,
                                                              EXCHANGE_MAPPINGS[i]["exchange"],
                                                              EXCHANGE_MAPPINGS[i]["handler"]),
                                     )
            chl.add_on_close_callback(self.channel_closed)
            chl.add_on_cancel_callback(self.channel_closed)

    def channel_closed(self, connection, error=None):
        logger.error("RabbitMQ connection failed: {0}".format(str(error)))
        self.exit_code = 1
        self.runloop.stop()

    def connection_closed(self, connection, error=None):
        """
        async callback that is invoked when the connection fails.
        print an error and shut down, this will then get detected as a crash-loop state
        :param connection:
        :param error:
        :return:
        """
        logger.error("RabbitMQ connection failed: {0}".format(str(error)))
        self.exit_code = 1
        connection.ioloop.stop()

    def handle(self):
        connection = pika.SelectConnection(
            pika.ConnectionParameters(
                host=os.environ.get("RABBITMQ_HOST"),
                port=int(os.environ.get("RABBITMQ_PORT", 5672)),
                virtual_host=os.environ.get("RABBITMQ_VHOST", "/"),
                credentials=pika.PlainCredentials(username=os.environ.get("RABBITMQ_USER"), password=os.environ.get("RABBITMQ_PASSWD")),
                connection_attempts=int(os.environ.get("RABBITMQ_CONNECTION_ATTEMPTS", 3)),
                retry_delay=int(os.environ.get("RABBITMQ_RETRY_DELAY", 3))
            ),
            on_open_callback=self.channel_opened,
            on_close_callback=self.connection_closed,
            on_open_error_callback=self.connection_closed,
        )

        self.runloop = connection.ioloop

        def on_quit(signum, frame):
            logger.info("Caught signal {0}, exiting...".format(signum))
            connection.ioloop.stop()

        signal.signal(signal.SIGINT, on_quit)
        signal.signal(signal.SIGTERM, on_quit)

        connection.ioloop.start()
        logger.info("terminated")
        sys.exit(self.exit_code)

if __name__=="__main__":
    cmd = Command()
    cmd.handle()