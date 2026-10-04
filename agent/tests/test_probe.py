"""Trust-boundary checks with fake controls; no desktop or SDK imports."""

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("probe", Path(__file__).parents[1] / "tools/probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Control:
    def window_text(self):
        return "private message"

    def class_name(self):
        return "mmui::ChatTextItemView"

    def get_value(self):
        return "private draft"

    def children(self, **kwargs):
        return [self, self]

    def wrapper_object(self):
        return self


class Window:
    def __init__(self, titles):
        self.titles = iter(titles)
        self.content_reads = 0

    def child_window(self, kind):
        control = Control()
        if kind == "title":
            control.window_text = lambda: next(self.titles)
        else:
            self.content_reads += 1
        return control


class ReadScopeTest(unittest.TestCase):
    selectors = {key: {"kind": key} for key in ("title", "input", "messages")}

    def test_scope_and_redaction(self):
        mismatch = Window(["another chat"])
        with self.assertRaises(probe.ChatMismatch):
            probe.read_test_chat(mismatch, self.selectors, "test", b"salt")
        self.assertEqual(0, mismatch.content_reads)

        changed = Window(["test", "another chat"])
        with self.assertRaises(probe.ChatMismatch):
            probe.read_test_chat(changed, self.selectors, "test", b"salt")

        matched = Window(["test"] * 4)
        snapshot = probe.read_test_chat(matched, self.selectors, "test", b"salt")
        self.assertNotIn("private", str(snapshot))
        self.assertFalse(snapshot["input_empty"])
        self.assertEqual(snapshot["messages"][0]["content_hmac"],
                         snapshot["messages"][1]["content_hmac"])
        self.assertEqual("UNVERIFIED", snapshot["messages"][0]["direction"])


if __name__ == "__main__":
    unittest.main()
