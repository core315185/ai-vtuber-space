"""キーボード入力から検証済み配置コマンドをUnityへ送る。"""

import asyncio
from pathlib import Path

from websockets.asyncio.server import serve

try:
    from . import server
    from .brain import decide
    from .validator import validate
except ImportError:
    # `python main.py` で直接起動する場合の読み込み。
    import server
    from brain import decide
    from validator import validate


ROOT = Path(__file__).resolve().parent.parent
allowed_models = {"Duck": str((ROOT / "models" / "Duck.glb").resolve())}
max_items = 10
room_state = {
    "bounds": {"x": [-3, 3], "z": [-3, 3]},
    "spawn_height": 2.0,
    "items": [],
}


async def run_input_loop():
    """Unity接続後、標準入力を別スレッドから受け付けて処理する。"""
    while True:
        comment = await asyncio.to_thread(input, "コメントを入力してください（空行またはquitで終了）: ")
        if not comment.strip() or comment.strip().casefold() == "quit":
            print("終了します")
            return

        decision = decide(comment, room_state)
        validated, reasons = validate(decision, room_state, allowed_models, max_items)
        print(f"VTuber: {decision.get('say', '')}")
        for reason in reasons:
            print(f"検証: {reason}")

        if validated is None:
            print("配置を拒否しました")
            continue
        if validated["action"] == "none":
            continue

        item = validated["item"]
        print(
            f"配置要求: {item['model']} position={item['position']} "
            f"target_height_m={item['target_height_m']}"
        )
        try:
            ack = await server.spawn_item_and_wait(
                allowed_models[item["model"]],
                item["position"],
                target_height_m=item["target_height_m"],
            )
        except asyncio.TimeoutError:
            print("配置結果: ACK待ちがタイムアウトしました")
            continue
        except Exception as error:
            print(f"配置結果: 送信に失敗しました ({error})")
            continue

        if ack.get("ok") is True:
            room_state["items"].append(
                {"name": item["model"], "position": list(item["position"])}
            )
            print(f"配置成功: {item['model']} ({ack.get('message', '')})")
        else:
            print(f"配置失敗: {ack.get('message', 'unknown error')}")


async def main():
    """WebSocketサーバーを起動し、Unity接続を待って入力処理を始める。"""
    async with serve(server.handler, server.HOST, server.PORT):
        print(f"WebSocketサーバーを起動しました: ws://{server.HOST}:{server.PORT}")
        await server.client_connected.wait()
        await run_input_loop()


if __name__ == "__main__":
    asyncio.run(main())
