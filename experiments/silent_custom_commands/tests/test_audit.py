import unittest
from audit_alexapy import audit


class AuditTests(unittest.TestCase):
    def test_reports_arguments_and_call_keywords(self):
        source = """
class API:
    async def run_custom(self, text, extra=None):
        await self.send_sequence(text, extra=extra)
    async def send_sequence(self, text, extra=None):
        await self.run_behavior(text)
    async def run_behavior(self, node):
        await self._post_request("/api/behaviors/preview", data=node)
"""
        found = {entry["method"]: entry for entry in audit(source)}
        self.assertEqual(set(found), {"run_custom", "send_sequence", "run_behavior"})
        self.assertEqual(found["run_custom"]["calls"][0]["keywords"], ["extra"])
        self.assertEqual(found["run_behavior"]["calls"][0]["callee"], "_post_request")

    def test_does_not_execute_code(self):
        source = """
async def run_custom():
    raise AssertionError("must never execute")
"""
        self.assertEqual(audit(source)[0]["method"], "run_custom")


if __name__ == "__main__":
    unittest.main()
