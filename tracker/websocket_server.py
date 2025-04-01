import asyncio
import websockets
import json

connected_peers = set()

async def handle_peer(websocket, path):
    connected_peers.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "UPDATE":
                await broadcast(data)
            elif data.get("type") == "ERROR":
                await websocket.send(json.dumps({"type": "ERROR", "message": data.get("message")}))
    except websockets.ConnectionClosed:
        print(f"Peer disconnected: {websocket.remote_address}")
    finally:
        connected_peers.remove(websocket)

async def broadcast(message):
    if connected_peers:
        await asyncio.wait([peer.send(json.dumps(message)) for peer in connected_peers])

start_server = websockets.serve(handle_peer, "0.0.0.0", 8765)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
