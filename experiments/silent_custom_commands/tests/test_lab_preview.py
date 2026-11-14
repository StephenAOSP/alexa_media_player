"""Offline-only tests; no Home Assistant, AlexaPy, login, or network required."""
import importlib.util
from pathlib import Path
import unittest

MODULE = (
    Path(__file__).resolve().parents[1]
    / "home_assistant"
    / "custom_components"
    / "alexa_silent_lab"
    / "preview.py"
)
spec = importlib.util.spec_from_file_location("alexa_silent_lab_preview", MODULE)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewTests(unittest.TestCase):
    def test_candidate_differs_only_by_unverified_suppression_flag(self):
        result = preview.build_preview("Set an alarm for 1 a.m.")
        self.assertEqual(result["mode"], "offline_only")
        self.assertFalse(result["amazon_request_sent"])
        self.assertFalse(result["schema_verified"])
        self.assertEqual(result["baseline"]["operationPayload"]["text"],
                         result["candidate"]["operationPayload"]["text"])
        self.assertEqual(
            result["candidate"]["operationPayload"]["suppressResponse"], True
        )
        baseline = result["baseline"]["operationPayload"].copy()
        candidate = result["candidate"]["operationPayload"].copy()
        candidate.pop("suppressResponse")
        self.assertEqual(baseline, candidate)

    def test_opt_out_yields_same_payload(self):
        result = preview.build_preview("Hello", suppress_response=False)
        self.assertEqual(result["baseline"], result["candidate"])

    def test_empty_command_rejected(self):
        for value in ("", "   "):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    preview.build_preview(value)


if __name__ == "__main__":
    unittest.main()
