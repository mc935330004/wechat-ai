"""Phase 0: inspect an existing Weixin window without navigating or sending."""

import argparse
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import hmac
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import secrets
import subprocess
import sys


class ChatMismatch(Exception):
    pass


def check(status, **evidence):
    return {"status": status, **evidence}


def find_wechat_window(titles=("微信", "Weixin")):
    """Resolve an existing native main window; never restore or activate it."""
    import psutil
    import win32gui
    import win32process
    process_ids = {p.pid for p in psutil.process_iter(["name"])
                   if (p.info["name"] or "").lower() in {"weixin.exe", "wechat.exe"}}
    handles = []
    def collect(handle, _):
        if (win32gui.IsWindowVisible(handle)
                and win32process.GetWindowThreadProcessId(handle)[1] in process_ids
                and win32gui.GetWindowText(handle) in titles):
            handles.append(handle)
    win32gui.EnumWindows(collect, None)
    if len(handles) != 1:
        raise ValueError("NO_UNIQUE_VISIBLE_MAIN_WINDOW")
    if win32gui.IsIconic(handles[0]):
        raise ValueError("WINDOW_MINIMIZED")
    return handles[0]


def read_test_chat(window, selectors, expected_chat, salt):
    """Display-name matching is a read scope, not a verified contact identity."""
    def current_title():
        return window.child_window(**selectors["title"]).wrapper_object().window_text()

    if current_title() != expected_chat:
        raise ChatMismatch()
    try:
        input_box = window.child_window(**selectors["input"]).wrapper_object()
        input_value = input_box.get_value()
        if not isinstance(input_value, str):
            raise TypeError("Input value unavailable")
    except Exception as error:
        input_result = {"input_readable": False, "input_error_type": type(error).__name__}
    else:
        input_result = {"input_readable": True, "input_empty": input_value == "",
                        "input_length": len(input_value)}
    message_list = window.child_window(**selectors["messages"]).wrapper_object()
    items = message_list.children(control_type="ListItem")
    messages = []
    # ponytail: inspect the last 20 rendered items; history navigation belongs later.
    for index, item in enumerate(items[-20:]):
        if current_title() != expected_chat:
            raise ChatMismatch()
        content = item.window_text()
        if not isinstance(content, str):
            raise TypeError("Message value unavailable")
        messages.append({
            "position": index,
            "control_class": item.class_name(),
            "content_length": len(content),
            "content_hmac": hmac.new(salt, content.encode("utf-8"), hashlib.sha256).hexdigest(),
            "direction": "UNVERIFIED",
        })
    if current_title() != expected_chat:
        raise ChatMismatch()
    return {
        "display_title_matched": True,
        **input_result,
        "rendered_message_count": len(items),
        "messages": messages,
        "redaction": "No plaintext; random per-run HMAC key is not retained.",
    }


def probe(expected_chat):
    result = {
        "schema_version": 1,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "effective_mode": "OFF",
        "read_only": True,
        "environment": {
            "python": platform.python_version(),
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
        },
        "checks": {},
        "route": "UNVERIFIED",
        "auto_eligible": False,
    }
    checks = result["checks"]
    for name in ("account_identity", "contact_identity", "message_direction",
                 "voice_transcription", "live_listener", "send_receipt",
                 "four_hour_observation"):
        checks[name] = check("UNVERIFIED")
    if sys.platform != "win32":
        checks["platform"] = check("FAIL", reason="WINDOWS_REQUIRED")
        return result
    try:
        # Import-only inspection: never call Navigator, AutoReply, Monitor or sender.
        with redirect_stdout(io.StringIO()):
            import pyweixin
            import pyautogui
            from pyweixin.Uielements import Main_window, Edits, Texts
            from pywinauto import Desktop
            from pywinauto.timings import Timings
            import psutil
            import win32api
            import win32gui
            import win32process
        # Upstream disables this at import; restore its fail-safe in this process.
        pyautogui.FAILSAFE = True
        result["environment"]["pywechat127"] = importlib.metadata.version("pywechat127")
        result["environment"]["pywinauto"] = importlib.metadata.version("pywinauto")
        checks["sdk_import"] = check("PASS")
        result["sdk_api_presence"] = {
            "listen_on_chat": callable(getattr(pyweixin.Monitor, "listen_on_chat", None)),
            "note": "Method presence only; not executed or verified.",
        }
        Timings.window_find_timeout = 2
        try:
            handle = find_wechat_window((Main_window.MainWindow["title"],))
        except ValueError as error:
            checks["main_window"] = check("BLOCKED", reason=str(error))
            return result
        process = psutil.Process(win32process.GetWindowThreadProcessId(handle)[1])
        version = win32api.GetFileVersionInfo(process.exe(), "\\")
        result["environment"]["wechat"] = ".".join(str(value) for value in (
            version["FileVersionMS"] >> 16, version["FileVersionMS"] & 65535,
            version["FileVersionLS"] >> 16, version["FileVersionLS"] & 65535))
        checks["main_window"] = check("PASS", native_class=win32gui.GetClassName(handle))
        desktop = Desktop(backend="uia")
        main = desktop.window(handle=handle).wrapper_object()
        child_types = Counter(child.element_info.control_type for child in main.children())
        checks["uia_children"] = check("PASS" if child_types else "FAIL",
                                       control_types=dict(child_types))
        if not child_types:
            checks["test_chat_read"] = check("BLOCKED", reason="UIA_TREE_UNAVAILABLE")
            return result
        if not expected_chat:
            checks["test_chat_read"] = check("UNVERIFIED", reason="EXPECTED_CHAT_REQUIRED")
            return result
        selectors = {"title": Texts.CurrentChatNameText, "input": Edits.CurrentChatEdit,
                     "messages": Main_window.FriendChatList}
        try:
            snapshot = read_test_chat(desktop.window(handle=main.handle), selectors,
                                      expected_chat, secrets.token_bytes(32))
        except ChatMismatch:
            checks["test_chat_read"] = check("BLOCKED", reason="CHAT_MISMATCH_OR_CHANGED")
        except Exception as error:
            checks["test_chat_read"] = check("FAIL", error_type=type(error).__name__)
        else:
            result["snapshot"] = snapshot
            checks["test_chat_read"] = check("PASS")
            checks["input_read"] = check("PASS" if snapshot["input_readable"] else "FAIL")
    except Exception as error:
        checks["probe_error"] = check("FAIL", error_type=type(error).__name__)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only", action="store_true", required=True)
    parser.add_argument("--expected-chat", help="Exact current test chat title; no auto-navigation")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "runtime/probe-latest.json")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(probe(args.expected_chat), ensure_ascii=True))
        return 0
    command = [sys.executable, str(Path(__file__).resolve()), "--read-only", "--worker"]
    if args.expected_chat:
        command += ["--expected-chat", args.expected_chat]
    try:
        # A hung provider can only hold this disposable probe for 30 seconds.
        child = subprocess.run(command, capture_output=True, text=True, timeout=30)
        report = json.loads(child.stdout) if child.returncode == 0 else {
            "read_only": True, "effective_mode": "OFF", "auto_eligible": False,
            "route": "UNVERIFIED", "checks": {"worker": check("FAIL", reason="WORKER_EXIT")}}
    except subprocess.TimeoutExpired:
        report = {"read_only": True, "effective_mode": "OFF", "auto_eligible": False,
                  "route": "UNVERIFIED", "checks": {"worker": check("FAIL", reason="UIA_TIMEOUT")}}
    except ValueError:
        report = {"read_only": True, "effective_mode": "OFF", "auto_eligible": False,
                  "route": "UNVERIFIED", "checks": {"worker": check("FAIL", reason="INVALID_REPORT")}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 2 if any(item["status"] in {"FAIL", "BLOCKED"}
                    for item in report["checks"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
