import logging

from common.dag_node import DAGNode
from common.rabbit.rabbit_exchange import RabbitExchange
from common.rabbit.rabbit_queue import RabbitQueue
from collections import defaultdict

QUEUE_NAME = 'metrics_consumer'
LOADER_ROUTING_KEY = 'loader_metrics_receiver'


class MetricsConsumer(DAGNode):
    def __init__(self,
                 rabbit_hostname: str,
                 producers: int = 1):
        super().__init__(rabbit_hostname)
        logging.info(f'expected EOFS: {producers}')
        self._input_queue = RabbitQueue(
            self._rabbit_connection,
            queue_name=QUEUE_NAME,
            producers=producers
        )
        self._output_exchange = RabbitExchange(
            self._rabbit_connection,
        )
        self._metrics = defaultdict(list)

    def run(self):
        self._input_queue.consume(self.on_message_callback, self.on_producer_finished)
        self._rabbit_connection.start_consuming()

    def on_message_callback(self, message, delivery_tag):
        if message['payload'] == 'EOF':
            return
        self._metrics[message['type']].append(message['payload'])

    def on_producer_finished(self, message, delivery_tag):
        logging.info(self._metrics)
