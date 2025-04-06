import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QProgressBar, QListWidget, QFileDialog, QLineEdit
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

        # Download Manager
        download_manager_label = QLabel("Download Manager")
        self.download_progress = QProgressBar()
        self.download_status = QLabel("Status: Idle")

        download_manager_layout = QVBoxLayout()
        download_manager_layout.addWidget(download_manager_label)
        download_manager_layout.addWidget(self.download_progress)
        download_manager_layout.addWidget(self.download_status)

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
            peer_list = self.peer.query_tracker(filename)
            threading.Thread(target=self.peer.download_file, args=(filename, peer_list)).start()
            self.download_status.setText(f"Downloading: {filename}")
        logging.info(f"Started downloading files: {[item.text() for item in selected_items]}")

    def update_download_progress(self, progress):
        """Update the download progress bar."""
        self.download_progress.setValue(progress)

if __name__ == "__main__":
    from peer import Peer

    # Example peer setup
    peer = Peer(ip="192.168.1.2", port=6882, tracker_ip="192.168.1.1", tracker_port=6881)

    app = QApplication(sys.argv)
    gui = P2PGUI(peer)
    gui.show()
    sys.exit(app.exec_())
