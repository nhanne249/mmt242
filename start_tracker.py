import threading
from Server import app, start_websocket_server, start_inactive_peer_removal, PeerFileReceiver

websocket_server_instance = None

def stop_websocket_server():
    global websocket_server_instance
    if websocket_server_instance:
        print("Stopping WebSocket server...")
        websocket_server_instance.close()
        websocket_server_instance = None

def run_tracker():
    # Start the WebSocket server in a separate thread
    threading.Thread(target=start_websocket_server, daemon=True).start()

    # Start the periodic inactive peer removal task
    threading.Thread(target=start_inactive_peer_removal, daemon=True).start()

    # Start the file receiver server in a separate thread
    threading.Thread(target=PeerFileReceiver(store_folder="store").start, daemon=True).start()

    try:
        # Start the Flask app
        app.run(host="0.0.0.0", port=1108, debug=False)  # Disable debug mode
    except KeyboardInterrupt:
        stop_websocket_server()  # Ensure WebSocket server is stopped on exit

if __name__ == "__main__":
    run_tracker()