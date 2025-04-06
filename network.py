import socket
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class NetworkUtils:
    @staticmethod
    def send_data(conn, data):
        """
        Send data reliably over a socket connection.
        :param conn: Socket connection object.
        :param data: Data to send (string or bytes).
        """
        if isinstance(data, str):
            data = data.encode()
        try:
            conn.sendall(data)
            logging.info("Data sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send data: {e}")
            raise

    @staticmethod
    def receive_data(conn, buffer_size=1024):
        """
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
        except Exception as e:
            logging.error(f"Failed to receive data: {e}")
            raise

    @staticmethod
    def create_server_socket(ip, port):
        """
        Create and bind a server socket.
        :param ip: IP address to bind the socket.
        :param port: Port to bind the socket.
        :return: Server socket object.
        """
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((ip, port))
            server.listen(5)
            logging.info(f"Server socket created on {ip}:{port}")
            return server
        except Exception as e:
            logging.error(f"Failed to create server socket: {e}")
            raise

    @staticmethod
    def create_client_socket(ip, port):
        """
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
        except Exception as e:
            logging.error(f"Failed to connect to server: {e}")
            raise
