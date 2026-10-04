"""Synthetic canary flow, never reads WeChat or sends real messages."""

import argparse
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
import receive_test


class ReceiveTest(unittest.TestCase):
    def test_scoped_canary_retry_and_receipt(self):
        def frame(count, status="PASS"):
            return {"read_only": True, "effective_mode": "OFF", "checks": {"title_ocr": {"status": "PASS"}},
                    "samples": [{"title_exact_match": True, "prepared_messages": {
                        "scenario": "pipeline", "status": status,
                        "markers": [{"observed_count": count}]}} for _ in range(2)]}

        for url in ("https://example.com", "http://localhost:8997", "http://127.0.0.1:8997?token=x",
                    "http://user@127.0.0.1:8997", "http://127.0.0.1:8997/elsewhere"):
            with self.assertRaises(ValueError):
                receive_test.validate_backend(url)
        self.assertEqual("http://127.0.0.1:8997", receive_test.validate_backend("http://127.0.0.1:8997/"))
        for invalid in (frame(1, "FAIL"), frame(2), {"checks": {"guard": {"status": "BLOCKED"}}}):
            with self.assertRaises(receive_test.TestBlocked):
                receive_test.marker_state(invalid)
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(duration_seconds=90, backend_url="http://127.0.0.1:8997",
                                      output=Path(directory) / "result.json")
            clock = [0]
            posted = []

            def exchange(url, token, payload=None):
                if payload is None:
                    return []
                posted.append(copy.deepcopy(payload))
                if len(posted) == 1:
                    raise URLError("simulated lost response")
                message = copy.deepcopy(payload)
                message["observedAt"] = message["observedAt"].replace("+00:00", "Z")
                return {"message": message, "status": "ACCEPTED", "effectiveMode": "OFF"}

            with patch.object(receive_test.time, "monotonic", side_effect=lambda: clock[0]), \
                    patch.object(receive_test.time, "sleep", side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)), \
                    patch.object(receive_test, "read_once", side_effect=[frame(0), frame(1)]), \
                    patch.object(receive_test, "exchange", side_effect=exchange):
                result = receive_test.run_test(args, "never-log-this-token")
            self.assertEqual("RECEIVED_BY_BACKEND", result["state"])
            self.assertEqual(posted[0], posted[1])
            self.assertNotIn("never-log-this-token", args.output.read_text(encoding="utf-8"))
            self.assertFalse(receive_test.receipt_matches({"message": posted[0], "status": "ACCEPTED", "effectiveMode": "AUTO"}, posted[0]))
            with patch.object(receive_test, "read_once", return_value=frame(1)), \
                    patch.object(receive_test, "exchange", return_value=[]):
                blocked = receive_test.run_test(args, "token")
            self.assertEqual("MARKER_ALREADY_VISIBLE_USE_A_FRESH_TEST", blocked["reason"])


if __name__ == "__main__":
    unittest.main()
