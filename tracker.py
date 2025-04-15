import socket
import threading
import json
import logging
import os
from colorama import Fore, Style

# Configure logging to display logs in the console
logging.basicConfig(
    level=logging.INFO,  # Set the logging level to INFO
    format=f"{Fore.CYAN}%(asctime)s{Style.RESET_ALL} - %(levelname)s - %(message)s"
)

# Example log to verify logging setup
logging.info("Tracker logging initialized.")

class Tracker:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.files = {}  # {filename: {chunk_index: [peer_ips]}}
        self.lock = threading.Lock()
        self.temp_file = "temp.json"  # File to store tracker data persistently
        self.load_files_from_temp()

    def load_files_from_temp(self):
        """Load tracker data from the temp.json file."""
        if os.path.exists(self.temp_file):
            try:
                with open(self.temp_file, "r") as f:
                    self.files = json.load(f)
                logging.info("Loaded tracker data from temp.json.")
            except Exception as e:
                logging.error(f"Failed to load tracker data from temp.json: {e}")

    def save_files_to_temp(self):
        """Save tracker data to the temp.json file."""
        try:
            with open(self.temp_file, "w") as f:
                json.dump(self.files, f)
            logging.info("Saved tracker data to temp.json.")
        except Exception as e:
            logging.error(f"Failed to save tracker data to temp.json: {e}")

    def handle_client(self, conn, addr):
        logging.info(f"New connection from {addr}")  # Log every new connection
        try:
            data = self.receive_data(conn)
            logging.info(f"Received raw data from {addr}: {data}")  # Log the raw data received from the client
            if not data:
                logging.warning(f"Empty request from {addr}")
                response = {"status": "error", "message": "Empty request"}
                conn.send(json.dumps(response).encode())
                return

            action = data.get("action")

            if action == "register":
                response = self.register_file(data, addr[0])
            elif action == "query":
                response = self.query_file(data)
            elif action == "list_files":
                response = self.list_files()
            elif action == "update":
                response = self.update_chunks(data, addr[0])
            else:
                response = {"status": "error", "message": "Unknown action"}
                logging.warning(f"Unknown action '{action}' from {addr}")

            conn.send(json.dumps(response).encode())
            logging.info(f"Response sent to peer {addr}: {response}")
        except json.JSONDecodeError:
            logging.error(f"Malformed request from {addr}")
            response = {"status": "error", "message": "Malformed request"}
            conn.send(json.dumps(response).encode())
        except Exception as e:
            logging.error(f"Error handling client {addr}: {e}")
            response = {"status": "error", "message": str(e)}
            conn.send(json.dumps(response).encode())
        finally:
            conn.close()
            logging.info(f"Connection with {addr} closed")

    def receive_data(self, conn):
        """Receive metadata and update chunk information."""
        buffer_size = 1024  # Default buffer size

        try:
            # Step 1: Receive metadata (e.g., action, filename, total_chunks)
            metadata = conn.recv(buffer_size).decode()
            logging.info(f"Received metadata: {metadata}")

            metadata_json = json.loads(metadata)
            total_chunks = metadata_json.get("total_chunks")
            filename = metadata_json.get("filename")
            peer_ip = metadata_json.get("peer_ip")

            # Validate filename and peer_ip
            if filename == "unknown" or peer_ip == "unknown":
                logging.warning(f"Invalid metadata received: filename='{filename}', peer_ip='{peer_ip}'")
                return None

            logging.info(f"Registering file '{filename}' with {total_chunks} chunks from peer {peer_ip}.")

            # Step 2: Update tracker information for the file and chunks
            with self.lock:
                if filename not in self.files:
                    self.files[filename] = {i: [] for i in range(total_chunks)}

                for chunk_index in range(total_chunks):
                    if peer_ip not in self.files[filename][chunk_index]:
                        self.files[filename][chunk_index].append(peer_ip)
                        logging.info(f"Chunk {chunk_index} of file '{filename}' registered for peer {peer_ip}.")

            return metadata_json  # Return the parsed metadata

        except Exception as e:
            logging.error(f"Error while receiving data: {e}")
            return None

    def register_file(self, request, peer_ip):
        filename = request.get("filename")
        total_chunks = request.get("total_chunks")

        # Validate filename and total_chunks
        if not filename or filename == "unknown" or not isinstance(total_chunks, int):
            logging.warning(f"Invalid file registration attempt: filename='{filename}', total_chunks='{total_chunks}'")
            return {"status": "error", "message": "Invalid file registration"}

        with self.lock:
            if filename not in self.files:
                self.files[filename] = {i: [] for i in range(total_chunks)}
            for chunk_index in range(total_chunks):
                if peer_ip not in self.files[filename][chunk_index]:
                    self.files[filename][chunk_index].append(peer_ip)

        self.save_files_to_temp()  # Save updated data to temp.json
        logging.info(f"File '{filename}' registered with {total_chunks} chunks by {peer_ip}")
        return {"status": "success", "filename": filename}

    def query_file(self, request):
        filename = request["filename"]
        with self.lock:
            file_info = self.files.get(filename, None)
        if file_info is None:
            return {"status": "error", "message": "File not found"}
        return {"status": "success", "file_info": file_info}

    def update_chunks(self, request, peer_ip):
        """Update the tracker with chunks downloaded by a peer."""
        filename = request["filename"]
        chunks = request["chunks"]
        with self.lock:
            if filename not in self.files:
                logging.warning(f"File '{filename}' not found in tracker.")
                return {"status": "error", "message": "File not found"}

            for chunk in chunks:
                chunk_index = int(chunk)
                if peer_ip not in self.files[filename][chunk_index]:
                    self.files[filename][chunk_index].append(peer_ip)

        self.save_files_to_temp()  # Save updated data to temp.json
        logging.info(f"Updated chunks for '{filename}' from peer {peer_ip}.")
        return {"status": "success"}

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

    def list_files(self):
        """Return a list of all files currently tracked."""
        with self.lock:
            file_list = list(self.files.keys())
        return {"status": "success", "files": file_list}

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
