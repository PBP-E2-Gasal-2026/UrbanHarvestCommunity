"""AMQP boundary. Each instance belongs to exactly one thread."""
from dataclasses import dataclass
import json
import uuid

import pika

from .openrouter import load_json

class BrokerUnavailable(Exception):
    pass

@dataclass(frozen=True)
class Delivery:
    tag: object
    job_id: uuid.UUID

class RabbitTransport:
    queue = "llm.search"

    def __init__(self, url, *, connection_factory=None):
        self.url = url
        self.connection_factory = connection_factory or pika.BlockingConnection
        self.connection = None
        self.channel = None

    def connect(self):
        if not self.url:
            raise BrokerUnavailable("RabbitMQ not configured")
        try:
            params = pika.URLParameters(self.url)
            params.socket_timeout = 3
            params.stack_timeout = 5
            params.blocked_connection_timeout = 5
            params.connection_attempts = 1
            # Longer than the two bounded provider calls while the consumer is busy.
            params.heartbeat = 180
            self.connection = self.connection_factory(params)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue, durable=True)
            self.channel.basic_qos(prefetch_count=1)
            self.channel.confirm_delivery()
        except (pika.exceptions.AMQPError, OSError, ValueError) as exc:
            self.close()
            raise BrokerUnavailable("RabbitMQ unavailable") from exc

    def publish(self, job_id):
        try:
            self.channel.basic_publish(exchange="", routing_key=self.queue,
                body=json.dumps({"job_id": str(job_id)}).encode(), mandatory=True,
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=2))
        except (pika.exceptions.AMQPError, OSError) as exc:
            raise BrokerUnavailable("RabbitMQ publish not confirmed") from exc

    def receive(self):
        try:
            method, properties, body = self.channel.basic_get(queue=self.queue, auto_ack=False)
            if method is None:
                return None
            try:
                if not body or len(body) > 512:
                    raise ValueError("Invalid message length")
                payload = load_json(body.decode("utf-8"))
                if not isinstance(payload, dict) or set(payload) != {"job_id"}:
                    raise ValueError("Invalid message fields")
                job_id = uuid.UUID(payload["job_id"])
            except (ValueError, TypeError, UnicodeError, AttributeError):
                self.channel.basic_ack(delivery_tag=method.delivery_tag)
                return None
            return Delivery(method.delivery_tag, job_id)
        except (pika.exceptions.AMQPError, OSError) as exc:
            raise BrokerUnavailable("RabbitMQ receive failed") from exc

    def ack(self, delivery):
        try:
            self.channel.basic_ack(delivery_tag=delivery.tag)
        except (pika.exceptions.AMQPError, OSError) as exc:
            raise BrokerUnavailable("RabbitMQ acknowledgement failed") from exc

    def maintain(self):
        try:
            self.connection.process_data_events(time_limit=0)
            if self.connection.is_closed:
                raise BrokerUnavailable("RabbitMQ connection closed")
        except (pika.exceptions.AMQPError, OSError) as exc:
            raise BrokerUnavailable("RabbitMQ disconnected") from exc

    def close(self):
        try:
            if self.connection is not None and self.connection.is_open:
                self.connection.close()
        except (pika.exceptions.AMQPError, OSError):
            pass
        finally:
            self.channel = None
            self.connection = None
