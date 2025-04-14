import os
import hashlib
import json
import logging
from config import TORRENT_MAX_SIZE_KB

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Torrent:
    @staticmethod
    def create_torrent(filepath, tracker_ip, tracker_port, piece_size=None):
        """
        Create a .torrent metadata file for the given file.
        :param filepath: Path to the file to be shared.
        :param tracker_ip: IP address of the tracker.
        :param tracker_port: Port of the tracker.
        :param piece_size: Size of each piece in bytes (default: 1 MB).
        :return: Metadata dictionary.
        """
        if not os.path.exists(filepath):
            logging.error(f"File '{filepath}' does not exist.")
            raise FileNotFoundError(f"File '{filepath}' does not exist.")

        # Use the maximum size from config if piece_size is not provided
        piece_size = piece_size or (TORRENT_MAX_SIZE_KB * 1024)
        if piece_size > TORRENT_MAX_SIZE_KB * 1024:
            piece_size = TORRENT_MAX_SIZE_KB * 1024
            logging.warning(f"Piece size exceeds maximum allowed size. Using {piece_size} bytes.")

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        pieces = []

        try:
            with open(filepath, "rb") as f:
                while chunk := f.read(piece_size):
                    pieces.append(hashlib.sha1(chunk).hexdigest())
        except Exception as e:
            logging.error(f"Error reading file '{filepath}': {e}")
            raise

        metadata = {
            "filename": filename,
            "file_size": file_size,
            "piece_size": piece_size,
            "pieces": pieces,
            "tracker": f"{tracker_ip}:{tracker_port}"
        }

        torrent_file = os.path.join("data", f"{filename}.torrent")
        os.makedirs("data", exist_ok=True)  # Ensure the 'data' directory exists
        try:
            with open(torrent_file, "w") as f:
                json.dump(metadata, f, indent=4)
            logging.info(f".torrent file created: {torrent_file}")
        except Exception as e:
            logging.error(f"Error writing .torrent file '{torrent_file}': {e}")
            raise

        return metadata

    @staticmethod
    def parse_torrent(torrent_file):
        """
        Parse a .torrent metadata file.
        :param torrent_file: Path to the .torrent file.
        :return: Metadata dictionary.
        """
        if not os.path.exists(torrent_file):
            logging.error(f"Torrent file '{torrent_file}' does not exist.")
            raise FileNotFoundError(f"Torrent file '{torrent_file}' does not exist.")

        try:
            with open(torrent_file, "r") as f:
                metadata = json.load(f)
            logging.info(f"Parsed .torrent file: {torrent_file}")
        except json.JSONDecodeError as e:
            logging.error(f"Malformed .torrent file '{torrent_file}': {e}")
            raise
        except Exception as e:
            logging.error(f"Error reading .torrent file '{torrent_file}': {e}")
            raise

        return metadata

# Example usage
if __name__ == "__main__":
    try:
        # Create a .torrent file
        metadata = Torrent.create_torrent(
            filepath="path/to/file",
            tracker_ip="192.168.1.1",
            tracker_port=6881
        )
        print("Created .torrent metadata:", metadata)

        # Parse a .torrent file
        parsed_metadata = Torrent.parse_torrent("file.torrent")
        print("Parsed .torrent metadata:", parsed_metadata)
    except Exception as e:
        logging.error(f"Error in Torrent operations: {e}")
