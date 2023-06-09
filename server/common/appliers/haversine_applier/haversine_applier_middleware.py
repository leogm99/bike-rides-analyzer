import logging

from common.middleware.middleware import Middleware
from common.rabbit.rabbit_exchange import RabbitExchange
from common.rabbit.rabbit_queue import RabbitQueue

QUEUE_NAME = 'haversine_applier'
OUTPUT_ROUTING_KEY_PREFIX = lambda n: f'aggregate_trip_distance_{n}'


class HaversineApplierMiddleware(Middleware):
    def __init__(self, hostname: str, producers: int):
        super().__init__(hostname)
        self._input_queue = RabbitQueue(
            self._rabbit_connection,
            queue_name=QUEUE_NAME,
            producers=producers
        )

        self._output_exchange = RabbitExchange(
            self._rabbit_connection,
        )

    def receive_trips(self, on_message_callback, on_end_message_callback):
        self._input_queue.consume(on_message_callback, on_end_message_callback)

    def send_aggregator_message(self, message, aggregator_id):
        self._output_exchange.publish(message, routing_key=OUTPUT_ROUTING_KEY_PREFIX(aggregator_id))
