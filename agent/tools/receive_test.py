"""Controlled new IN canary -> local Spring Boot receipt; no general message listener."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import uuid

from observe import read_once, save_report

MARKER = "WXPIPE20261004A"


class TestBlocked(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def validate_backend(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username
            or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or parsed.port is None or not 1 <= parsed.port <= 65535):
        raise ValueError("Backend must be http://127.0.0.1:<port>")
    return url.rstrip("/")


def exchange(url, token, payload=None):
    request = Request(url + "/api/v1/dev/probe-messages",
                      data=json.dumps(payload).encode("utf-8") if payload else None,
                      headers={"X-Probe-Token": token, "Content-Type": "application/json"})
    with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=5) as response:
        body = response.read(65537)
        if len(body) > 65536:
            raise TestBlocked("BACKEND_RESPONSE_TOO_LARGE")
        return json.loads(body)


def marker_state(report):
    for name, item in report.get("checks", {}).items():
        if name not in ("two_sample_consistency", "prepared_pipeline") and item.get("status") in ("FAIL", "BLOCKED"):
            raise TestBlocked(item.get("reason", "OCR_PROBE_FAILED"))
    if (report.get("read_only") is not True or report.get("effective_mode") != "OFF"
            or report.get("checks", {}).get("title_ocr", {}).get("status") != "PASS"
            or len(report.get("samples", [])) != 2):
        raise TestBlocked("INVALID_SCOPED_SAMPLE")
    counts = []
    for frame in report["samples"]:
        if frame.get("title_exact_match") is not True:
            raise TestBlocked("OCR_TITLE_MISMATCH")
        prepared = frame["prepared_messages"]
        if prepared["scenario"] != "pipeline" or len(prepared["markers"]) != 1:
            raise TestBlocked("INVALID_TEST_MARKER_EVIDENCE")
        count = prepared["markers"][0]["observed_count"]
        if count > 1:
            raise TestBlocked("AMBIGUOUS_REPEATED_TEST_MARKER")
        if count == 1 and prepared["status"] != "PASS":
            raise TestBlocked("TEST_MARKER_DIRECTION_OR_CONFIDENCE_FAILED")
        counts.append(count)
    return counts


def receipt_matches(receipt, payload):
    message = receipt.get("message", {})
    if (receipt.get("status") != "ACCEPTED" or receipt.get("effectiveMode") != "OFF"
            or any(message.get(key) != payload[key] for key in payload if key != "observedAt")):
        return False
    try:
        return (datetime.fromisoformat(message["observedAt"].replace("Z", "+00:00"))
                == datetime.fromisoformat(payload["observedAt"].replace("Z", "+00:00")))
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def run_test(args, token):
    started = time.monotonic()
    result = {"state": "STARTING", "effective_mode": "OFF", "read_only_wechat": True,
              "evidence_source": "REAL_DESKTOP_OCR", "marker": MARKER,
              "backend_url": args.backend_url, "agent_run_id": str(uuid.uuid4()),
              "scope": "One fresh known IN marker in the manually opened test chat only"}
    save_report(args.output, result)
    try:
        exchange(args.backend_url, token)  # Check backend/token before arming the desktop test.
        if marker_state(read_once(args)) != [0, 0]:
            raise TestBlocked("MARKER_ALREADY_VISIBLE_USE_A_FRESH_TEST")
        result["state"] = "ARMED"
        result["armed_at_utc"] = datetime.now(timezone.utc).isoformat()
        save_report(args.output, result)
        print("ARMED: ask the other account to send " + MARKER + " now.", flush=True)
        payload = None
        while time.monotonic() - started < args.duration_seconds:
            time.sleep(15)
            if time.monotonic() - started >= args.duration_seconds:
                break
            if payload is None:
                if marker_state(read_once(args)) != [1, 1]:
                    continue
                payload = {"eventId": str(uuid.uuid4()), "agentRunId": result["agent_run_id"],
                           "observedAt": datetime.now(timezone.utc).isoformat(), "text": MARKER,
                           "direction": "IN", "evidenceSource": "REAL_DESKTOP_OCR"}
                result["state"] = "DETECTED_PENDING_RECEIPT"
                result["event"] = payload
                save_report(args.output, result)
            try:
                receipt = exchange(args.backend_url, token, payload)
            except HTTPError as error:
                if error.code >= 500:
                    continue
                raise TestBlocked("BACKEND_HTTP_" + str(error.code)) from None
            except (URLError, TimeoutError, ConnectionError):
                continue  # Retry the exact same event ID/content; never resend on WeChat.
            if not receipt_matches(receipt, payload):
                raise TestBlocked("BACKEND_RECEIPT_MISMATCH")
            result["state"] = "RECEIVED_BY_BACKEND"
            result["receipt"] = receipt
            break
        if result["state"] != "RECEIVED_BY_BACKEND":
            result["state"] = "STOPPED"
            result["reason"] = "TEST_TIMEOUT_OR_RECEIPT_PENDING"
    except KeyboardInterrupt:
        result.update(state="STOPPED", reason="USER_INTERRUPTED")
    except TestBlocked as error:
        result.update(state="STOPPED", reason=str(error))
    except HTTPError as error:
        result.update(state="STOPPED", reason="BACKEND_HTTP_" + str(error.code))
    except Exception as error:
        result.update(state="STOPPED", error_type=type(error).__name__)
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    save_report(args.output, result)
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only", action="store_true", required=True)
    parser.add_argument("--expected-chat", required=True)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8997")
    parser.add_argument("--token-file", type=Path, default=root.parent / "runtime/probe-token.txt")
    parser.add_argument("--duration-seconds", type=int, default=180)
    parser.add_argument("--layout", type=Path, default=root / "ocr-layout.json")
    parser.add_argument("--output", type=Path, default=root / "runtime/receive-test-latest.json")
    args = parser.parse_args()
    args.message_check = "pipeline"
    try:
        args.backend_url = validate_backend(args.backend_url)
        token = args.token_file.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
            raise ValueError("Invalid local probe token file")
        if not args.expected_chat.strip() or not 60 <= args.duration_seconds <= 600:
            raise ValueError("Expected chat required; duration 60..600 seconds")
    except (ValueError, OSError) as error:
        parser.error(str(error) if isinstance(error, ValueError) else "Probe token file unavailable")
    report = run_test(args, token)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["state"] == "RECEIVED_BY_BACKEND" else 2


if __name__ == "__main__":
    sys.exit(main())
