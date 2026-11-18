"""Unityへ配置コマンドを送る最小WebSocketサーバー。"""

import asyncio
import json
import uuid
from pathlib import Path

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed


HOST = "localhost"
PORT = 8765
clients = set()
client_connected = asyncio.Event()
pending_acks = {}


async def handler(websocket):
    """Unityクライアントを登録し、受信した応答を表示する。"""
    clients.add(websocket)
    client_connected.set()
    print("Unityが接続しました")
    try:
        async for message in websocket:
            print(message)
            # ACKはIDごとの待機Futureへ渡し、呼び出し側で結果を確認できるようにする。
            try:
                response = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(response, dict) and response.get("type") == "ack":
                ack_id = response.get("id")
                if isinstance(ack_id, str):
                    waiter = pending_acks.get(ack_id)
                    if waiter is not None and not waiter.done():
                        waiter.set_result(response)
    except ConnectionClosed:
        pass
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
    command = _make_spawn_command(
        model_path, position, rotation, scale, target_height_m, mass
    )
    await _broadcast(command)
    return command["id"]


async def spawn_item_and_wait(
    model_path,
    position,
    rotation=(0, 0, 0),
    scale=(1, 1, 1),
    target_height_m=0.0,
    mass=1.0,
    timeout=30.0,
):
    """配置コマンドを送り、Unityから対応するACKが届くまで待つ。"""
    command = _make_spawn_command(
        model_path, position, rotation, scale, target_height_m, mass
    )
    waiter = asyncio.get_running_loop().create_future()
    pending_acks[command["id"]] = waiter
    try:
        await _broadcast(command)
        return await asyncio.wait_for(waiter, timeout=timeout)
    finally:
        pending_acks.pop(command["id"], None)


def _make_spawn_command(model_path, position, rotation, scale, target_height_m, mass):
    """Unityへ送る配置コマンドを組み立てる。"""
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
    return command


async def _broadcast(command):
    """配置コマンドを現在接続中の全クライアントへ送る。"""
    message = json.dumps(command, ensure_ascii=False)
    if clients:
        await asyncio.gather(*(client.send(message) for client in tuple(clients)))
    else:
        print("接続中のUnityクライアントがありません")


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
