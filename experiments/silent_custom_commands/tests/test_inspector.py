import unittest
from inspect_alexapy import extract_functions


class InspectorTests(unittest.TestCase):
    def test_extracts_only_named_functions_without_executing_them(self):
        source = '''\nclass AlexaAPI:\n    async def run_custom(self, text, extra=None):\n        raise RuntimeError("must not execute")\n    async def unrelated(self):\n        pass\n'''
        results = list(extract_functions(source))
        self.assertEqual([x[0] for x in results], ["run_custom"])
        self.assertIn("extra=None", results[0][2])


if __name__ == "__main__":
    unittest.main()
