import asyncio
from hashlib import sha1
from collections import defaultdict

class DownloadManager:
    def __init__(self, torrent, peers):
        self.torrent = torrent
        self.peers = peers
        self.pieces = defaultdict(list)

    async def download(self):
        rarest_pieces = self._get_rarest_pieces()
        for piece in rarest_pieces:
            await self._download_piece(piece)

    def _get_rarest_pieces(self):
        piece_count = defaultdict(int)
        for peer in self.peers:
            for piece in peer["pieces"]:
                piece_count[piece] += 1
        return sorted(piece_count, key=piece_count.get)

    async def _download_piece(self, piece):
        for peer in self.peers:
            if piece in peer["pieces"]:
                data = await self._request_piece(peer, piece)
                if self._verify_piece(piece, data):
                    self.pieces[piece] = data
                    break

    async def _request_piece(self, peer, piece):
        await asyncio.sleep(1)
        return b"piece_data"

    def _verify_piece(self, piece, data):
        return sha1(data).digest() == self.torrent.pieces[piece]
