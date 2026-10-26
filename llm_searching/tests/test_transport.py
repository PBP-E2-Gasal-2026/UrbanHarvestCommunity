import json
import uuid
from types import SimpleNamespace
from unittest.mock import Mock
from django.test import SimpleTestCase
from llm_searching.transport import RabbitTransport, BrokerUnavailable

class TransportTests(SimpleTestCase):
    def make_transport(self):
        channel = Mock()
        channel.basic_get.return_value = (None, None, None)
        connection = Mock()
        connection.channel.return_value = channel
        transport = RabbitTransport("amqp://guest:guest@localhost:5672/%2F", connection_factory=lambda p: connection)
        transport.connect()
        return transport, channel

    def test_confirmed_persistent_id_only_publication(self):
        transport, channel = self.make_transport()
        job_id = uuid.uuid4()
        transport.publish(job_id)
        args = channel.basic_publish.call_args.kwargs
        self.assertEqual(json.loads(args["body"]), {"job_id": str(job_id)})
        self.assertTrue(args["mandatory"])
        self.assertEqual(args["properties"].delivery_mode, 2)
        channel.confirm_delivery.assert_called_once()
        channel.queue_declare.assert_called_once_with(queue="llm.search", durable=True)
        transport.close()

    def test_poison_message_dropped_without_database_access(self):
        transport, channel = self.make_transport()
        channel.basic_get.return_value = (SimpleNamespace(delivery_tag=42), None, b'{"sql":"DELETE"}')
        self.assertIsNone(transport.receive())
        channel.basic_ack.assert_called_once_with(delivery_tag=42)
        transport.close()

    def test_missing_configuration_is_recoverable(self):
        with self.assertRaises(BrokerUnavailable):
            RabbitTransport("").connect()
