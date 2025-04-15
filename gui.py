import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QProgressBar, QListWidget, QFileDialog, QLineEdit, QScrollArea
)
from PyQt5.QtCore import Qt, QMetaObject, pyqtSignal
import threading
import logging
import argparse
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class P2PGUI(QMainWindow):
    save_path_requested = pyqtSignal(str, name="savePathRequested")

    def __init__(self, peer):
        super().__init__()
        self.peer = peer
        self.tracker_ip = peer.tracker_ip  # Use tracker IP from peer
        self.tracker_port = peer.tracker_port  # Use tracker port from peer
        self.init_ui()
        self.download_progress_bars = {}  # Track progress bars for each file
        self.download_status_labels = {}  # Track status labels for each file

        # Connect the signal to the slot
        self.save_path_requested.connect(self.get_save_path)

    def init_ui(self):
        self.setWindowTitle("P2P File Sharing System")
        self.setGeometry(100, 100, 800, 600)

        # Main layout
        main_layout = QVBoxLayout()

        # Shared Files Panel
        shared_files_label = QLabel("Shared Files")
        self.shared_files_list = QListWidget()
        add_files_button = QPushButton("Add Files")
        add_files_button.clicked.connect(self.add_files)

        shared_files_layout = QVBoxLayout()
        shared_files_layout.addWidget(shared_files_label)
        shared_files_layout.addWidget(self.shared_files_list)
        shared_files_layout.addWidget(add_files_button)

        # Available Files Panel
        available_files_label = QLabel("Available Files")
        self.available_files_list = QListWidget()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_available_files)

        available_files_layout = QVBoxLayout()
        available_files_layout.addWidget(available_files_label)
        available_files_layout.addWidget(self.available_files_list)
        available_files_layout.addWidget(refresh_button)

        download_button = QPushButton("Download Selected")
        download_button.clicked.connect(self.download_selected_files)

        available_files_layout.addWidget(download_button)

        # Remove the button for loading .torrent files
        # Automatically fetch .torrent files when a file is selected for download
        download_button.clicked.connect(self.download_selected_files)

        # Download Manager (Updated for multiple files)
        download_manager_label = QLabel("Download Manager")
        self.download_manager_layout = QVBoxLayout()
        self.download_manager_layout.addWidget(download_manager_label)

        # Add a scrollable area for multiple downloads
        self.download_manager_widget = QWidget()
        self.download_manager_widget.setLayout(self.download_manager_layout)
        self.download_manager_scroll = QScrollArea()
        self.download_manager_scroll.setWidget(self.download_manager_widget)
        self.download_manager_scroll.setWidgetResizable(True)

        # Replace the single progress bar and status label with the scrollable area
        download_manager_layout = QVBoxLayout()
        download_manager_layout.addWidget(download_manager_label)
        download_manager_layout.addWidget(self.download_manager_scroll)

        # Combine layouts
        top_layout = QHBoxLayout()
        top_layout.addLayout(shared_files_layout)
        top_layout.addLayout(available_files_layout)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(download_manager_layout)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def add_files(self):
        """Add files to share."""
        logging.info("Add Files button clicked.")
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, "Select Files to Share")
        logging.info(f"Files selected: {file_paths}")

        def process_files():
            for file_path in file_paths:
                try:
                    logging.info(f"Attempting to register file: {file_path}")
                    filename = self.peer.register_file(file_path)  # Register file with tracker
                    if filename:
                        logging.info(f"File registered successfully: {filename}")
                        # Update GUI directly on the main thread
                        self.shared_files_list.addItem(filename)
                        logging.info(f"Successfully updated GUI with filename: {filename}")
                    else:
                        logging.error(f"Failed to register file: {file_path}")
                except Exception as e:
                    logging.error(f"Exception occurred while adding file '{file_path}': {e}")

        threading.Thread(target=process_files).start()

    def download_selected_files(self):
        """Download selected files from the available files list."""
        selected_items = self.available_files_list.selectedItems()
        for item in selected_items:
            filename = item.text()

            # Check if the file is already being downloaded
            if filename in self.download_progress_bars:
                logging.warning(f"Download for '{filename}' is already in progress.")
                continue

            # Query tracker for peers sharing the file
            response = self.peer.query_tracker(filename)
            if response.get("status") == "success":
                peer_chunks = response.get("file_info", {})

                # Add progress bar and status label for the file
                progress_bar = QProgressBar()
                status_label = QLabel(f"Status: Downloading {filename}")
                self.download_manager_layout.addWidget(progress_bar)
                self.download_manager_layout.addWidget(status_label)

                self.download_progress_bars[filename] = progress_bar
                self.download_status_labels[filename] = status_label

                # Start the download in a separate thread
                threading.Thread(target=self.start_download, args=(filename,)).start()
            else:
                logging.error(f"Failed to query tracker for '{filename}': {response.get('message')}.")

    def get_save_path(self, filename):
        """Slot to open QFileDialog and get the save path."""
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File As", filename)
        self.save_path = save_path

    def start_download(self, filename):
        """Start downloading the selected file."""
        try:
            # Query tracker for file info
            request = {"action": "query", "filename": filename}
            response = self.peer.send_to_tracker(request)
            file_info = json.loads(response).get("file_info", {})

            if not file_info:
                logging.error(f"No file info found for '{filename}'.")
                return

            # Emit signal to request save path on the main thread
            self.save_path = None
            self.save_path_requested.emit(filename)

            # Wait for the save path to be set
            while self.save_path is None:
                QApplication.processEvents()

            if not self.save_path:
                logging.warning("Download canceled by user.")
                return

            # Initialize progress bar
            total_chunks = len(file_info)
            self.download_progress_bars[filename].setMaximum(total_chunks)

            # Define a callback to update the progress bar
            def update_progress(current_chunks, total_chunks):
                self.download_progress_bars[filename].setValue(current_chunks)

            # Start the download with the progress callback
            self.peer.download_file(filename, file_info, self.save_path, update_progress)

            # Remove progress bar and status label after download completes
            self.download_manager_layout.removeWidget(self.download_progress_bars[filename])
            self.download_manager_layout.removeWidget(self.download_status_labels[filename])
            self.download_progress_bars[filename].deleteLater()
            self.download_status_labels[filename].deleteLater()

            del self.download_progress_bars[filename]
            del self.download_status_labels[filename]
        except Exception as e:
            logging.error(f"Error starting download for '{filename}': {e}")

    def refresh_available_files(self):
        """Query the tracker for available files and update the list."""
        request = {"action": "list_files"}
        response = self.peer.send_to_tracker(request)

        if response:
            response_data = json.loads(response)
            if response_data.get("status") == "success":
                files = response_data.get("files", [])
                self.available_files_list.clear()
                for file in files:
                    self.available_files_list.addItem(file)
                logging.info("Available files updated.")
            else:
                logging.error(f"Failed to fetch available files: {response_data.get('message')}.")
        else:
            logging.error("No response from tracker while fetching available files.")

def main():
    parser = argparse.ArgumentParser(description="GUI for P2P File Sharing System")
    parser.add_argument("--peer-ip", required=True, help="IP address of the peer to connect to")
    parser.add_argument("--peer-port", type=int, required=True, help="Port of the peer to connect to")
    args = parser.parse_args()

    from peer import Peer

    # Example peer setup
    peer = Peer(ip=args.peer_ip, port=args.peer_port, tracker_ip="192.168.0.5", tracker_port=6881)

    app = QApplication(sys.argv)
    gui = P2PGUI(peer)
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
