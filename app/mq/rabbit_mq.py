import json
import time
from typing import Callable

import pika
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker

from app.config.env import EnvSettings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RabbitMQClient:
    """
    RabbitMQClient - Hỗ trợ Publisher và Consumer với RabbitMQ
    """

    def __init__(
        self,
        host="localhost",
        port=5672,
        user="x",
        password="x",
        durable=True,
        prefetch_count=1
    ):
        self.host = host
        self.port = port
        self.durable = durable
        self.prefetch_count = prefetch_count
        self.credentials = pika.PlainCredentials(user, password)
        self.connection = None
        self.channel = None
        self.reconnect_delay = 5  # Start with 5 seconds delay
        self.max_reconnect_delay = 60  # Maximum delay of 1 minute
        self._connect()

    def _connect(self):
        """Kết nối đến RabbitMQ."""
        try:
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=self.credentials,
                heartbeat=60,  # Heartbeat to detect connection issues
                blocked_connection_timeout=300,  # Timeout for blocked connections
                connection_attempts=3,  # Attempt reconnection on initial connect
                retry_delay=5  # Delay between connection attempts
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            # Reset reconnect delay after successful connection
            self.reconnect_delay = 5
            logger.info(
                f"Connected to RabbitMQ on {self.host}:{self.port}, Durable: {self.durable}"
            )
        except Exception as e:
            logger.error(f"Connection error: {e}")
            # Increase reconnect delay with exponential backoff
            self.reconnect_delay = min(
                self.reconnect_delay * 2, self.max_reconnect_delay)
            raise

    def publish(self, queue, message):
        """Gửi tin nhắn đến queue."""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                if not self.channel or self.connection.is_closed:
                    self._connect()

                # Khai báo queue với durable=True
                self.channel.queue_declare(queue=queue, durable=self.durable)

                # Chuyển dict sang JSON string
                body = json.dumps(message)

                # Gửi message với delivery_mode=2 (persistent)
                self.channel.basic_publish(
                    exchange="",
                    routing_key=queue,
                    body=body.encode("utf-8"),
                    properties=pika.BasicProperties(
                        delivery_mode=2 if self.durable else 1)
                )
                logger.info(f"Sent message to {queue}: {message}")
                return True

            except (AMQPConnectionError, ChannelClosedByBroker) as e:
                retry_count += 1
                logger.warning(
                    f"Publish failed (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(self.reconnect_delay)
                    try:
                        self._connect()
                    except Exception:
                        pass  # Will retry on next attempt
                else:
                    logger.error(
                        f"Failed to publish message after {max_retries} attempts")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error during publish: {e}")
                raise

    def start_consumer(self, queue, callback: Callable, auto_ack=EnvSettings().RABBIT_MQ_AUTO_ACKNOWLEDGE):
        """
        Bắt đầu consumer, lắng nghe queue với retry logic.

        Args:
            queue: Tên queue để listen
            callback: Hàm callback để xử lý message
            auto_ack: True để tự động acknowledge message, False để manual acknowledge
                      (Default: False - manual acknowledgment for safety)
        """
        # Wrap the callback to handle exceptions and acknowledgment
        def wrapped_callback(ch, method, properties, body):
            message_id = method.delivery_tag
            logger.debug(f"Processing message {message_id} from {queue}")

            try:
                # Execute the callback
                result = callback(ch, method, properties, body)

                # Only handle manual acknowledgment if auto_ack is False
                if not auto_ack and ch.is_open:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.debug(f"Manually acknowledged message {message_id}")

                return result
            except Exception as e:
                logger.error(
                    f"Error processing message {message_id}: {e}", exc_info=True)

                # Only handle negative acknowledgment if auto_ack is False and channel is open
                if not auto_ack and ch.is_open:
                    # Negative acknowledgment - requeue the message if it's a temporary failure
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag, requeue=True)
                    logger.debug(f"Nacked and requeued message {message_id}")
                elif not ch.is_open:
                    logger.warning(
                        f"Channel closed, couldn't handle acknowledgment for message {message_id}")

                # Reraise the exception to trigger reconnection
                raise

        while True:
            try:
                if not self.channel or self.connection.is_closed:
                    self._connect()

                # Declare queue
                self.channel.queue_declare(queue=queue, durable=self.durable)

                # Set QoS - only process one message at a time until acknowledged
                # Only apply prefetch if using manual acknowledgment
                if not auto_ack:
                    self.channel.basic_qos(prefetch_count=self.prefetch_count)

                # Start consuming with the specified auto_ack setting
                self.channel.basic_consume(
                    queue=queue,
                    on_message_callback=wrapped_callback,
                    auto_ack=auto_ack
                )

                ack_mode = "automatic" if auto_ack else "manual"
                logger.info(
                    f"Waiting for messages on {queue} with {ack_mode} acknowledgment. To exit press CTRL+C")
                self.channel.start_consuming()

            except KeyboardInterrupt:
                logger.info("Interrupted by user. Shutting down gracefully...")
                if self.channel and self.channel.is_open:
                    self.channel.stop_consuming()
                if self.connection and self.connection.is_open:
                    self.connection.close()
                logger.info("RabbitMQ connection closed cleanly")
                break

            except (AMQPConnectionError, ChannelClosedByBroker) as e:
                logger.warning(
                    f"Connection lost: {e}. Reconnecting in {self.reconnect_delay} seconds...")
                time.sleep(self.reconnect_delay)
                # Update reconnect delay with exponential backoff
                self.reconnect_delay = min(
                    self.reconnect_delay * 2, self.max_reconnect_delay)

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                time.sleep(self.reconnect_delay)
