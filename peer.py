import socket
import threading
import json
import os
import hashlib
import logging
import time

class Peer:
    def __init__(self, ip, port, tracker_ip, tracker_port):
        self.ip = ip
        self.port = port
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.shared_files = {}  # {filename: filepath}
        self.chunks = {}  # {filename: {chunk_index: chunk_data}}
        self.downloaded_chunks = {}  # {filename: set(chunk_indices)}
        self.lock = threading.Lock()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    def register_file(self, filepath):
        """Register a file with the tracker."""
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        chunk_size = 1024 * 1024  # 1 MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size

        with open(filepath, "rb") as f:
            self.chunks[filename] = {}
            for i in range(total_chunks):
                chunk_data = f.read(chunk_size)
                self.chunks[filename][i] = chunk_data

        self.shared_files[filename] = filepath
        request = {
            "action": "register",
            "filename": filename,
            "total_chunks": total_chunks
        }
        self.send_to_tracker(request)
        logging.info(f"Registered file '{filename}' with tracker.")

    def query_tracker(self, filename):
        """Query the tracker for available peers for a file."""
        request = {"action": "query", "filename": filename}
        response = self.send_to_tracker(request)
        return json.loads(response)

    def download_file(self, filename, peer_list):
        """Download a file by fetching chunks from multiple peers."""
        total_chunks = len(peer_list)
        self.downloaded_chunks[filename] = set()

        def download_chunk(chunk_index, peer_ip):
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.connect((peer_ip, self.port))
                request = {"action": "get_chunk", "filename": filename, "chunk_index": chunk_index}
                conn.send(json.dumps(request).encode())
                chunk_data = conn.recv(1024 * 1024)  # 1 MB
                with self.lock:
                    self.downloaded_chunks[filename].add(chunk_index)
                conn.close()
                logging.info(f"Downloaded chunk {chunk_index} of '{filename}' from {peer_ip}.")
            except Exception as e:
                logging.error(f"Failed to download chunk {chunk_index} from {peer_ip}: {e}")

        threads = []
        for chunk_index, peer_ip in enumerate(peer_list):
            thread = threading.Thread(target=download_chunk, args=(chunk_index, peer_ip))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Reassemble the file
        with open(f"downloaded_{filename}", "wb") as f:
            for i in range(total_chunks):
                f.write(self.chunks[filename][i])
        logging.info(f"File '{filename}' downloaded and reassembled.")

        # Notify tracker of downloaded chunks
        self.update_tracker(filename)

    def update_tracker(self, filename):
        """Update the tracker with newly downloaded chunks."""
        request = {
            "action": "update",
            "filename": filename,
            "chunks": list(self.downloaded_chunks[filename])
        }
        self.send_to_tracker(request)
        logging.info(f"Updated tracker with downloaded chunks for '{filename}'.")

    def upload_chunk(self, conn, request):
        """Upload a requested chunk to a peer."""
        filename = request["filename"]
        chunk_index = request["chunk_index"]
        with self.lock:
            chunk_data = self.chunks[filename][chunk_index]
        conn.send(chunk_data)
        logging.info(f"Uploaded chunk {chunk_index} of '{filename}'.")

    def handle_peer_request(self, conn):
        """Handle incoming requests from other peers."""
        try:
            data = conn.recv(1024).decode()
            request = json.loads(data)
            action = request.get("action")

            if action == "get_chunk":
                self.upload_chunk(conn, request)
            else:
                logging.warning(f"Unknown action '{action}' from peer.")
        except Exception as e:
            logging.error(f"Error handling peer request: {e}")
        finally:
            conn.close()

    def send_to_tracker(self, request):
        """Send a request to the tracker and return the response."""
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((self.tracker_ip, self.tracker_port))
            conn.send(json.dumps(request).encode())
            response = conn.recv(1024).decode()
            conn.close()
            return response
        except Exception as e:
            logging.error(f"Failed to communicate with tracker: {e}")
            return None

    def start(self):
        """Start the peer server to handle incoming requests."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        logging.info(f"Peer running on {self.ip}:{self.port}")

        while True:
            conn, addr = server.accept()
            logging.info(f"Connection from {addr}")
            threading.Thread(target=self.handle_peer_request, args=(conn,)).start()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Peer Node")
    parser.add_argument("--ip", required=True, help="Peer IP address")
    parser.add_argument("--port", type=int, required=True, help="Peer port")
    parser.add_argument("--tracker-ip", required=True, help="Tracker IP address")
    parser.add_argument("--tracker-port", type=int, required=True, help="Tracker port")
    args = parser.parse_args()

    peer = Peer(args.ip, args.port, args.tracker_ip, args.tracker_port)
    threading.Thread(target=peer.start).start()

    # Example usage: Register a file
    # peer.register_file("path/to/file")
