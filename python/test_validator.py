"""validator の入力検証と補正を確認する標準ライブラリテスト。"""

import math
import unittest

try:
    from .validator import validate
except ImportError:
    from validator import validate


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.room_state = {
            "bounds": {"x": [-3, 3], "z": [-3, 3]},
            "spawn_height": 2.0,
            "items": [],
        }
        self.allowed_models = {"Duck": "models/Duck.glb"}
        self.decision = {
            "say": "アヒルを置くね！",
            "action": "spawn",
            "item": {
                "model": "Duck",
                "position": [1.0, 2.0, -0.5],
                "target_height_m": 0.5,
            },
        }

    def test_valid_decision(self):
        validated, reasons = validate(
            self.decision, self.room_state, self.allowed_models, 10
        )
        self.assertEqual(validated, self.decision)
        self.assertEqual(reasons, [])

    def test_out_of_bounds_position_is_clamped(self):
        decision = {**self.decision, "item": {**self.decision["item"], "position": [9, 8, -9]}}
        validated, reasons = validate(decision, self.room_state, self.allowed_models, 10)
        self.assertEqual(validated["item"]["position"], [3, 5.0, -3])
        self.assertEqual(len(reasons), 3)

    def test_unknown_model_is_rejected(self):
        decision = {**self.decision, "item": {**self.decision["item"], "model": "Chair"}}
        self.assertIsNone(validate(decision, self.room_state, self.allowed_models, 10)[0])

    def test_missing_required_key_is_rejected(self):
        decision = {"say": "hello"}
        self.assertIsNone(validate(decision, self.room_state, self.allowed_models, 10)[0])

    def test_wrong_type_is_rejected(self):
        decision = {**self.decision, "say": 42}
        self.assertIsNone(validate(decision, self.room_state, self.allowed_models, 10)[0])

    def test_nan_is_rejected(self):
        decision = {
            **self.decision,
            "item": {**self.decision["item"], "position": [math.nan, 2, 0]},
        }
        self.assertIsNone(validate(decision, self.room_state, self.allowed_models, 10)[0])

    def test_item_limit_is_rejected(self):
        room_state = {**self.room_state, "items": [{}] * 10}
        self.assertIsNone(validate(self.decision, room_state, self.allowed_models, 10)[0])


if __name__ == "__main__":
    unittest.main()
