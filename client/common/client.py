import csv
import socket
import logging
import signal
import json
from multiprocessing import Process, Lock
from common.utils import get_file_paths_by_city_and_type
from typing import Dict
from common_utils.utils import send_string_message, receive_string_message, recv_n_bytes
from common_utils.protocol.protocol import Protocol
from common_utils.protocol.payload import Payload
from common_utils.protocol.message import Message
from time import sleep


BATCH_SIZE = 500


class Client:
    def __init__(self, server_addr: str, server_port: int, data_path: str, output_path: str):
        """
        :param server_addr: Server ip address.
        :param server_port: Server TCP listening port.
        :param data_path: Path to the data directory containing cities' data.
        :param output_path: Path in which to save the metrics.
        """
        self.closed = False
        self._socket = socket.socket(family=socket.AF_INET,
                                     type=socket.SOCK_STREAM)
        self._data_path = data_path
        self._output_path = output_path
        self._rwlock = Lock()
        try:
            logging.info('action: init_client | status: in progress')
            self._socket.connect((server_addr, server_port))
            logging.info('action: init_client | status: success')
        except socket.error as e:
            logging.error(f'action: init_client | status: failed | reason: {str(e)}')
            raise e
        signal.signal(signal.SIGTERM, lambda *_: self.stop())

    def run(self):
        logging.info('action: register_sigterm | status: success')
        files_paths_by_city_and_type = get_file_paths_by_city_and_type(self._data_path)

        weather_sender = Process(target=self.__send_csv_data,
                                 args=(files_paths_by_city_and_type, 'weather', self.__send_all_process_safe))
        stations_sender = Process(target=self.__send_csv_data,
                                  args=(files_paths_by_city_and_type, 'stations', self.__send_all_process_safe))

        logging.debug(f'action: sending_static_data | status: in progress')
        weather_sender.start()
        stations_sender.start()
        weather_sender.join()
        stations_sender.join()
        if (weather_sender.exitcode != 0) or (stations_sender.exitcode != 0):
            if self.closed:
                logging.info('action: close | status: success | gracefully quitting')
                return
        logging.debug(f'action: sending_static_data | status: success')
        message = Protocol.receive_message(self.__recv_all)
        if not message.is_type('notify') and not message.payload.data == 'ACK':
            self.stop()
            return
        logging.info(f'action: receive-message | message: {message}')
        # reuse the same functions but avoid having to lock with just one process...
        self.__send_csv_data(files_paths_by_city_and_type, 'trips', lambda payload: self._socket.sendall(payload))
        try:
            metrics = Protocol.receive_message(self.__recv_all)
        except BrokenPipeError:
            logging.info('action: receive | status: Connection closed by remote end')
            return
        self.save_metrics(metrics)
        self.stop()

    @staticmethod
    def __send_csv_data(paths_by_city_and_type: Dict[str, Dict[str, str]],
                        data_type: str,
                        send_callback):
        try:
            for city, city_paths in paths_by_city_and_type.items():
                data_path = city_paths[data_type]
                with open(data_path, newline='') as source:
                    reader = csv.DictReader(f=source)
                    Client.read_and_send_batched(reader, city, data_type, send_callback)
            Client.send_eof(data_type, send_callback)
        except BaseException:
            return

    @staticmethod
    def send_eof(data_type, send_callback):
        eof_data = {'type': data_type, 'payload': 'EOF'}
        json_eof_data = json.dumps(eof_data)
        send_string_message(send_callback, json_eof_data, 4)

    @staticmethod
    def read_and_send_batched(reader, city, data_type, send_callback, batch_size=BATCH_SIZE):
        send_buffer = []
        for row in reader:
            row['city'] = city
            send_buffer.append(Payload(data=row))
            if len(send_buffer) == batch_size:
                msg = Message(message_type=data_type, payload=send_buffer)
                # throttle
                sleep(0.001)
                Protocol.send_message(send_callback, msg)
                send_buffer = []
        if len(send_buffer) != 0:
            msg = Message(message_type=data_type, payload=send_buffer)
            Protocol.send_message(send_callback, msg)

    def __send_all_process_safe(self, payload):
        """Process safe send_all"""
        with self._rwlock:
            self._socket.sendall(payload)

    def __recv_all(self, n):
        return recv_n_bytes(self._socket, n)

    def stop(self):
        logging.info('action: stop | status: in progress')
        self.closed = True
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()

    def save_metrics(self, metrics):
        for k, v in metrics.payload.data.items():
            with open(f'{self._output_path}/{k}.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(v[0].keys())
                for row in v:
                    values = []
                    for value in row.values():
                        if isinstance(value, list):
                            values.append(value[0])
                        else:
                            values.append(value)
                    writer.writerow(values)
