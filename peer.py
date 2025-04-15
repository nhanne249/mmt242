import socket
import threading
import json
import os
import hashlib
import logging
from config import TORRENT_MAX_SIZE_KB
import tkinter as tk
from tkinter import filedialog

class Peer:
    def __init__(self, ip, port, tracker_ip, tracker_port):
        self.ip = ip
        self.port = port
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.shared_files = {}  # {filename: filepath}
        self.chunks = {}  # {filename: {chunk_index: chunk_data}}
        self.downloaded_chunks = {}  # {filename: set(chunk_indices)}
        self.active_downloads = {}  # {filename: threading.Thread}
        self.lock = threading.Lock()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    def register_file(self, filepath):
        """Register a file with the tracker."""
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        chunk_size = TORRENT_MAX_SIZE_KB * 1024  # Configurable chunk size
        total_chunks = (file_size + chunk_size - 1) // chunk_size

        # Split the file into chunks and store them in the 'store' folder
        os.makedirs("store", exist_ok=True)
        with open(filepath, "rb") as f:
            for i in range(total_chunks):
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    logging.warning(f"Chunk {i} of file '{filename}' is empty. Check the source file.")
                chunk_path = os.path.join("store", f"{filename}.torrent{i}")
                with open(chunk_path, "wb") as chunk_file:
                    chunk_file.write(chunk_data)
                logging.info(f"Chunk {i} of file '{filename}' created at '{chunk_path}'.")

        self.shared_files[filename] = filepath
        request = {
            "action": "register",
            "filename": filename,
            "total_chunks": total_chunks,
            "peer_ip": self.ip  # Include peer's IP address
        }
        response = self.send_to_tracker(request)
        if response:
            try:
                response_data = json.loads(response)
                if response_data.get("status") == "success" and response_data.get("filename") == filename:
                    logging.info(f"Registered file '{filename}' with tracker successfully.")
                    return filename  # Return the filename to GUI
                else:
                    logging.error(f"Tracker responded with an error for file '{filename}': {response_data}")
            except json.JSONDecodeError:
                logging.error(f"Invalid JSON response from tracker for file '{filename}': {response}")
        else:
            logging.error(f"Failed to register file '{filename}' with tracker.")
        return None

    def query_tracker(self, filename):
        """Query the tracker for available peers for a file."""
        request = {"action": "query", "filename": filename}
        response = self.send_to_tracker(request)
        return json.loads(response)

    def download_file(self, filename, peer_chunks, save_path, progress_callback=None):
        """Download a file by fetching chunks from multiple peers."""
        if filename in self.active_downloads:
            logging.warning(f"Download for '{filename}' is already in progress.")
            return

        def download_task():
            total_chunks = len(peer_chunks)
            self.downloaded_chunks[filename] = set()

            def download_chunk(chunk_index, peer_ip):
                try:
                    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    conn.connect((peer_ip, self.port))
                    request = {"action": "get_chunk", "filename": filename, "chunk_index": chunk_index}
                    conn.send(json.dumps(request).encode())

                    # Receive the entire chunk
                    chunk_data = b""
                    while len(chunk_data) < TORRENT_MAX_SIZE_KB * 1024:  # Configurable chunk size
                        packet = conn.recv(TORRENT_MAX_SIZE_KB * 1024 - len(chunk_data))
                        if not packet:
                            break
                        chunk_data += packet

                    if not chunk_data:
                        logging.warning(f"Received empty chunk {chunk_index} from {peer_ip}.")
                    else:
                        logging.info(f"Received chunk {chunk_index} from {peer_ip}, size: {len(chunk_data)} bytes.")

                    # Save the chunk to the 'data' folder instead of 'store'
                    chunk_path = os.path.join("data", f"{filename}.torrent{chunk_index}")
                    os.makedirs(os.path.dirname(chunk_path), exist_ok=True)  # Ensure the 'data' folder exists
                    with open(chunk_path, "wb") as chunk_file:
                        chunk_file.write(chunk_data)

                    with self.lock:
                        self.downloaded_chunks[filename].add(chunk_index)

                    # Update progress callback if provided
                    if progress_callback:
                        progress_callback(len(self.downloaded_chunks[filename]), total_chunks)

                    logging.info(f"Downloaded chunk {chunk_index} of '{filename}' from {peer_ip} and saved to 'data' folder.")
                    conn.close()
                except Exception as e:
                    logging.error(f"Failed to download chunk {chunk_index} from {peer_ip}: {e}")

            threads = []
            for chunk_index, peers in peer_chunks.items():
                for peer_ip in peers:
                    if chunk_index not in self.downloaded_chunks[filename]:
                        thread = threading.Thread(target=download_chunk, args=(chunk_index, peer_ip))
                        threads.append(thread)
                        thread.start()

            for thread in threads:
                thread.join()

            # Reassemble the file
            os.makedirs(os.path.dirname(save_path), exist_ok=True)  # Ensure directory exists
            with open(save_path, "wb") as f:  # Write in binary mode
                for i in range(total_chunks):
                    chunk_path = os.path.join("data", f"{filename}.torrent{i}")
                    if os.path.exists(chunk_path):
                        with open(chunk_path, "rb") as chunk_file:  # Read in binary mode
                            f.write(chunk_file.read())
                    else:
                        logging.error(f"Missing chunk {i} for '{filename}'. File may be incomplete.")
            logging.info(f"File '{filename}' downloaded and reassembled at {save_path}.")

            # Notify tracker of downloaded chunks
            self.update_tracker(filename)

            # Remove from active downloads
            with self.lock:
                del self.active_downloads[filename]

        # Start the download task in a new thread
        download_thread = threading.Thread(target=download_task)
        self.active_downloads[filename] = download_thread
        download_thread.start()

    def update_tracker(self, filename):
        """Update the tracker with newly downloaded chunks."""
        request = {
            "action": "update",
            "filename": filename,
            "chunks": list(self.downloaded_chunks[filename])
        }
        self.send_to_tracker(request)
        logging.info(f"Updated tracker with downloaded chunks for '{filename}'.")

    def send_to_tracker(self, request):
        """Send a request to the tracker and return the response."""
        try:
            logging.info(f"Sending request to tracker: {request}")  # Log the request being sent
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((self.tracker_ip, self.tracker_port))
            conn.sendall(json.dumps(request).encode())  # Ensure all data is sent
            response = conn.recv(1024).decode()
            logging.info(f"Received response from tracker: {response}")  # Log the response received from tracker
            conn.close()
            return response
        except Exception as e:
            logging.error(f"Failed to communicate with tracker: {e}")
            return None

    def get_save_path_from_user(self, filename):
        """Open a file dialog to get the save path from the user."""
        save_path = None

        def ask_save_path():
            nonlocal save_path
            root = tk.Tk()
            root.withdraw()  # Hide the root window
            save_path = filedialog.asksaveasfilename(initialfile=filename, title="Save File As")
            root.destroy()

        # Ensure the file dialog runs on the main thread
        if threading.current_thread() is threading.main_thread():
            ask_save_path()
        else:
            tk.Tk().after(0, ask_save_path)

        if not save_path:
            logging.warning("No save path selected. Using default path.")
            save_path = os.path.join("downloads", filename)
        return save_path

    def start(self):
        """Start the peer server to handle incoming requests."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.ip, self.port))
        server.listen(5)
        logging.info(f"Peer running on {self.ip}:{self.port}")

        # Removed self.load_chunks() to avoid preloading chunks at startup

        while True:
            conn, addr = server.accept()
            logging.info(f"Connection from {addr}")
            threading.Thread(target=self.handle_peer_request, args=(conn,)).start()

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

    def load_chunks(self):
        """Load all shared chunks into memory when the peer starts."""
        for filename in self.shared_files:
            file_path = self.shared_files[filename]
            file_size = os.path.getsize(file_path)
            chunk_size = TORRENT_MAX_SIZE_KB * 1024  # Configurable chunk size
            total_chunks = (file_size + chunk_size - 1) // chunk_size

            self.chunks[filename] = {}
            for i in range(total_chunks):
                chunk_path = os.path.join("store", f"{filename}.torrent{i}")
                if os.path.exists(chunk_path):
                    try:
                        with open(chunk_path, "rb") as chunk_file:
                            self.chunks[filename][i] = chunk_file.read()
                        logging.info(f"Loaded chunk {i} of '{filename}' from '{chunk_path}'.")
                    except Exception as e:
                        logging.error(f"Failed to read chunk {i} of '{filename}' from '{chunk_path}': {e}")
                else:
                    logging.warning(f"Chunk {i} of '{filename}' is missing in 'store' folder.")

    def upload_chunk(self, conn, request):
        """Upload a requested chunk to a peer."""
        filename = request["filename"]
        chunk_index = request["chunk_index"]

        # Directly load the chunk from the 'store' folder
        chunk_path = os.path.join("store", f"{filename}.torrent{chunk_index}")
        if os.path.exists(chunk_path):
            try:
                with open(chunk_path, "rb") as chunk_file:
                    chunk_data = chunk_file.read()
                conn.send(chunk_data)
                logging.info(f"Uploaded chunk {chunk_index} of '{filename}' from '{chunk_path}', size: {len(chunk_data)} bytes.")
            except Exception as e:
                logging.error(f"Failed to read or send chunk {chunk_index} of '{filename}' from '{chunk_path}': {e}")
                conn.send(b"")
        else:
            logging.error(f"Chunk {chunk_index} of '{filename}' not found in 'store' folder.")
            conn.send(b"")

# Ensure tracker IP and port are passed correctly from command-line arguments
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Peer Node")
    parser.add_argument("--ip", required=True, help="Peer IP address")
    parser.add_argument("--port", type=int, required=True, help="Peer port")
    parser.add_argument("--tracker-ip", required=True, help="Tracker IP address")
    parser.add_argument("--tracker-port", type=int, required=True, help="Tracker port")
    args = parser.parse_args()

    peer = Peer(ip=args.ip, port=args.port, tracker_ip=args.tracker_ip, tracker_port=args.tracker_port)
    threading.Thread(target=peer.start).start()