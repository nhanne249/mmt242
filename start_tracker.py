import threading
from Server import app, start_websocket_server, start_inactive_peer_removal

def run_tracker():
    # Start the WebSocket server in a separate thread
    threading.Thread(target=start_websocket_server, daemon=True).start()

    # Start the periodic inactive peer removal task
    threading.Thread(target=start_inactive_peer_removal, daemon=True).start()

    # Start the Flask app
    app.run(host="0.0.0.0", port=1108, debug=True)

if __name__ == "__main__":
    run_tracker()