"""OCR trust boundaries; fake frame checks do not interact with the desktop."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
import ocr_probe


class OcrGuardTest(unittest.TestCase):
    def test_prepared_markers_are_scoped_and_require_distinct_rows(self):
        layout = json.loads((Path(__file__).parents[1] / "ocr-layout.json").read_text(encoding="utf-8"))

        def line(text, x=100, y=100, confidence=0.99):
            return {"text": text, "rect": [x, y, 200, 25], "confidence": confidence}

        incoming = line("WXIN20261004A")
        outgoing = line("WXOUT20261004A", x=1100, y=200)
        self.assertEqual("PASS", ocr_probe.assess_prepared_messages(
            [incoming, outgoing, line("private other message", y=300)], layout, "direction")["status"])
        self.assertEqual("PASS", ocr_probe.assess_prepared_messages(
            [incoming, outgoing, line("WXIN20261004B"), line("WXOUT20261004B", x=1100, y=200)],
            layout, "direction-b")["status"])  # Old A markers do not affect the new round.
        self.assertEqual("FAIL", ocr_probe.assess_prepared_messages(
            [incoming, line("WXOUT20261004A", y=200)], layout, "direction")["status"])
        self.assertEqual("FAIL", ocr_probe.assess_prepared_messages(
            [incoming, line("WXOUT20261004A", x=1100, y=200, confidence=0.8)],
            layout, "direction")["status"])
        duplicates = [line("WXDUP20261004", y=y) for y in (100, 200)]
        evidence = ocr_probe.assess_prepared_messages(duplicates, layout, "duplicates")
        self.assertEqual("PASS", evidence["status"])
        self.assertEqual(2, evidence["markers"][0]["observed_count"])
        self.assertNotIn("WXDUP20261004", json.dumps(evidence))
        for invalid in (duplicates[:1], [duplicates[0]] * 2,
                        duplicates + [line("WXDUP20261004", y=300)]):
            self.assertEqual("FAIL", ocr_probe.assess_prepared_messages(
                invalid, layout, "duplicates")["status"])
        for scenario, prefix in (("sequence", "WXSEQ20261004"), ("sequence-dup", "WXDUP20261004")):
            sequence = [line(prefix + suffix, y=100 + index * 100)
                        for index, suffix in enumerate("ABC")]
            self.assertEqual("PASS", ocr_probe.assess_prepared_messages(sequence, layout, scenario)["status"])
            if scenario == "sequence-dup":
                self.assertEqual("FAIL", ocr_probe.assess_prepared_messages(sequence, layout, "sequence")["status"])
                self.assertEqual("FAIL", ocr_probe.assess_prepared_messages(sequence, layout, "duplicates")["status"])
            sequence[0]["rect"][1], sequence[2]["rect"][1] = 300, 100
            self.assertEqual("FAIL", ocr_probe.assess_prepared_messages(sequence, layout, scenario)["status"])
        with self.assertRaises(ocr_probe.GuardFailure):
            ocr_probe.assess_prepared_messages([line("WXDUP20261004", x=-1)], layout, "duplicates")
        with patch.object(ocr_probe, "recognize", side_effect=[
                [{"text": "allowed chat", "confidence": 0.99}],
                [incoming, outgoing, line("private other message", y=300)], []]):
            sample = ocr_probe.read_frame(None, layout, "allowedchat", None, b"salt", Path("."),
                                          message_check="direction")
        self.assertEqual("PASS", sample["prepared_messages"]["status"])
        self.assertNotIn("private", json.dumps(sample))
        with patch.object(ocr_probe, "recognize", side_effect=[
                [{"text": "allowed chat", "confidence": 0.99}],
                [line("prefix WXIN20261004A")], [outgoing]]):
            sample = ocr_probe.read_frame(None, layout, "allowedchat", None, b"salt", Path("."),
                                          message_check="direction")
        self.assertEqual("FAIL", sample["prepared_messages"]["status"])
        self.assertTrue(sample["marker_diagnostics"][0]["embedded_in_message_line"])
        self.assertTrue(sample["marker_diagnostics"][1]["exact_in_input"])
        self.assertNotIn("prefix", json.dumps(sample))

    def test_scope_layout_and_redaction(self):
        layout = json.loads((Path(__file__).parents[1] / "ocr-layout.json").read_text(encoding="utf-8"))
        ocr_probe.verify_layout(layout["client_size"], layout["dpi"], layout["calibrated_wechat_version"], layout)
        for size, dpi, version in (([1200, 800], 120, "4.1.15.13"),
                                   ([1100, 800], 96, "4.1.15.13"),
                                   ([1100, 800], 120, "4.1.16.0")):
            with self.assertRaises(ocr_probe.GuardFailure):
                ocr_probe.verify_layout(size, dpi, version, layout)
        self.assertTrue(ocr_probe.title_matches([{"text": "文 件 传 输 助 手"}], "文件传输助手"))
        self.assertFalse(ocr_probe.title_matches([{"text": "文任牛传输助手"}], "文件传输助手"))
        self.assertFalse(ocr_probe.title_matches([{"text": "文件传输助手", "confidence": 0.8}], "文件传输助手"))
        self.assertFalse(ocr_probe.title_matches([{"text": "文件传输助手"}] * 2, "文件传输助手"))
        with patch.object(ocr_probe, "recognize", return_value=[{"text": "another chat"}]) as recognition:
            with self.assertRaises(ocr_probe.GuardFailure):
                ocr_probe.read_frame(None, layout, "文件传输助手", None, b"salt", Path("."))
            self.assertEqual(1, recognition.call_count)  # Never read message/input regions after mismatch.
        self.assertNotIn("private", str(ocr_probe.redact_lines(
            [{"text": "private text", "rect": [0, 0, 10, 10]}], b"salt")))


if __name__ == "__main__":
    unittest.main()
