import asyncio
import json
import os
import http.client
from colorama import Fore, Style
from util import check_file_size
from ConfigClass import DefaultConfig
from threading import Thread

class PeerClient:
    def __init__(self, tracker_ip, tracker_port, peer_port, files, peer_ip='127.0.0.1', peer_name="PEER", request_files=None):
        self.config = DefaultConfig()
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.peer_port = peer_port
        self.tracker_reader = None
        self.tracker_writer = None
        self.files = files
        self.peer_ip = peer_ip
        self.file_path = self.config.client_directory()
        self.piece_size = self.config.piece_size()
        self.peer_name = peer_name
        self.lock = asyncio.Lock()
        self.read_lock = asyncio.Lock()
        self.server_thread = None
        self.peers = {}
        self.request_files = request_files if request_files else []  # Thêm thuộc tính request_files
        self.registered = False  # Cờ kiểm tra trạng thái đăng ký
        self.heartbeat_task = None  # Quản lý heartbeat task
        self.server_task = None  # Quản lý server task
        self.main_task = None  # Quản lý task chính
        if not os.path.exists("downloaded"):
            os.makedirs("downloaded")

    def log(self, prompt):
        print(f'{Fore.BLUE}[{self.peer_name}]{Style.RESET_ALL} {prompt}')

    def log_message(self, message):
        print(f'{Fore.BLUE}[{self.peer_name} - MESSAGE]{Style.RESET_ALL} {message}')

    def log_error(self, error_message):
        print(f'{Fore.RED}[{self.peer_name} - ERROR]{Style.RESET_ALL} {error_message}')

    async def register_with_tracker(self):
        """Register the peer with the tracker."""
        if self.registered:  # Kiểm tra nếu đã đăng ký thì không gửi lại yêu cầu
            self.log(f"Already registered with tracker at {self.tracker_ip}:{self.tracker_port}")
            return

        file_sizes = [check_file_size(f"{self.file_path}/{file_path}") for file_path in self.files]
        register_message = {
            "type": "REGISTER",
            "port": self.peer_port,
            "files": self.files,
            "peer_ip": self.peer_ip,
            "file_sizes": file_sizes
        }
        await self.send_to_tracker("/register", register_message)  # Gửi đến API /register
        self.registered = True  # Đánh dấu đã đăng ký
        self.log(f"Registered with tracker at {self.tracker_ip}:{self.tracker_port}")

    async def connect_to_tracker(self):
        """Connect to the tracker and manage peer tasks."""
        try:
            # Establish a connection to the tracker
            self.tracker_reader, self.tracker_writer = await asyncio.open_connection(self.tracker_ip, self.tracker_port)

            # If no request_files, perform registration
            if not self.request_files:
                await self.register_with_tracker()

            # Start main tasks
            tasks = [
                self.send_heartbeat(),
                self.start_server(),
                self.main_loop()
            ]
            # If there are request_files, call request_files_from_peers
            if self.request_files:
                await self.request_files_from_peers()
            await asyncio.gather(*tasks)
        except Exception as e:
            self.log_error(f"Error in main tasks: {e}")
        finally:
            # Close tracker connection on exit
            if self.tracker_writer:
                self.tracker_writer.close()
                await self.tracker_writer.wait_closed()

    async def main_loop(self):
        """Main loop to keep the client running."""
        try:
            while True:
                await asyncio.sleep(1)  # Giữ client hoạt động
        except asyncio.CancelledError:
            self.log("Main loop cancelled. Exiting...")

    async def request_files_from_peers(self):
        """Request files from other peers."""
        await asyncio.sleep(3) 
        self.log("Requesting files from peers...")
        file_names = self.request_files
        response = await self.get_n_file_idle_peers(file_names)
        if response:
            file_peers = response.get('file_peer', [])
            file_sizes = response.get('file_sizes', {})
            self.log(f"Tracker response for requested files: {response}")  # Log the response
            if not file_peers:
                self.log("No peers available for the requested files. Stopping requests.")
                return  # Stop further requests to avoid infinite loop
            for file_name, peer in file_peers:
                peer_ip, peer_port = peer['ip'], peer['port']
                self.log(f"Requesting file {file_name} from peer {peer_ip}:{peer_port}...")
                try:
                    await self.connect_to_peer(peer_ip, peer_port, file_name, file_sizes[file_name])
                except Exception as e:
                    self.log_error(f"Failed to connect to peer {peer_ip}:{peer_port} for file {file_name}: {e}")
        else:
            self.log_error("Failed to get peers from tracker.")

    async def start_server(self):
        """Start the server to listen for incoming peer connections."""
        try:
            server = await asyncio.start_server(self.listen_for_peers, '0.0.0.0', self.peer_port)
            self.log(f"{self.peer_name} listening on port {self.peer_port}")
            async with server:
                await server.serve_forever()
        except Exception as e:
            self.log_error(f"Failed to start server: {e}")

    async def send_to_tracker(self, endpoint, message):
        """Send a JSON message to the tracker."""
        try:
            str_message = json.dumps(message)
            self.log_message(f"Sending message to tracker ({endpoint}): {str_message}")

            # Sử dụng HTTP client để gửi yêu cầu thay vì kết nối socket
            conn = http.client.HTTPConnection(self.tracker_ip, self.tracker_port)
            headers = {'Content-Type': 'application/json'}
            conn.request("POST", endpoint, body=str_message, headers=headers)

            # Đọc phản hồi từ tracker
            response = conn.getresponse()
            response_data = response.read().decode('utf-8')

            # Kiểm tra nếu phản hồi là JSON hợp lệ
            try:
                json_response = json.loads(response_data)
                self.log_message(f"Response from tracker ({endpoint}): {json_response}")
                return json_response
            except json.JSONDecodeError:
                self.log_error(f"Unexpected response from tracker: {response_data}")
                return None
        except Exception as e:
            self.log_error(f"Failed to send message to tracker ({endpoint}): {e}")
            return None

    async def read_from_tracker(self):
        """Read a JSON message from the tracker."""
        async with self.lock:
            self.log('Waiting...')
            response = await self.tracker_reader.readline()
            response_data = response.decode('utf-8').strip()

            # Check if the response is valid JSON
            try:
                json_response = json.loads(response_data)
                self.log_message(f"Received message from tracker: {json_response}")
                return json_response
            except json.JSONDecodeError:
                self.log_error(f"Unexpected response from tracker: {response_data}")
                return None
        
    async def get_n_file_idle_peers(self, file_names):
        """Request N idle peers from the tracker."""
        request_message = {"type": "GET_N_FILE_IDLE_PEERS", "file_names": file_names, 'peer_ip': self.peer_ip, 'peer_port': self.peer_port}
        response_data = await self.send_to_tracker("/get_n_file_idle_peers", request_message)
        self.log(f"Send to tracker: {request_message}")
        # response_data = await self.read_from_tracker()
        if response_data and response_data['type'] == 'PEERS_AVAILABLE':
            self.log(f"Received peers for files: {response_data['file_peer']}")
            return response_data
        else:
            self.log_error("No peers available for the requested files.")
            return {}

    async def request_file(self, peer_ip, file_name, file_size):
        """Request a specific file from another peer."""
        self.log(f"Requesting file {file_name} from peer {peer_ip}...")
        request_message = {"type": "REQUEST_FILE", "peer_ip": peer_ip, "file_name": file_name}
        await self.send_to_tracker("/request_file", request_message)
        response_data = await self.read_from_tracker()

        if response_data and response_data['type'] == "PEER_CONTACT":
            peer_ip = response_data['peer_ip']
            peer_port = response_data['peer_port']
            self.log(f"Contacting peer {peer_ip}:{peer_port} for file transfer.")
            await self.connect_to_peer(peer_ip, peer_port, file_name, file_size)
        elif response_data and response_data['type'] == "PEER_BUSY":
            self.log(f"Requested peer {peer_ip} is busy or does not have the requested file.")
        else:
            self.log_error(f"Unexpected response from tracker: {response_data}")

    async def connect_to_peer(self, peer_ip, peer_port, file_name, file_size):
        """Connect to another peer to request a specific file."""
        try:
            self.log(f"Connecting to peer {peer_ip}:{peer_port} for file {file_name}...")
            reader, writer = await asyncio.open_connection(peer_ip, peer_port)
            writer.write(f"REQUEST_FILE:{file_name}".encode('utf-8'))
            await writer.drain()
            
            file_data = b''
            remaining_size = file_size
            while remaining_size > 0:
                chunk = await reader.read(min(self.config.buffer_size(), remaining_size))
                if not chunk:
                    break
                file_data += chunk
                remaining_size -= len(chunk)

            if file_data:
                self.log(f"Successfully received {file_name} from {peer_ip}:{peer_port}. Saving to 'downloaded' folder.")
                if not os.path.exists("downloaded"):
                    os.makedirs("downloaded")
                with open(f"downloaded/{file_name}", 'wb') as file:
                    file.write(file_data)
                self.log("File saved successfully. Exiting program.")  # Log thông báo thoát
                os._exit(0)  # Thoát chương trình ngay lập tức
            else:
                self.log_error(f"Failed to receive {file_name} from {peer_ip}:{peer_port}. File data is empty.")

        except Exception as e:
            self.log_error(f"Error connecting to peer {peer_ip}:{peer_port} for file {file_name}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def listen_for_peers(self, reader, writer):
        """Listen for incoming peer connections to handle file requests."""
        try:
            request = await reader.read(self.config.buffer_size())
            if request.decode('utf-8').startswith("REQUEST_FILE:"):
                file_name = request.decode('utf-8').split(":")[1]
                file_path = f"{self.file_path}/{file_name}"
                self.log(f"Peer requested file {file_name}. Checking availability...")
                if os.path.exists(file_path):
                    self.log(f"Serving file {file_name} to peer.")
                    with open(file_path, 'rb') as file:
                        while chunk := file.read(self.config.buffer_size()):
                            writer.write(chunk)
                            await writer.drain()
                else:
                    self.log_error(f"File {file_name} not found in {self.file_path}.")
            else:
                self.log_error("Invalid request received from peer.")
        except Exception as e:
            self.log_error(f"Error handling peer request: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def send_heartbeat(self):
        """Send heartbeat to tracker periodically."""
        while True:
            try:
                heartbeat_message = {"type": "HEARTBEAT", "port": self.peer_port}
                await self.send_to_tracker("/heartbeat", heartbeat_message)
                self.log_message("Heartbeat sent to tracker.")
            except Exception as e:
                self.log_error(f"Failed to send heartbeat: {e}")
            await asyncio.sleep(10)

    async def handle_tracker_updates(self):
        """Continuously listen for updates from the tracker."""
        while True:
            response_data = await self.read_from_tracker()
            if response_data:
                if response_data['type'] == 'PEER_UPDATE':
                    self.log(f"Updated peer list: {response_data['peers']}")
                elif response_data['type'] == 'ERROR':
                    self.log_error(f"Tracker error: {response_data['message']}")
            await asyncio.sleep(1)

    async def detect_peer_disconnects(self):
        """Detect and handle peer disconnects."""
        while True:
            current_time = asyncio.get_event_loop().time()
            disconnected_peers = [
                peer for peer, info in self.peers.items()
                if current_time - info.get('last_heartbeat', 0) > 60
            ]
            if disconnected_peers:
                self.log(f"Detected disconnected peers: {disconnected_peers}")
                disconnect_message = {"type": "PEER_DISCONNECT", "peers": disconnected_peers}
                await self.send_to_tracker("/peer_disconnect", disconnect_message)
            await asyncio.sleep(5)

    async def disconnect_from_tracker(self):
        """Notify tracker before disconnecting."""
        try:
            disconnect_message = {"type": "DISCONNECT"}
            await self.send_to_tracker("/disconnect", disconnect_message)
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
