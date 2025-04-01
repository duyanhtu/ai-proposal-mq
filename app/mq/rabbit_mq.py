import pika
import json
import time


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
    ):
        self.host = host
        self.port = port
        self.durable = durable
        self.credentials = pika.PlainCredentials(user, password)
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        """Kết nối đến RabbitMQ."""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host, port=self.port, credentials=self.credentials
                )
            )
            self.channel = self.connection.channel()
            print(
                f" [*] Connected to RabbitMQ on {self.host}:{self.port}, Durable: {self.durable}"
            )
        except Exception as e:
            print(f" [!] Connection error: {e}")

    def publish(self, queue, message):
        """Gửi tin nhắn đến queue."""
        if not self.channel or self.connection.is_closed:
            self._connect()

        try:
            # Khai báo queue với durable=True
            self.channel.queue_declare(queue=queue, durable=self.durable)
            # self.channel.queue_declare(queue=queue)

            # Chuyển dict sang JSON string
            body = json.dumps(message)

            # Gửi message với delivery_mode=2 (persistent)
            self.channel.basic_publish(
                exchange="",
                routing_key=queue,
                body=body.encode("utf-8"),
                properties=pika.BasicProperties(delivery_mode=2 if self.durable else 1)
            )
            print(f" [x] Sent: {message}")
        except Exception as e:
            print(f" [!] Publish error: {e}")

    def start_consumer(self, queue, call_back):
        """Bắt đầu consumer, lắng nghe queue."""
        while True:
            try:
                if not self.channel or self.connection.is_closed:
                    self._connect()

                # Khai báo queue để đảm bảo nó tồn tại
                self.channel.queue_declare(queue=queue, durable=self.durable)

                self.channel.basic_consume(
                    queue=queue, on_message_callback=call_back, auto_ack=True
                )

                print(f" [*] Waiting for messages on {queue}. To exit press CTRL+C")
                self.channel.start_consuming()

            except (
                pika.exceptions.AMQPConnectionError,
                pika.exceptions.ChannelClosedByBroker,
            ) as e:
                print(f" [!] Connection lost: {e}. Reconnecting in 5 seconds...")
                time.sleep(5)
                self._connect()

            except KeyboardInterrupt:
                print(" [!] Consumer stopped.")
                if self.connection:
                    self.connection.close()
                break
