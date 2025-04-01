from flask import Flask, request, jsonify
from Action import *
from colorama import Fore, Style
from collections import defaultdict
from ConfigClass import DefaultConfig
import time
import threading
import asyncio
import websockets
import json
import os
import socket

app = Flask(__name__)

class PeerTracker:
    def __init__(self, port=1108):
        self.config = DefaultConfig()
        self.port = port
        self.peers = {}
        self.hash_table = defaultdict(list)
        self.torrent_directory = self.config.meta_file_path()
        self.meta = {}
        self.hash_dict = {}
        self.meta_path = self.config.meta_path()
        self.hash_file_path = self.config.hash_file_path()

    def log_message(self, message):
        print(f"{Fore.GREEN}[MESSAGE-TRACKER]{Style.RESET_ALL} {message}")

    def log_error(self, message):
        print(f'{Fore.RED}[ERROR-TRACKER]{Style.RESET_ALL} {message}')

    def remove_inactive_peers(self):
        """Remove peers that have not sent a heartbeat within the timeout period."""
        timeout = 60
        current_time = time.time()
        inactive_peers = [peer for peer, info in self.peers.items() if current_time - info['last_heartbeat'] > timeout]
        for peer in inactive_peers:
            del self.peers[peer]
            self.log_message(f"Removed inactive peer: {peer}")

    async def broadcast_peer_updates(self, message):
        """Broadcast updates to all connected peers via WebSocket."""
        if hasattr(self, 'websocket_peers'):
            for websocket in list(self.websocket_peers):
                try:
                    await websocket.send(json.dumps(message))
                except websockets.ConnectionClosed:
                    self.websocket_peers.remove(websocket)

tracker = PeerTracker()

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.json
    peer_ip = request.remote_addr
    peer_port = data.get("port")
    peer_key = (peer_ip, peer_port)
    if peer_key in tracker.peers:
        tracker.peers[peer_key]['last_heartbeat'] = time.time()
        tracker.log_message(f"Heartbeat received from {peer_key}")
        return jsonify({"message": "Heartbeat received"}), 200
    else:
        tracker.log_error(f"Received heartbeat from unregistered peer: {peer_key}")
        return jsonify({"error": "Peer not registered"}), 400

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    peer_ip = request.remote_addr
    peer_port = data.get("port")
    peer_key = (peer_ip, peer_port)
    tracker.peers[peer_key] = {
        'status': 'idle',
        'port': peer_port,
        'files': data.get('files', []),
        'last_heartbeat': time.time()
    }
    tracker.log_message(f"PEER {peer_key} registered with files: {data.get('files', [])}")
    return jsonify({"message": "Peer registered successfully"}), 200

@app.route("/get_n_idle_peers", methods=["POST"])
def get_n_idle_peers():
    data = request.json
    requested_count = data.get("count")
    peer_ip = request.remote_addr
    peer_port = data.get("peer_port")
    idle_peers = [ip for ip, info in tracker.peers.items() if info['status'] == 'idle' and (peer_ip, peer_port) != ip]
    if len(idle_peers) >= requested_count:
        return jsonify({"type": "PEERS_AVAILABLE", "peers": idle_peers[:requested_count]}), 200
    else:
        return jsonify({"type": "NOT_ENOUGH_IDLE_PEERS"}), 200

@app.route("/get_n_file_idle_peers", methods=["POST"])
def get_n_file_idle_peers():
    data = request.json
    file_names = data.get("file_names")
    peer_ip = request.remote_addr
    peer_port = data.get("peer_port")
    tracker.log_message(f"Received request for N idle peers with file: {file_names}")
    
    file_peers = []
    for file_name in file_names:
        for peer, info in tracker.peers.items():
            if file_name in info['files'] and info['status'] == 'idle' and peer != (peer_ip, peer_port):
                file_peers.append({"file_name": file_name, "peer": peer})
    
    if file_peers:
        return jsonify({"type": "PEERS_AVAILABLE", "file_peer": file_peers}), 200
    else:
        return jsonify({"type": "NOT_ENOUGH_IDLE_PEERS"}), 200

@app.route("/complete_transfer", methods=["POST"])
def complete_transfer():
    data = request.json
    peer_ip = data.get("peer_ip")
    peer_key = (peer_ip, data.get("peer_port"))
    if peer_key in tracker.peers:
        tracker.peers[peer_key]['status'] = 'idle'
        tracker.log_message(f"Peer {peer_key} is now idle.")
        return jsonify({"message": "Transfer completed"}), 200
    else:
        return jsonify({"error": "Peer not found"}), 404

websocket_peers = set()

async def websocket_handler(websocket, path):
    websocket_peers.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "ERROR":
                await websocket.send(json.dumps({"type": "ERROR", "message": data.get("message")}))
    except websockets.ConnectionClosed:
        pass
    finally:
        websocket_peers.remove(websocket)

def start_inactive_peer_removal():
    while True:
        tracker.remove_inactive_peers()
        time.sleep(30)  # Check every 30 seconds

# Ensure folders exist
if not os.path.exists("downloaded"):
    os.makedirs("downloaded")
if not os.path.exists("uploaded"):
    os.makedirs("uploaded")

class PeerFileReceiver:
    def __init__(self, host="0.0.0.0", port=6000, store_folder="store"):
        self.host = host
        self.port = port
        self.store_folder = store_folder
        if not os.path.exists(store_folder):
            os.makedirs(store_folder)

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"File receiver listening on {self.host}:{self.port} and saving files to {self.store_folder}")
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connection accepted from {addr}")
            threading.Thread(target=self._handle_client, args=(client_socket, addr)).start()

    def _handle_client(self, client_socket, addr):
        try:
            # Receive the file name (terminated by a newline)
            file_name = ""
            while True:
                char = client_socket.recv(1).decode("utf-8")
                if char == "\n":  # End of file name
                    break
                file_name += char

            print(f"Receiving file: {file_name} from {addr}")
            file_path = os.path.join(self.store_folder, file_name)

            # Receive the file content and save it
            with open(file_path, "wb") as f:
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    f.write(data)
            print(f"File {file_name} saved to {self.store_folder}")
        except Exception as e:
            print(f"Error receiving file from {addr}: {e}")
        finally:
            client_socket.close()

# Start WebSocket server
def start_websocket_server():
    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)
    try:
        server = websockets.serve(websocket_handler, "0.0.0.0", 8765)
        loop.run_until_complete(server)  # Start the WebSocket server
        loop.run_forever()
    except Exception as e:
        print(f"Error in WebSocket server: {e}")
    finally:
        loop.close()

if __name__ == "__main__":
    threading.Thread(target=start_inactive_peer_removal, daemon=True).start()
    threading.Thread(target=start_websocket_server, daemon=True).start()
    threading.Thread(target=PeerFileReceiver().start, daemon=True).start()  # Start file receiver
    app.run(host="0.0.0.0", port=1108, debug=True)
