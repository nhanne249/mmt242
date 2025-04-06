# BitTorrent-Based P2P File Sharing System

## Overview
This system implements a BitTorrent-based P2P file sharing system with a centralized tracker and peer nodes. It includes a GUI for managing shared files, downloads, and uploads.

## Setup Instructions

### 1. Start the Tracker
Run the tracker on the designated VM:
```bash
python3 tracker.py --ip <TRACKER_IP> --port 6881
```

### 2. Start a Peer Node
Run the peer on another VM:
```bash
python3 peer.py --ip <PEER_IP> --port 6882 --tracker-ip <TRACKER_IP> --tracker-port 6881
```

### 3. Use the GUI
- Launch the GUI by running `gui.py`:
  ```bash
  python3 gui.py
  ```
- Use the GUI to:
  - Add files to share.
  - View available files from the tracker.
  - Download files and monitor progress.

## Testing
1. Share files from one peer and register them with the tracker.
2. Query the tracker from another peer to view available files.
3. Download files concurrently from multiple peers.
4. Verify file integrity using SHA-1 hashing.

## Notes
- Ensure all VMs are on the same network and have unique IPs.
- Use real IPs (e.g., 192.168.x.x) for all socket connections.
