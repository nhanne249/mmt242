import json
from colorama import Fore, Style
from util import max_bipartite_matching_scipy
from util import itemgetter
from threading import Thread 
import asyncio

class Action:
    """Base class for all actions that can be performed by peers."""
    def __init__(self, tracker, message, writer, ip, port):
        self.tracker = tracker
        self.message = message
        self.writer = writer
        self.ip = ip 
        self.port = port

    async def execute(self):
        """Execute the action. This should be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method.")
    
    def log(self, message):
        self.tracker.log(message)

class Register(Action):
    """Handles registration of a peer."""
    async def execute(self):
        peer_ip, _ = self.writer.get_extra_info('peername')
        peer_port = self.message.get('port')
        sock = self.writer.get_extra_info('socket')
        # peer_ip, peer_port = sock.getsockname()
        files = self.message.get('files', [])
        fsizes = self.message.get('file_sizes', 0)
        self.update_meta(files, fsizes)
        self.tracker.peers[peer_ip, peer_port] = {
            'status': 'idle',
            'port': peer_port,
            'files': files,
            'file_requests': [],
        }
        self.tracker.hash_table[peer_ip, peer_port] = files
        print(f"{Fore.GREEN}[TRACKER]{Style.RESET_ALL} PEER {peer_ip}:{peer_port} registered with files: {files}.")

    def update_meta(self, file_names, file_sizes):
        appendant = {k: {'file_size': v} for k, v in zip(file_names, file_sizes)}
        self.tracker.meta.update(appendant)
        with open(self.tracker.torrent_directory, 'w') as f:
            json.dump(self.tracker.meta, f)

        with open(self.tracker.hash_file_path, 'w') as f:
            hash_dict = {k: f"{k}.torrent.json" for k in self.tracker.meta.keys()}   
            json.dump(hash_dict, f)

        for k, v in self.tracker.meta.items():
            with open(self.tracker.meta_path + f"{k}.torrent.json", 'w') as f:
                json.dump(v, f)

class GetNIdlePeers(Action):
    """Handles the request for N idle peers."""
    async def execute(self):
        peer_ip = self.message.get('peer_ip')
        peer_port = self.message.get('peer_port')
        requested_count = self.message['count']
        idle_peers = [ip for ip, info in self.tracker.peers.items() if info['status'] == 'idle' and (peer_ip, peer_port) != ip]
        if len(idle_peers) >= requested_count:
            response = {
                'type': 'PEERS_AVAILABLE',
                'peers': idle_peers[:requested_count]
            }
        else:
            response = {'type': 'NOT_ENOUGH_IDLE_PEERS'}
        
        self.writer.write(f"{json.dumps(response)}\n".encode('utf-8'))
        await self.writer.drain()

class GetNFileIdlePeers(Action):
    """Handles the request for N idle peers with a specific file."""
    async def execute(self):
        self.log(f"Received request for N idle peers with file: {self.message['file_names']}")
        file_names = self.message['file_names']
        ip_file = []
        while len(ip_file) < len(file_names):
            T = set(file_names)
            ip, C = list(zip(*list(self.tracker.hash_table.items())))
            C = list(C)
            result = [None]
            
            def callback(func):
                def inner_callback(*args, **kwargs):
                    result[0] = func(*args, **kwargs)
                return inner_callback

            thread = Thread(target=callback(max_bipartite_matching_scipy), args=(T, C))
            # index_file = max_bipartite_matching_scipy(T, C)
            thread.start()
            thread.join()
            index_file = result[0]
            ip_file = [(file, ip[index]) for index, file in index_file.items()]
            
            if len(ip_file) >= len(file_names):
                file_sizes = dict(zip(file_names, itemgetter(*file_names)(self.tracker.meta)))
                response = {
                    'type': 'PEERS_AVAILABLE',
                    'file_peer': ip_file,
                    'file_sizes': file_sizes
                }
            else:
                self.tracker.log(f"Not enough idle peers with the requested file.")
                response = {'type': 'NOT_ENOUGH_IDLE_PEERS'}
                await asyncio.sleep(1)
            
        self.log(f'Response: {response}')
        self.writer.write(f"{json.dumps(response)}\n".encode('utf-8'))
        await self.writer.drain()

class RequestFile(Action):
    """Handles file requests from peers."""
    async def execute(self):
        self.log(f"Received request for file: {self.message['file_name']}")
        requested_peer_ip = tuple(self.message['peer_ip'])
        file_name = self.message['file_name']
        if requested_peer_ip in self.tracker.peers:
            peer_info = self.tracker.peers[requested_peer_ip]
            if peer_info['status'] == 'idle' and file_name in peer_info['files']:
                # Mark peer as busy and add to file_requests
                # peer_info['status'] = 'busy'
                peer_info['file_requests'].append(file_name)
                response = {
                    'type': 'PEER_CONTACT',
                    'peer_ip': requested_peer_ip[0],
                    'peer_port': peer_info['port']
                }
            else:
                if peer_info['status'] == 'busy':
                    self.tracker.log('Busy peer')
                else:
                    self.tracker.log('Not found')
                    self.tracker.log(peer_info['files'])
                    self.tracker.log(file_name)
                response = {'type': 'PEER_BUSY'}
        else:
            response = {'type': 'PEER_BUSY'}
        self.log(f"Sending response: {response}\n")
        self.writer.write(f"{json.dumps(response)}\n".encode('utf-8'))
        await self.writer.drain()

class CompleteTransfer(Action):
    """Handles the completion of file transfers."""
    async def execute(self):
        requested_peer_ip = self.message['peer_ip']
        if requested_peer_ip in self.tracker.peers:
            self.tracker.peers[requested_peer_ip]['status'] = 'idle'
            print(f"{Fore.GREEN}[TRACKER]{Style.RESET_ALL} Peer {requested_peer_ip} is now idle.")
