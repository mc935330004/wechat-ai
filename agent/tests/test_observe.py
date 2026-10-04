"""Fake-clock scheduling and stop guards; no real desktop or real four-hour evidence."""

import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
import observe


class ObservationTest(unittest.TestCase):
    def test_duration_guards_redaction_and_fail_closed(self):
        sample = {"read_only": True, "effective_mode": "OFF", "observed_at_utc": "synthetic",
                  "checks": {"title_ocr": {"status": "PASS"},
                             "two_sample_consistency": {"status": "FAIL"}},
                  "samples": [{"title_exact_match": True, "visible_message_line_count": 5,
                               "visible_input_line_count": 0, "text": "never persist this"}] * 2}
        for duration, interval in ((29, 30), (14401, 30), (60, 1), (30, 60)):
            with self.assertRaises(ValueError):
                observe.validate_options(duration, interval)
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(duration_seconds=30, interval_seconds=30,
                                      output=Path(directory) / "report.json")
            clock = [0.0]

            def sleep(seconds):
                clock[0] += seconds

            with patch.object(observe.time, "monotonic", side_effect=lambda: clock[0]), \
                    patch.object(observe.time, "sleep", side_effect=sleep), \
                    patch.object(observe, "read_once", return_value=sample) as reader:
                report = observe.run_observation(args)
            self.assertEqual("COMPLETED", report["state"])
            self.assertEqual(2, reader.call_count)
            self.assertEqual(30, report["observed_span_seconds"])
            self.assertEqual("UNVERIFIED", report["checks"]["four_hour_observation"]["status"])
            self.assertNotIn("never persist", args.output.read_text(encoding="utf-8"))
            self.assertFalse(args.output.with_name("report.json.tmp").exists())
            wrong_title = copy.deepcopy(sample)
            wrong_title["samples"][0]["title_exact_match"] = False
            for blocked in ({"checks": {"guard": {"status": "BLOCKED", "reason": "OCR_TITLE_MISMATCH"}}},
                            wrong_title, {"checks": {"worker": {"status": "FAIL"}}}):
                with patch.object(observe, "read_once", return_value=blocked) as reader:
                    report = observe.run_observation(args)
                self.assertEqual("STOPPED", report["state"])
                self.assertEqual(1, reader.call_count)
                self.assertEqual([], report["observations"])
                self.assertEqual("UNVERIFIED", report["checks"]["four_hour_observation"]["status"])
            self.assertEqual("STOPPED", json.loads(args.output.read_text(encoding="utf-8"))["state"])
            clock[0] = 0.0

            def stalled_probe(_):
                clock[0] += 100  # Synthetic suspended/hung run must not pass by elapsed time alone.
                return sample

            with patch.object(observe.time, "monotonic", side_effect=lambda: clock[0]), \
                    patch.object(observe.time, "sleep", side_effect=sleep), \
                    patch.object(observe, "read_once", side_effect=stalled_probe) as reader:
                report = observe.run_observation(args)
            self.assertEqual("OBSERVATION_GAP", report["checks"]["observation_run"]["reason"])
            self.assertEqual(1, reader.call_count)
            self.assertEqual("UNVERIFIED", report["checks"]["four_hour_observation"]["status"])


if __name__ == "__main__":
    unittest.main()
