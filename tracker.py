from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory storage (file -> list of peers)
files = {}  # Example: {"file1.txt": [{"ip": "192.168.1.2", "port": 5001}]}

# Register a new peer and its files
@app.route("/register", methods=["POST"])
def register_peer():
    data = request.json  # Get JSON data from the peer
    ip = data.get("ip")
    port = data.get("port")
    file_list = data.get("files", [])

    if not ip or not port or not file_list:
        return jsonify({"error": "Missing parameters"}), 400

    # Store peer details for each file
    for file in file_list:
        if file not in files:
            files[file] = []
        peer_info = {"ip": ip, "port": port}
        if peer_info not in files[file]:
            files[file].append(peer_info)

    return jsonify({"message": "Peer registered successfully"}), 200

# Get the list of peers sharing a specific file
@app.route("/peers", methods=["GET"])
def get_peers():
    file_name = request.args.get("file")
    if not file_name or file_name not in files:
        return jsonify({"error": "File not found"}), 404

    return jsonify({"peers": files[file_name]}), 200

# Show all files currently tracked
@app.route("/files", methods=["GET"])
def list_files():
    return jsonify({"tracked_files": list(files.keys())}), 200

# Update peer status
@app.route("/update_status", methods=["POST"])
def update_status():
    data = request.json
    ip = data.get("ip")
    port = data.get("port")
    status = data.get("status")

    if not ip or not port or not status:
        return jsonify({"error": "Missing parameters"}), 400

    for file, peers in files.items():
        for peer in peers:
            if peer["ip"] == ip and peer["port"] == port:
                peer["status"] = status
                return jsonify({"message": "Status updated successfully"}), 200

    return jsonify({"error": "Peer not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)  # Run on port 8000
