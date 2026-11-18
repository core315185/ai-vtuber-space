"""入力コメントを配置判断へ変換するルールベースのダミー脳。"""

import random


def decide(comment: str, room_state: dict) -> dict:
    """配置判断関数。将来はこの関数だけをLLM呼び出しへ差し替える。"""
    lowered = comment.casefold()
    if not any(word in lowered for word in ("アヒル", "ダック", "duck")):
        return {"say": "それは置けないみたい", "action": "none"}

    bounds = room_state["bounds"]
    spawn_height = room_state["spawn_height"]
    return {
        "say": "アヒルを置くね！",
        "action": "spawn",
        "item": {
            "model": "Duck",
            "position": [
                random.uniform(bounds["x"][0], bounds["x"][1]),
                spawn_height,
                random.uniform(bounds["z"][0], bounds["z"][1]),
            ],
            "target_height_m": 0.5,
        },
    }
