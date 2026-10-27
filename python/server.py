"""Unityへ配置コマンドを送る最小WebSocketサーバー。"""

import asyncio
import json
import uuid
from pathlib import Path

from websockets.asyncio.server import serve


HOST = "localhost"
PORT = 8765
clients = set()
client_connected = asyncio.Event()


async def handler(websocket):
    """Unityクライアントを登録し、受信した応答を表示する。"""
    clients.add(websocket)
    client_connected.set()
    print("Unityが接続しました")
    try:
        async for message in websocket:
            print(message)
    finally:
        clients.discard(websocket)
        if not clients:
            client_connected.clear()
        print("Unityが切断しました")


async def spawn_item(
    model_path,
    position,
    rotation=(0, 0, 0),
    scale=(1, 1, 1),
    target_height_m=0.0,
    mass=1.0,
):
    """指定モデルの配置コマンドを接続中の全Unityへ送る。"""
    command = {
        "command": "spawn_item",
        "id": uuid.uuid4().hex[:8],
        "model_path": str(Path(model_path).resolve()),
        "position": list(position),
        "rotation": list(rotation),
        "scale": list(scale),
        "target_height_m": target_height_m,
        "mass": mass,
    }
    message = json.dumps(command, ensure_ascii=False)
    if clients:
        await asyncio.gather(*(client.send(message) for client in tuple(clients)))
    else:
        print("接続中のUnityクライアントがありません")
    return command["id"]


async def main():
    """サーバーを起動し、Unity接続後にDuckを一度配置する。"""
    async with serve(handler, HOST, PORT):
        print(f"WebSocketサーバーを起動しました: ws://{HOST}:{PORT}")
        await client_connected.wait()
        duck_path = Path(__file__).resolve().parent.parent / "models" / "Duck.glb"
        await spawn_item(duck_path, (0, 2, 0), target_height_m=0.5)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
