import socket
import threading
import logging
import os

class SeedingPeer:
    def __init__(self, host, port, uploaded, piece_size=1024):
        self.host = host
        self.port = port
        self.uploaded = uploaded
        self.piece_size = piece_size
        self.running = False
        self.server_socket = None
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='peer_upload.log',
            filemode='a'
        )
        self.logger = logging.getLogger('SeedingPeer')
        
        if not os.path.exists("uploaded"):
            os.makedirs("uploaded")
        
    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.logger.info(f"Seeding peer started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    self.logger.info(f"Connection from {client_address}")
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Connection error: {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"Startup failed: {str(e)}")
            raise
            
    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.logger.info("Seeding peer stopped")
        
    def handle_client(self, client_socket, client_address):
        try:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:
                self.logger.info(f"Empty request from {client_address}")
                return
                
            self.logger.info(f"Request from {client_address}: {request}")
            
            if request.startswith("GET_PIECE:"):
                parts = request.split(':')
                if len(parts) == 3:
                    _, file_id, piece_index = parts
                    try:
                        piece_index = int(piece_index)
                        self.send_piece(client_socket, file_id, piece_index)
                    except ValueError:
                        client_socket.sendall(b"ERROR:INVALID_PIECE_INDEX")
                else:
                    client_socket.sendall(b"ERROR:INVALID_REQUEST_FORMAT")
            else:
                client_socket.sendall(b"ERROR:UNSUPPORTED_REQUEST")
                
        except Exception as e:
            self.logger.error(f"Client error {client_address}: {str(e)}")
        finally:
            client_socket.close()
            self.logger.info(f"Closed connection with {client_address}")
            
    def send_piece(self, client_socket, file_id, piece_index):
        file_path = os.path.join("uploaded", file_id)
        
        if not os.path.exists(file_path):
            client_socket.sendall(b"ERROR:FILE_NOT_FOUND")
            return
            
        file_size = os.path.getsize(file_path)
        total_pieces = (file_size + self.piece_size - 1) // self.piece_size
        
        if piece_index < 0 or piece_index >= total_pieces:
            client_socket.sendall(b"ERROR:INVALID_PIECE_INDEX")
            return
            
        offset = piece_index * self.piece_size
        bytes_to_send = min(self.piece_size, file_size - offset)
        
        try:
            with open(file_path, 'rb') as f:
                f.seek(offset)
                piece_data = f.read(bytes_to_send)
                
            header = f"PIECE:{piece_index}:{bytes_to_send}:".encode('utf-8')
            client_socket.sendall(header + piece_data)
            
        except Exception as e:
            client_socket.sendall(b"ERROR:INTERNAL_ERROR")

    def send_file_to_receiver(self, file_name, receiver_host="127.0.0.1", receiver_port=6000):
        """Send a file to the PeerFileReceiver."""
        file_path = os.path.join("uploaded", file_name)
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return

        try:
            with socket.create_connection((receiver_host, receiver_port)) as sock:
                # Send file name followed by a newline as a delimiter
                sock.sendall(f"{file_name}\n".encode("utf-8"))
                with open(file_path, "rb") as f:
                    while chunk := f.read(1024):
                        sock.sendall(chunk)
            self.logger.info(f"File {file_name} sent to {receiver_host}:{receiver_port}")
        except Exception as e:
            self.logger.error(f"Failed to send file {file_name} to receiver: {e}")


if __name__ == "__main__":
    uploaded = {
        "file1": "uploaded/fileA1.txt",
        "file2": "uploaded/fileA2.txt"
    }
    
    peer = SeedingPeer("0.0.0.0", 5000, uploaded)
    
    try:
        # Start the seeding peer in a separate thread
        threading.Thread(target=peer.start, daemon=True).start()

        # Send files to PeerFileReceiver
        for file_name in uploaded.values():
            peer.send_file_to_receiver(os.path.basename(file_name))
    except KeyboardInterrupt:
        peer.stop()