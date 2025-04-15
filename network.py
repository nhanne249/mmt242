import socket
import logging
from typing import Union

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class NetworkUtils:
    """
    Lớp này cung cấp các hàm hỗ trợ cho giao tiếp socket.
    """
    @staticmethod
    def send_data(conn: socket.socket, data: Union[str, bytes]) -> None:
        """
        Gửi dữ liệu qua kết nối socket một cách đáng tin cậy.
        Send data reliably over a socket connection.
        :param conn: Socket connection object.
        :param data: Data to send (string or bytes).
        """
        if isinstance(data, str):
            data = data.encode()
        try:
            conn.sendall(data)
            logging.info("Data sent successfully.")
        except (socket.error, Exception) as e:
            logging.error(f"Failed to send data: {e}")
            raise

    @staticmethod
    def receive_data(conn: socket.socket, buffer_size: int = 1024) -> str:
        """
        Nhận dữ liệu qua kết nối socket một cách đáng tin cậy.
        Receive data reliably over a socket connection.
        :param conn: Socket connection object.
        :param buffer_size: Size of each data chunk to receive.
        :return: Received data as a string.
        """
        data = b""
        try:
            while True:
                chunk = conn.recv(buffer_size)
                if not chunk:
                    break
                data += chunk
            logging.info("Data received successfully.")
            return data.decode()
        except (socket.error, Exception) as e:
            logging.error(f"Failed to receive data: {e}")
            raise

    @staticmethod
    def create_server_socket(ip: str, port: int) -> socket.socket:
        """
        Tạo và bind một socket server.
        Create and bind a server socket.
        :param ip: IP address to bind the socket.
        :param port: Port to bind the socket.
        :return: Server socket object.
        """
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((ip, port))
            server.listen(5)
            logging.info(f"Server socket created on {ip}:{port}")
            return server
        except (socket.error, Exception) as e:
            logging.error(f"Failed to create server socket: {e}")
            raise

    @staticmethod
    def create_client_socket(ip: str, port: int) -> socket.socket:
        """
        Tạo một socket client và kết nối đến server.
        Create a client socket and connect to a server.
        :param ip: Server IP address.
        :param port: Server port.
        :return: Client socket object.
        """
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ip, port))
            logging.info(f"Connected to server at {ip}:{port}")
            return client
        except (socket.error, Exception) as e:
            logging.error(f"Failed to connect to server: {e}")
            raise
