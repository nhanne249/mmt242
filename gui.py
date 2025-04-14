import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QProgressBar, QListWidget, QFileDialog, QLineEdit, QScrollArea
)
from PyQt5.QtCore import Qt
import threading
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class P2PGUI(QMainWindow):
    def __init__(self, peer):
        super().__init__()
        self.peer = peer
        self.init_ui()
        self.download_progress_bars = {}  # Track progress bars for each file
        self.download_status_labels = {}  # Track status labels for each file

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
        download_button = QPushButton("Download Selected")
        download_button.clicked.connect(self.download_selected_files)

        available_files_layout = QVBoxLayout()
        available_files_layout.addWidget(available_files_label)
        available_files_layout.addWidget(self.available_files_list)
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

        # Settings Panel
        settings_label = QLabel("Settings")
        self.tracker_ip_input = QLineEdit()
        self.tracker_ip_input.setPlaceholderText("Tracker IP")
        self.tracker_port_input = QLineEdit()
        self.tracker_port_input.setPlaceholderText("Tracker Port")

        settings_layout = QVBoxLayout()
        settings_layout.addWidget(settings_label)
        settings_layout.addWidget(self.tracker_ip_input)
        settings_layout.addWidget(self.tracker_port_input)

        # Combine layouts
        top_layout = QHBoxLayout()
        top_layout.addLayout(shared_files_layout)
        top_layout.addLayout(available_files_layout)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(download_manager_layout)
        main_layout.addLayout(settings_layout)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def add_files(self):
        """Add files to share."""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, "Select Files to Share")
        for file_path in file_paths:
            self.peer.register_file(file_path)
            self.shared_files_list.addItem(file_path)
        logging.info(f"Added files for sharing: {file_paths}")

    def download_selected_files(self):
        """Download selected files from the available files list."""
        selected_items = self.available_files_list.selectedItems()
        for item in selected_items:
            filename = item.text()
            tracker_ip = self.tracker_ip_input.text()
            tracker_port = int(self.tracker_port_input.text())

            # Query tracker for peers sharing the file
            peer_list = self.peer.query_tracker(filename)

            # Fetch the .torrent file from one of the peers
            if peer_list:
                torrent_file = self.peer.fetch_torrent(filename, peer_list[0])
                if torrent_file:
                    # Add progress bar and status label for the file
                    progress_bar = QProgressBar()
                    status_label = QLabel(f"Status: Downloading {filename}")
                    self.download_manager_layout.addWidget(progress_bar)
                    self.download_manager_layout.addWidget(status_label)

                    self.download_progress_bars[filename] = progress_bar
                    self.download_status_labels[filename] = status_label

                    # Start the download in a separate thread
                    threading.Thread(target=self.start_download, args=(torrent_file, filename)).start()
                else:
                    logging.error(f"Failed to fetch .torrent file for '{filename}'.")
            else:
                logging.error(f"No peers found for '{filename}'.")
        logging.info(f"Started downloading files: {[item.text() for item in selected_items]}")

    def start_download(self, torrent_file, filename):
        """Start downloading a file and update the progress bar."""
        self.peer.download_torrent(torrent_file)
        self.download_status_labels[filename].setText(f"Status: Completed {filename}")
        self.download_progress_bars[filename].setValue(100)

if __name__ == "__main__":
    from peer import Peer

    # Example peer setup
    peer = Peer(ip="192.168.1.2", port=6882, tracker_ip="192.168.1.1", tracker_port=6881)

    app = QApplication(sys.argv)
    gui = P2PGUI(peer)
    gui.show()
    sys.exit(app.exec_())
