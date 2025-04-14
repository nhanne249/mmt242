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
        chunk_size = TORRENT_MAX_SIZE_KB * 1024  # Use the maximum size from config
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

    def register_torrent(self, torrent_file):
        """Register a file with the tracker using a .torrent file."""
        metadata = self.parse_torrent(torrent_file)
        filename = metadata["filename"]
        pieces = metadata["pieces"]

        # Load file chunks into memory
        filepath = self.shared_files.get(filename)
        if not filepath or not os.path.exists(filepath):
            logging.error(f"File '{filename}' not found for registration.")
            return

        with open(filepath, "rb") as f:
            self.chunks[filename] = {}
            for i, piece_hash in enumerate(pieces):
                chunk_data = f.read(len(piece_hash))
                self.chunks[filename][i] = chunk_data

        request = {
            "action": "register_torrent",
            "filename": filename,
            "pieces": pieces
        }
        self.send_to_tracker(request)
        logging.info(f"Registered .torrent file '{filename}' with tracker.")

    def query_tracker(self, filename):
        """Query the tracker for available peers for a file."""
        request = {"action": "query", "filename": filename}
        response = self.send_to_tracker(request)
        return json.loads(response)

    def download_file(self, filename, peer_chunks):
        """Download a file by fetching chunks from multiple peers."""
        if filename in self.active_downloads:
            logging.warning(f"Download for '{filename}' is already in progress.")
            return

        def download_task():
            metadata = self.parse_torrent(f"{filename}.torrent")
            pieces = metadata["pieces"]
            total_chunks = len(pieces)
            self.downloaded_chunks[filename] = set()

            def download_chunk(chunk_index, peer_ip):
                try:
                    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    conn.connect((peer_ip, self.port))
                    request = {"action": "get_chunk", "filename": filename, "chunk_index": chunk_index}
                    conn.send(json.dumps(request).encode())
                    chunk_data = conn.recv(1024 * 1024)  # 1 MB

                    # Verify piece integrity
                    if hashlib.sha1(chunk_data).hexdigest() == pieces[chunk_index]:
                        with self.lock:
                            self.downloaded_chunks[filename].add(chunk_index)
                            self.chunks.setdefault(filename, {})[chunk_index] = chunk_data
                        logging.info(f"Downloaded and verified chunk {chunk_index} of '{filename}' from {peer_ip}.")
                    else:
                        logging.error(f"Chunk {chunk_index} failed integrity check from {peer_ip}.")
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

            # Retry failed chunks
            for chunk_index in range(total_chunks):
                if chunk_index not in self.downloaded_chunks[filename]:
                    logging.warning(f"Retrying download for chunk {chunk_index} of '{filename}'.")
                    for peer_ip in peer_chunks.get(chunk_index, []):
                        download_chunk(chunk_index, peer_ip)

            # Reassemble the file
            save_path = self.get_save_path_from_user(filename)  # Get save path from GUI
            with open(save_path, "wb") as f:
                for i in range(total_chunks):
                    if i in self.chunks[filename]:
                        f.write(self.chunks[filename][i])
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

    def download_torrent(self, torrent_file):
        """Download a file using a .torrent file."""
        metadata = self.parse_torrent(torrent_file)
        filename = metadata["filename"]
        pieces = metadata["pieces"]

        # Query tracker for peers
        request = {"action": "query_torrent", "filename": filename}
        response = self.send_to_tracker(request)
        peer_chunks = json.loads(response)

        self.downloaded_chunks[filename] = set()

        def download_piece(piece_index, peer_ip):
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.connect((peer_ip, self.port))
                request = {"action": "get_chunk", "filename": filename, "chunk_index": piece_index}
                conn.send(json.dumps(request).encode())
                chunk_data = conn.recv(1024 * 1024)  # 1 MB

                # Verify piece integrity
                if hashlib.sha1(chunk_data).hexdigest() == pieces[piece_index]:
                    with self.lock:
                        self.downloaded_chunks[filename].add(piece_index)
                        self.chunks[filename][piece_index] = chunk_data
                    logging.info(f"Downloaded and verified piece {piece_index} of '{filename}' from {peer_ip}.")
                else:
                    logging.error(f"Piece {piece_index} failed integrity check from {peer_ip}.")
                conn.close()
            except Exception as e:
                logging.error(f"Failed to download piece {piece_index} from {peer_ip}: {e}")

        threads = []
        for piece_index, peers in peer_chunks.items():
            for peer_ip in peers:
                thread = threading.Thread(target=download_piece, args=(piece_index, peer_ip))
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        # Reassemble the file
        with open(f"downloaded_{filename}", "wb") as f:
            for i in range(len(pieces)):
                f.write(self.chunks[filename][i])
        logging.info(f"File '{filename}' downloaded and reassembled.")

        # Notify tracker of downloaded pieces
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
            elif action == "get_torrent":
                filename = request["filename"]
                torrent_file = f"{filename}.torrent"
                if os.path.exists(torrent_file):
                    with open(torrent_file, "r") as f:
                        conn.send(f.read().encode())
                    logging.info(f"Sent .torrent file for '{filename}' to peer.")
                else:
                    logging.error(f"Requested .torrent file '{filename}' not found.")
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

    def parse_torrent(self, torrent_file):
        """Parse a .torrent file to extract metadata."""
        try:
            with open(torrent_file, "r") as f:
                metadata = json.load(f)
            logging.info(f"Parsed .torrent file: {torrent_file}")
            return metadata
        except Exception as e:
            logging.error(f"Failed to parse .torrent file '{torrent_file}': {e}")
            raise

    def share_file(self, filepath):
        """Share a file by creating and registering its .torrent file."""
        filename = os.path.basename(filepath)
        self.shared_files[filename] = filepath

        # Create .torrent file
        metadata = {
            "filename": filename,
            "file_size": os.path.getsize(filepath),
            "piece_size": 1024 * 1024,  # 1 MB
            "pieces": []
        }

        with open(filepath, "rb") as f:
            while chunk := f.read(metadata["piece_size"]):
                metadata["pieces"].append(hashlib.sha1(chunk).hexdigest())

        torrent_file = f"{filename}.torrent"
        with open(torrent_file, "w") as f:
            json.dump(metadata, f)

        # Register .torrent file with tracker
        request = {
            "action": "register_torrent",
            "filename": filename,
            "pieces": metadata["pieces"]
        }
        self.send_to_tracker(request)
        logging.info(f"Shared file '{filename}' and registered .torrent with tracker.")

    def fetch_torrent(self, filename, peer_ip):
        """Fetch the .torrent file for a given filename from a peer."""
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((peer_ip, self.port))
            request = {"action": "get_torrent", "filename": filename}
            conn.send(json.dumps(request).encode())
            torrent_data = conn.recv(1024 * 1024).decode()
            torrent_file = os.path.join("store", f"{filename}.torrent")
            os.makedirs("store", exist_ok=True)  # Ensure the 'store' directory exists
            with open(torrent_file, "w") as f:
                f.write(torrent_data)
            logging.info(f"Fetched .torrent file for '{filename}' from {peer_ip}.")
            return torrent_file
        except Exception as e:
            logging.error(f"Failed to fetch .torrent file for '{filename}' from {peer_ip}: {e}")
            return None

    def get_save_path_from_user(self, filename):
        """Open a file dialog to get the save path from the user."""
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        save_path = filedialog.asksaveasfilename(initialfile=filename, title="Save File As")
        if not save_path:
            logging.warning("No save path selected. Using default path.")
            save_path = os.path.join("downloads", filename)
        return save_path

    def start(self):
        """Start the peer server to handle incoming requests."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        logging.info(f"Peer running on {self.ip}:{self.port}")

        while True:
            conn, addr = server.accept()
            logging.info(f"Connection from {addr}")
            threading.Thread(target=self.handle_peer_request, args=(conn)).start()

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
