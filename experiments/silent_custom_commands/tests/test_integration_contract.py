"""Contract test for the integration-to-AlexaPy custom command boundary.

Run with: python -m unittest discover -s experiments/silent_custom_commands/tests -v
This deliberately avoids importing Home Assistant or contacting Amazon.
"""
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAYER = ROOT / "custom_components" / "alexa_media" / "media_player.py"


class CustomCommandContractTests(unittest.TestCase):
    def test_custom_handler_forwards_kwargs_to_run_custom(self):
        tree = ast.parse(PLAYER.read_text(encoding="utf-8"))
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run_custom"
        ]
        self.assertGreaterEqual(len(calls), 1, "run_custom call missing")
        for call in calls:
            self.assertTrue(any(kw.arg is None and isinstance(kw.value, ast.Name)
                                and kw.value.id == "kwargs" for kw in call.keywords),
                            "Custom command no longer forwards **kwargs")
            self.assertTrue(any(kw.arg == "customer_id" for kw in call.keywords))
            self.assertTrue(any(kw.arg == "queue_delay" for kw in call.keywords))

    def test_manifest_pins_target_alexapy(self):
        import json
        manifest = json.loads(
            (ROOT / "custom_components" / "alexa_media" / "manifest.json")
            .read_text(encoding="utf-8")
        )
        self.assertIn("alexapy==1.34.0", manifest["requirements"])


if __name__ == "__main__":
    unittest.main()
