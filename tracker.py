import socket
import threading
import json
import logging
from colorama import Fore, Style

class Tracker:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.files = {}  # {filename: {chunk_index: [peer_ips]}}
        self.lock = threading.Lock()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    def handle_client(self, conn, addr):
        log_message('INFO', f"Handling client {addr}")  # Log interaction with peer
        try:
            data = self.receive_data(conn)
            if not data:
                log_message('WARNING', f"Empty request from {addr}")
                return

            request = json.loads(data)
            action = request.get("action")

            if action == "register_torrent":
                log_message('INFO', f"Action: register_torrent from {addr}")  # Log action
                self.register_torrent(request, addr[0])
            elif action == "query_torrent":
                log_message('INFO', f"Action: query_torrent from {addr}")  # Log action
                response = self.query_torrent(request)
                conn.send(json.dumps(response).encode())
            elif action == "register":
                log_message('INFO', f"Action: register from {addr}")  # Log action
                self.register_file(request, addr[0])
            elif action == "query":
                log_message('INFO', f"Action: query from {addr}")  # Log action
                response = self.query_file(request)
                conn.send(json.dumps(response).encode())
            elif action == "update":
                log_message('INFO', f"Action: update from {addr}")  # Log action
                self.update_chunks(request, addr[0])
            else:
                log_message('WARNING', f"Unknown action '{action}' from {addr}")
        except json.JSONDecodeError:
            log_message('ERROR', f"Malformed request from {addr}")
        except Exception as e:
            log_message('ERROR', f"Error handling client {addr}: {e}")
        finally:
            conn.close()
            log_message('INFO', f"Connection with {addr} closed")  # Log connection closure

    def receive_data(self, conn):
        """Receive data in chunks to handle larger payloads."""
        data = b""
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data += chunk
        return data.decode()

    def register_file(self, request, peer_ip):
        filename = request["filename"]
        total_chunks = request["total_chunks"]
        with self.lock:
            if filename not in self.files:
                self.files[filename] = {i: [] for i in range(total_chunks)}
        log_message('INFO', f"Registered file: {filename} from {peer_ip}")

    def query_file(self, request):
        filename = request["filename"]
        with self.lock:
            response = self.files.get(filename, {})
        log_message('INFO', f"Query for file: {filename}")
        return response

    def update_chunks(self, request, peer_ip):
        filename = request["filename"]
        chunks = request["chunks"]
        with self.lock:
            for chunk in chunks:
                if peer_ip not in self.files[filename][chunk]:
                    self.files[filename][chunk].append(peer_ip)
        log_message('INFO', f"Updated chunks for {filename} from {peer_ip}")

    def register_torrent(self, request, peer_ip):
        """Register a file using .torrent metadata."""
        filename = request["filename"]
        pieces = request["pieces"]
        with self.lock:
            if filename not in self.files:
                self.files[filename] = {i: [] for i in range(len(pieces))}
        log_message('INFO', f"Registered .torrent file: {filename} from {peer_ip}")

    def query_torrent(self, request):
        """Query the tracker for peers using .torrent metadata."""
        filename = request["filename"]
        with self.lock:
            response = self.files.get(filename, {})
        log_message('INFO', f"Query for .torrent file: {filename}")
        return response

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        log_message('INFO', f"Tracker running on {self.ip}:{self.port}")

        while True:
            conn, addr = server.accept()
            log_message('INFO', f"Connection from {addr}")
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

def log_message(level, message):
    if level == 'INFO':
        print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} {message}")
    elif level == 'WARNING':
        print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {message}")
    elif level == 'ERROR':
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")
    else:
        print(f"{Fore.CYAN}[{level}]{Style.RESET_ALL} {message}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tracker Server")
    parser.add_argument("--ip", required=True, help="Tracker IP address")
    parser.add_argument("--port", type=int, required=True, help="Tracker port")
    args = parser.parse_args()

    tracker = Tracker(args.ip, args.port)
    tracker.start()
