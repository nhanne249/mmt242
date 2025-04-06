import socket
import threading
import json
import logging

class Tracker:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.files = {}  # {filename: {chunk_index: [peer_ips]}}
        self.lock = threading.Lock()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    def handle_client(self, conn, addr):
        try:
            data = self.receive_data(conn)
            if not data:
                logging.warning(f"Empty request from {addr}")
                return

            request = json.loads(data)
            action = request.get("action")

            if action == "register":
                self.register_file(request, addr[0])
            elif action == "query":
                response = self.query_file(request)
                conn.send(json.dumps(response).encode())
            elif action == "update":
                self.update_chunks(request, addr[0])
            else:
                logging.warning(f"Unknown action '{action}' from {addr}")
        except json.JSONDecodeError:
            logging.error(f"Malformed request from {addr}")
        except Exception as e:
            logging.error(f"Error handling client {addr}: {e}")
        finally:
            conn.close()

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
        logging.info(f"Registered file: {filename} from {peer_ip}")

    def query_file(self, request):
        filename = request["filename"]
        with self.lock:
            response = self.files.get(filename, {})
        logging.info(f"Query for file: {filename}")
        return response

    def update_chunks(self, request, peer_ip):
        filename = request["filename"]
        chunks = request["chunks"]
        with self.lock:
            for chunk in chunks:
                if peer_ip not in self.files[filename][chunk]:
                    self.files[filename][chunk].append(peer_ip)
        logging.info(f"Updated chunks for {filename} from {peer_ip}")

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        logging.info(f"Tracker running on {self.ip}:{self.port}")

        while True:
            conn, addr = server.accept()
            logging.info(f"Connection from {addr}")
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tracker Server")
    parser.add_argument("--ip", required=True, help="Tracker IP address")
    parser.add_argument("--port", type=int, required=True, help="Tracker port")
    args = parser.parse_args()

    tracker = Tracker(args.ip, args.port)
    tracker.start()
