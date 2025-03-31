import asyncio
import json
import os
from colorama import Fore, Style
from util import check_file_size
from ConfigClass import DefaultConfig
from threading import Thread

class PeerClient:
    def __init__(self, tracker_ip, tracker_port, peer_port, files, peer_ip='127.0.0.1', peer_name="PEER"):
        self.config = DefaultConfig()
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.peer_port = peer_port
        self.tracker_reader = None
        self.tracker_writer = None
        self.files = files  # Store files that this peer has
        self.peer_ip = peer_ip
        self.file_path = self.config.client_directory()
        self.piece_size = self.config.piece_size()
        self.peer_name = peer_name
        self.lock = asyncio.Lock()
        self.read_lock = asyncio.Lock()
        self.server_thread = None
        self.peers = {}  # Initialize peers as an empty dictionary
        if not os.path.exists("downloaded"):
            os.makedirs("downloaded")

    def log(self, prompt):
        print(f'{Fore.BLUE}[{self.peer_name}]{Style.RESET_ALL} {prompt}')

    def log_message(self, message):
        print(f'{Fore.BLUE}[{self.peer_name} - MESSAGE]{Style.RESET_ALL} {message}')

    def log_error(self, error_message):
        print(f'{Fore.RED}[{self.peer_name} - ERROR]{Style.RESET_ALL} {error_message}')

    async def connect_to_tracker(self):
        """Connect to the tracker and register the peer."""
        self.tracker_reader, self.tracker_writer = await asyncio.open_connection(self.tracker_ip, self.tracker_port)
        file_sizes = [check_file_size(f"{self.file_path}/{file_path}") for file_path in self.files]
        register_message = {"type": "REGISTER", "port": self.peer_port, "files": self.files, "peer_ip": self.peer_ip, 'file_sizes': file_sizes}
        await self.send_to_tracker(register_message)
        self.log(f"Registered with tracker at {self.tracker_ip}:{self.tracker_port}")
        self.server_thread = Thread(target=asyncio.run, args=(self.start_server(),))
        self.server_thread.start()
        self.log(f"Finishing setup server")

        # Start sending heartbeat
        asyncio.create_task(self.send_heartbeat())

        # Request files after registration
        asyncio.create_task(self.request_files_from_peers())

        # New tasks for handling tracker updates and detecting disconnects
        asyncio.create_task(self.handle_tracker_updates())
        asyncio.create_task(self.detect_peer_disconnects())

    async def request_files_from_peers(self):
        """Request files from other peers."""
        await asyncio.sleep(3)  # Wait for tracker to stabilize
        self.log("Requesting files from peers...")
        file_names = ["fileA1.txt", "fileA2.txt"]  # Example files to request
        response = await self.get_n_file_idle_peers(file_names)
        if response:
            file_peers = response.get('file_peer', [])
            file_sizes = response.get('file_sizes', {})
            for file_name, peer in file_peers:
                peer_ip, peer_port = peer
                await self.request_file(peer_ip, file_name, file_sizes[file_name]['file_size'])

    async def start_server(self):
        # Start listening for incoming peer connections
        server = await asyncio.start_server(self.listen_for_peers, '0.0.0.0', self.peer_port)
        self.log(f"{self.peer_name} listening on port {self.peer_port}")
        async with server:
            await server.serve_forever()

    async def send_to_tracker(self, message):
        """Send a JSON message to the tracker."""
        async with self.lock:
            str_message = json.dumps(message)
            self.log_message(f"Sending message to tracker: {str_message}")
            self.tracker_writer.write(f'{str_message}\n'.encode('utf-8'))
        await self.tracker_writer.drain()
        self.log(f"Sending done")

    async def read_from_tracker(self):
        """Read a JSON message from the tracker."""
        async with self.lock:
            self.log('Waiting...')
            response = await self.tracker_reader.readline()
            if not response.strip():  # Handle empty responses
                self.log_error("Received empty response from tracker.")
                return None
            self.log_message(f"Received message from tracker: {response.decode('utf-8')}")
            response_data = json.loads(response.decode('utf-8'))

            if response_data.get('type') == 'ERROR':
                self.log_error(f"Error from tracker: {response_data['message']}")
                return None

            return response_data

    async def get_n_idle_peers(self, n):
        """Request N idle peers from the tracker."""
        request_message = {"type": "GET_N_IDLE_PEERS", "count": n, 'peer_ip': self.peer_ip, 'peer_port': self.peer_port}
        await self.send_to_tracker(request_message)

        # Wait for tracker response
        
        response_data = await self.read_from_tracker()

        if response_data and response_data['type'] == 'PEERS_AVAILABLE':
            return response_data['peers']
        else:
            return []
        
    async def get_n_file_idle_peers(self, file_names):
        """Request N idle peers from the tracker."""
        request_message = {"type": "GET_N_FILE_IDLE_PEERS", "file_names": file_names, 'peer_ip': self.peer_ip, 'peer_port': self.peer_port}
        await self.send_to_tracker(request_message)
        self.log(f"Send to tracker: {request_message}")
        response_data = await self.read_from_tracker()

        if response_data and response_data['type'] == 'PEERS_AVAILABLE':
            return response_data | {'file_sizes': response_data['file_sizes']}
        else:
            return {}

    async def request_file(self, peer_ip, file_name, file_size):
        """Request a specific file from another peer."""
        request_message = {"type": "REQUEST_FILE", "peer_ip": peer_ip, "file_name": file_name}
        await self.send_to_tracker(request_message)
        # Wait for tracker response
        response_data = await self.read_from_tracker()

        if response_data and response_data['type'] == "PEER_CONTACT":
            peer_ip = response_data['peer_ip']
            peer_port = response_data['peer_port']
            self.log(f"Contacting peer {peer_ip}:{peer_port} for file transfer.")
            await self.connect_to_peer(peer_ip, peer_port, file_name, file_size)
        elif response_data and response_data['type'] == "PEER_BUSY":
            self.log(f"Requested peer {peer_ip} is busy or does not have the requested file.")

    async def connect_to_peer(self, peer_ip, peer_port, file_name, file_size):
        """Connect to another peer to request a specific file."""
        reader, writer = await asyncio.open_connection(peer_ip, peer_port)
        writer.write(f"REQUEST_FILE:{file_name}".encode('utf-8'))
        await writer.drain()
        
        file_data = b''
        for _ in range(file_size // self.piece_size + 1):
            file_data += await reader.read(self.config.buffer_size())
        self.log(f"Received {file_name} from {peer_ip}:{peer_port}: |{file_data.decode('utf-8')}|")
        if not os.path.exists("downloaded"):
            os.makedirs("downloaded")
        with open(f"downloaded/{file_name}", 'wb') as file:
            file.write(file_data)
        await self.notify_transfer_complete(peer_ip)
        writer.close()
        await writer.wait_closed()

    async def notify_transfer_complete(self, peer_ip):
        """Notify the tracker that the file transfer is complete."""
        complete_message = {"type": "COMPLETE", "peer_ip": peer_ip}
        await self.send_to_tracker(complete_message)

    async def listen_for_peers(self, reader, writer):
        """Listen for incoming peer connections to handle file requests."""
        request = await reader.read(self.config.buffer_size())
        if request.decode('utf-8').startswith("REQUEST_FILE:"):
            file_name = request.decode('utf-8').split(":")[1]
            file_path = f"{self.file_path}/{file_name}"  # Serve files from the data folder
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    while chunk := file.read(self.config.buffer_size()):
                        writer.write(chunk)
                        await writer.drain()
                self.log(f"Served file {file_name} to peer.")
            else:
                self.log(f"File {file_name} not found in {self.file_path}.")
        writer.close()
        await writer.wait_closed()

    async def send_heartbeat(self):
        """Send heartbeat to tracker periodically."""
        while True:
            try:
                heartbeat_message = {"type": "HEARTBEAT", "port": self.peer_port}
                await self.send_to_tracker(heartbeat_message)
                self.log_message("Heartbeat sent to tracker.")
            except Exception as e:
                self.log_error(f"Failed to send heartbeat: {e}")
            await asyncio.sleep(10)  # Send heartbeat every 10 seconds

    async def handle_tracker_updates(self):
        """Continuously listen for updates from the tracker."""
        while True:
            response_data = await self.read_from_tracker()
            if response_data:
                if response_data['type'] == 'PEER_UPDATE':
                    self.log(f"Updated peer list: {response_data['peers']}")
                elif response_data['type'] == 'ERROR':
                    self.log_error(f"Tracker error: {response_data['message']}")
            await asyncio.sleep(1)  # Poll tracker updates every second

    async def detect_peer_disconnects(self):
        """Detect and handle peer disconnects."""
        while True:
            # Simulate checking peer connectivity (placeholder logic)
            current_time = asyncio.get_event_loop().time()
            disconnected_peers = [
                peer for peer, info in self.peers.items()
                if current_time - info.get('last_heartbeat', 0) > 60  # 60 seconds timeout
            ]
            if disconnected_peers:
                self.log(f"Detected disconnected peers: {disconnected_peers}")
                # Notify tracker about disconnected peers
                disconnect_message = {"type": "PEER_DISCONNECT", "peers": disconnected_peers}
                await self.send_to_tracker(disconnect_message)
            await asyncio.sleep(5)  # Check every 5 seconds

    async def disconnect_from_tracker(self):
        """Notify tracker before disconnecting."""
        try:
            disconnect_message = {"type": "DISCONNECT"}
            await self.send_to_tracker(disconnect_message)
        except Exception as e:
            self.log_error(f"Failed to notify tracker before disconnecting: {e}")
        finally:
            if self.tracker_writer:
                self.tracker_writer.close()
                await self.tracker_writer.wait_closed()

    async def run_tests(self):
        """Run tests for tracker and peer functionalities."""
        self.log("Starting test for tracker and peer functionalities...")
        await asyncio.gather(
            self.handle_tracker_updates(),
            self.detect_peer_disconnects()
        )
