from common.middleware.middleware import Middleware
from common.rabbit.rabbit_exchange import RabbitExchange
from common.rabbit.rabbit_queue import RabbitQueue

DATA_EXCHANGE = 'data'
DATA_EXCHANGE_TYPE = 'direct'
STATIONS_QUEUE_NAME = 'stations'
JOINER_BY_YEAR_CITY_STATION_ID_EXCHANGE = 'join_by_year_city_station_id_stations'
JOINER_BY_YEAR_CITY_STATION_ID_EXCHANGE_TYPE = 'fanout'
FILTER_BY_CITY_ROUTING_KEY = 'filter_by_city_stations'


class StationsConsumerMiddleware(Middleware):
    def __init__(self, hostname, producers):
        super(StationsConsumerMiddleware, self).__init__(hostname)

        self._input_queue = RabbitQueue(
            self._rabbit_connection,
            queue_name=STATIONS_QUEUE_NAME,
            bind_exchange=DATA_EXCHANGE,
            bind_exchange_type=DATA_EXCHANGE_TYPE,
            routing_key=STATIONS_QUEUE_NAME,
            producers=producers,
        )

        self._joiner_exchange = RabbitExchange(
            self._rabbit_connection,
            exchange_name=JOINER_BY_YEAR_CITY_STATION_ID_EXCHANGE,
            exchange_type=JOINER_BY_YEAR_CITY_STATION_ID_EXCHANGE_TYPE,
        )

        self._filter_exchange = RabbitExchange(
            self._rabbit_connection,
        )

    def receive_stations(self, on_message_callback, on_end_message_callback):
        super().receive(self._input_queue, on_message_callback, on_end_message_callback, auto_ack=False)

    def send_joiner_message(self, message):
        super().send(message, self._joiner_exchange)

    def send_filter_message(self, message):
        super().send(message, self._filter_exchange, FILTER_BY_CITY_ROUTING_KEY)
