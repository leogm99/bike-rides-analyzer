from common.middleware.middleware import Middleware
from common.rabbit.rabbit_exchange import RabbitExchange
from common.rabbit.rabbit_queue import RabbitQueue


QUEUE_NAME_PREFIX = lambda n: f'aggregate_trip_distance_{n}'
FILTER_BY_DISTANCE_ROUTING_KEY = 'filter_by_distance'


class AggregateTripDistanceMiddleware(Middleware):
    def __init__(self, hostname: str, producers: int, aggregate_id: int):
        super().__init__(hostname)
        self._input_queue = RabbitQueue(
            self._rabbit_connection,
            queue_name=QUEUE_NAME_PREFIX(aggregate_id),
            producers=producers
        )
        self._output_exchange = RabbitExchange(
            self._rabbit_connection,
        )

    def receive_trips_distances(self, on_message_callback, on_end_message_callback):
        self._input_queue.consume(on_message_callback, on_end_message_callback)

    def send_filter_message(self, message):
        self._output_exchange.publish(message, routing_key=FILTER_BY_DISTANCE_ROUTING_KEY)
