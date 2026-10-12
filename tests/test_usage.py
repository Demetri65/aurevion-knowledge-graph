import unittest

from aurevion_knowledge_lab.usage import UsageLedger


class UsageTests(unittest.TestCase):
    def test_ledger_deduplicates_and_never_retains_sensitive_inputs(self):
        ledger = UsageLedger()
        kwargs = {"model": "gemini/test", "response_cost": 0.002, "api_key": "not-a-real-key", "messages": [{"content": "private prompt"}]}
        response = {"id": "request1", "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}, "choices": [{"text": "private answer"}]}
        ledger.record(kwargs, response, 0, 1)
        ledger.record(kwargs, response, 0, 1)
        self.assertEqual(ledger.summary()["observed_requests"], 1)
        self.assertEqual(ledger.summary()["observed_total_tokens"], 14)
        self.assertNotIn("private", str(ledger.records))
        self.assertNotIn("not-a-real-key", str(ledger.records))

    def test_unknown_cost_is_not_reported_as_free(self):
        ledger = UsageLedger()
        ledger.record({"model": "test"}, {"id": "1", "usage": {}}, 0, 1)
        self.assertIsNone(ledger.summary()["estimated_api_cost_usd"])
        self.assertEqual(ledger.summary()["requests_missing_cost"], 1)


if __name__ == "__main__":
    unittest.main()
