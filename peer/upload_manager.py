import socket
import threading
import os

class UploadManager:
    def __init__(self, host, port, shared_files, piece_size=1024):
        self.host = host
        self.port = port
        self.shared_files = shared_files
        self.piece_size = piece_size

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"UploadManager listening on {self.host}:{self.port}")
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connection accepted from {addr}")
            threading.Thread(target=self._handle_client, args=(client_socket, addr)).start()

    def _handle_client(self, client_socket, addr):
        try:
            request = client_socket.recv(1024).decode("utf-8")
            print(f"Request received from {addr}: {request}")
            if request.startswith("GET_PIECE:"):
                _, file_name, piece_index = request.split(":")
                self._send_piece(client_socket, file_name, int(piece_index))
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            print(f"Connection closed with {addr}")

    def _send_piece(self, client_socket, file_name, piece_index):
        if file_name not in self.shared_files:
            client_socket.sendall(b"ERROR:FILE_NOT_FOUND")
            print(f"File not found: {file_name}")
            return
        file_path = self.shared_files[file_name]
        if not os.path.exists(file_path):
            client_socket.sendall(b"ERROR:FILE_NOT_FOUND")
            print(f"File path does not exist: {file_path}")
            return
        with open(file_path, "rb") as f:
            f.seek(piece_index * self.piece_size)
            data = f.read(self.piece_size)
            client_socket.sendall(data)
            print(f"Sent piece {piece_index} of file {file_name} to client")
