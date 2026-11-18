"""ダミー脳や将来のLLM出力を安全に検証・補正する。"""

import math
from numbers import Real


def _finite_number(value):
    """boolを除く有限の数値かを判定する。"""
    if not isinstance(value, Real) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def validate(
    decision: dict, room_state: dict, allowed_models: dict, max_items: int
) -> tuple[dict | None, list[str]]:
    """決定内容を検証し、境界値を補正して理由とともに返す。"""
    reasons = []
    if not isinstance(decision, dict):
        return None, ["決定がオブジェクトではありません"]
    if "say" not in decision or "action" not in decision:
        return None, ["必須キー say または action がありません"]
    if not isinstance(decision["say"], str) or not isinstance(decision["action"], str):
        return None, ["say と action は文字列である必要があります"]

    action = decision["action"]
    if action == "none":
        return {"say": decision["say"], "action": "none"}, reasons
    if action != "spawn":
        return None, ["action が spawn または none ではありません"]

    item = decision.get("item")
    if not isinstance(item, dict):
        return None, ["item がありません、またはオブジェクトではありません"]
    model = item.get("model")
    if not isinstance(model, str) or not isinstance(allowed_models, dict) or model not in allowed_models:
        return None, ["許可されていないモデルです"]

    if not isinstance(room_state, dict):
        return None, ["room_state の形式が不正です"]
    items = room_state.get("items")
    if not isinstance(items, list):
        return None, ["配置済みアイテム一覧の形式が不正です"]
    if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 0:
        return None, ["max_items の値が不正です"]
    if len(items) >= max_items:
        return None, ["配置数が上限に達しています"]

    position = item.get("position")
    if not isinstance(position, (list, tuple)) or len(position) != 3:
        return None, ["position は3つの数値である必要があります"]
    if not all(_finite_number(value) for value in position):
        return None, ["position に有限でない数値があります"]

    bounds = room_state.get("bounds")
    if not isinstance(bounds, dict):
        return None, ["bounds の形式が不正です"]
    validated_position = list(position)
    for index, axis in ((0, "x"), (2, "z")):
        axis_bounds = bounds.get(axis)
        if (
            not isinstance(axis_bounds, (list, tuple))
            or len(axis_bounds) != 2
            or not all(_finite_number(value) for value in axis_bounds)
            or axis_bounds[0] > axis_bounds[1]
        ):
            return None, [f"{axis} bounds の形式が不正です"]
        corrected = min(max(validated_position[index], axis_bounds[0]), axis_bounds[1])
        if corrected != validated_position[index]:
            reasons.append(f"{axis} 座標を bounds の範囲内に補正しました")
            validated_position[index] = corrected

    corrected_y = min(max(validated_position[1], 0.0), 5.0)
    if corrected_y != validated_position[1]:
        reasons.append("y 座標を 0〜5 の範囲内に補正しました")
        validated_position[1] = corrected_y

    target_height = item.get("target_height_m")
    if not _finite_number(target_height):
        return None, ["target_height_m は有限の数値である必要があります"]
    corrected_height = min(max(target_height, 0.1), 2.0)
    if corrected_height != target_height:
        reasons.append("target_height_m を 0.1〜2.0 の範囲内に補正しました")

    validated = {
        "say": decision["say"],
        "action": "spawn",
        "item": {
            "model": model,
            "position": validated_position,
            "target_height_m": corrected_height,
        },
    }
    return validated, reasons
