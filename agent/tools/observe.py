"""Phase 0 low-frequency read-only observation of one manually selected chat."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from probe import check


def validate_options(duration, interval):
    if (type(duration) is not int or type(interval) is not int
            or not 30 <= duration <= 14400 or not 30 <= interval <= 300
            or interval > duration):
        raise ValueError("Duration must be 30..14400s; interval 30..300s and <= duration")


def read_once(args):
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="observe-", dir=root / "runtime") as temporary:
        output_path = Path(temporary) / "sample.json"
        command = [sys.executable, "-X", "utf8", str(Path(__file__).with_name("ocr_probe.py")),
                   "--read-only", "--expected-chat", args.expected_chat,
                   "--layout", str(args.layout.resolve()), "--output", str(output_path)]
        if getattr(args, "message_check", None):
            command += ["--message-check", args.message_check]
        child = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
        try:
            child.wait(timeout=55)
        except subprocess.TimeoutExpired:
            return {"checks": {"worker": check("FAIL", reason="OBSERVER_WORKER_TIMEOUT")}}
        finally:
            if child.poll() is None:
                # Includes Ctrl+C: stop only our probe tree, never the existing WeChat process.
                subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                child.wait(timeout=5)
        if not output_path.is_file():
            return {"checks": {"worker": check("FAIL", reason="OBSERVER_WORKER_NO_REPORT")}}
        report = json.loads(output_path.read_text(encoding="utf-8"))
        # A changing pair of snapshots is normal during observation, not a worker failure.
        if child.returncode not in (0, 2):
            return {"checks": {"worker": check("FAIL", reason="OBSERVER_WORKER_EXIT")}}
        return report


def save_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_observation(args):
    validate_options(args.duration_seconds, args.interval_seconds)
    report = {"schema_version": 1, "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "read_only": True, "effective_mode": "OFF", "auto_eligible": False,
              "route": "UNVERIFIED", "state": "RUNNING",
              "requested_duration_seconds": args.duration_seconds,
              "interval_seconds": args.interval_seconds, "observed_span_seconds": 0,
              "max_poll_gap_seconds": 0,
              "checks": {"observation_run": check("RUNNING"),
                         "four_hour_observation": check("UNVERIFIED"),
                         "message_identity_direction_dedup_aggregation": check("UNVERIFIED")},
              "observations": [],
              "scope": "One manually selected title; visible snapshots only, not complete message coverage"}
    started = time.monotonic()
    previous_poll = None
    save_report(args.output, report)
    try:
        while True:
            poll_started = time.monotonic()
            if previous_poll is not None:
                gap = poll_started - previous_poll
                report["max_poll_gap_seconds"] = round(max(report["max_poll_gap_seconds"], gap), 3)
                if gap > args.interval_seconds + 55:
                    report["state"] = "STOPPED"
                    report["checks"]["observation_run"] = check("BLOCKED", reason="OBSERVATION_GAP")
                    break
            previous_poll = poll_started
            sample = read_once(args)
            failures = [item for name, item in sample.get("checks", {}).items()
                        if name != "two_sample_consistency" and item.get("status") in ("FAIL", "BLOCKED")]
            if failures:
                report["state"] = "STOPPED"
                report["checks"]["observation_run"] = failures[0]
                break
            if (sample.get("read_only") is not True or sample.get("effective_mode") != "OFF"
                    or sample.get("checks", {}).get("title_ocr", {}).get("status") != "PASS"
                    or len(sample.get("samples", [])) != 2
                    or not all(frame.get("title_exact_match") is True for frame in sample["samples"])):
                report["state"] = "STOPPED"
                report["checks"]["observation_run"] = check("FAIL", reason="INVALID_SCOPED_SAMPLE")
                break
            span = poll_started - started
            report["observed_span_seconds"] = round(span, 3)
            report["observations"].append({
                "probe_started_at_utc": sample["observed_at_utc"],
                "offset_seconds": round(span, 3),
                "probe_duration_seconds": round(time.monotonic() - poll_started, 3),
                "title_exact_match": True,
                "pair_consistency": sample["checks"].get("two_sample_consistency", {}).get("status"),
                "visible_message_line_counts": [frame["visible_message_line_count"] for frame in sample["samples"]],
                "visible_input_line_counts": [frame["visible_input_line_count"] for frame in sample["samples"]],
            })
            # ponytail: reuse the bounded probe process; no daemon, message event model or automatic recovery.
            if span >= args.duration_seconds:
                report["state"] = "COMPLETED"
                report["checks"]["observation_run"] = check("PASS", scope="Requested read-only polling span only")
                if span >= 14400:
                    report["checks"]["four_hour_observation"] = check(
                        "PASS", scope="Single-title low-frequency OCR polling; message completeness/identity unverified")
                break
            save_report(args.output, report)
            next_poll = min(poll_started + args.interval_seconds, started + args.duration_seconds)
            time.sleep(max(0, next_poll - time.monotonic()))
    except KeyboardInterrupt:
        report["state"] = "STOPPED"
        report["checks"]["observation_run"] = check("BLOCKED", reason="USER_INTERRUPTED")
    except Exception as error:
        report["state"] = "STOPPED"
        report["checks"]["observation_run"] = check("FAIL", error_type=type(error).__name__)
    report["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    save_report(args.output, report)
    return report


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only", action="store_true", required=True)
    parser.add_argument("--expected-chat", required=True)
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--layout", type=Path, default=root / "ocr-layout.json")
    parser.add_argument("--output", type=Path, default=root / "runtime/observation-latest.json")
    args = parser.parse_args()
    try:
        validate_options(args.duration_seconds, args.interval_seconds)
    except ValueError as error:
        parser.error(str(error))
    if not args.expected_chat.strip():
        parser.error("Expected chat cannot be empty")
    (root / "runtime").mkdir(exist_ok=True)
    report = run_observation(args)
    print(json.dumps({key: value for key, value in report.items() if key != "observations"}, indent=2))
    return 0 if report["state"] == "COMPLETED" else 2


if __name__ == "__main__":
    sys.exit(main())
