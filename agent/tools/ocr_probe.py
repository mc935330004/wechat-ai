"""Read-only native Windows OCR prototype for an explicitly named test chat."""

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import hmac
import importlib.metadata
import json
import math
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

from probe import check, find_wechat_window

PREPARED_MARKERS = {
    "direction": [("WXIN20261004A", "LEFT", 1), ("WXOUT20261004A", "RIGHT", 1)],
    "direction-b": [("WXIN20261004B", "LEFT", 1), ("WXOUT20261004B", "RIGHT", 1)],
    "duplicates": [("WXDUP20261004", "LEFT", 2)],
    "sequence": [("WXSEQ20261004" + suffix, "LEFT", 1) for suffix in "ABC"],
    "sequence-dup": [("WXDUP20261004" + suffix, "LEFT", 1) for suffix in "ABC"],
}


class GuardFailure(Exception):
    pass


def verify_layout(size, dpi, version, layout):
    if (list(size) != layout["client_size"] or dpi != layout["dpi"]
            or version != layout["calibrated_wechat_version"]):
        raise GuardFailure("LAYOUT_OR_VERSION_CHANGED")
    boxes = []
    for key in ("header_box", "message_box", "input_box"):
        box = layout[key]
        if (len(box) != 4 or any(type(value) is not int for value in box)
                or min(box) < 0 or box[2] == 0 or box[3] == 0
                or box[0] + box[2] > size[0] or box[1] + box[3] > size[1]):
            raise GuardFailure("INVALID_REGION")
        boxes.append(box)
    for index, (x, y, width, height) in enumerate(boxes):
        for other_x, other_y, other_width, other_height in boxes[index + 1:]:
            if (x < other_x + other_width and other_x < x + width
                    and y < other_y + other_height and other_y < y + height):
                raise GuardFailure("OVERLAPPING_REGIONS")
    if layout["scale"] != 2 or not 0 < layout["threshold"] < 255:
        raise GuardFailure("INVALID_PREPROCESSING")


def title_matches(lines, expected):
    # Whitespace is OCR segmentation; never correct characters or use fuzzy matching.
    matches = [line for line in lines if "".join(line["text"].split()) == expected]
    return len(matches) == 1 and matches[0].get("confidence", 1) >= 0.9


def redact_lines(lines, salt):
    return [{"length": len(line["text"]), "box": line["rect"],
             "confidence": line.get("confidence"),
             "text_hmac": hmac.new(salt, line["text"].encode("utf-8"), hashlib.sha256).hexdigest(),
             "direction": "UNVERIFIED"} for line in lines]


def assess_prepared_messages(lines, layout, scenario):
    """Check manually labelled public markers, not arbitrary customer messages."""
    markers = PREPARED_MARKERS[scenario]
    width, height = (value * layout["scale"] for value in layout["message_box"][2:])
    evidence = []
    valid = True
    all_boxes = []
    for index, (marker, expected_side, count) in enumerate(markers):
        matches = [line for line in lines if "".join(line["text"].split()) == marker]
        positions = []
        for line in matches:
            x, y, w, h = line["rect"]
            if (not all(math.isfinite(value) for value in (x, y, w, h))
                    or x < 0 or y < 0 or w <= 0 or h <= 0
                    or x + w > width or y + h > height):
                raise GuardFailure("INVALID_OCR_BOX")
            # ponytail: geometry only validates these labelled markers; no general IN/OUT detector.
            center = (x + w / 2) / width
            side = "LEFT" if center < 0.4 else "RIGHT" if center > 0.6 else "UNKNOWN"
            valid = valid and side == expected_side and line.get("confidence", 0) >= 0.9
            positions.append({"box": line["rect"], "side": side,
                              "confidence": line.get("confidence")})
            all_boxes.append(line["rect"])
        valid = valid and len(matches) == count
        evidence.append({"marker_index": index, "expected_count": count,
                         "observed_count": len(matches), "expected_side": expected_side,
                         "positions": positions})
    # Separate repeated bubbles must occupy distinct vertical rows, not duplicate OCR detections.
    ordered = sorted(all_boxes, key=lambda box: box[1])
    separated = all(first[1] + first[3] < second[1]
                    for first, second in zip(ordered, ordered[1:]))
    if scenario in ("sequence", "sequence-dup") and all(len(item["positions"]) == 1 for item in evidence):
        centers = [item["positions"][0]["box"][1] for item in evidence]
        valid = valid and centers == sorted(centers)
    return check("PASS" if valid and separated else "FAIL", scenario=scenario,
                 markers=evidence, distinct_rows=separated,
                 scope="Visible prepared markers only; no event deduplication or aggregation verified")


def ensure_unlocked():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                               wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    desktop = user32.OpenInputDesktop(0, False, 1)
    if not desktop:
        raise GuardFailure("DESKTOP_LOCKED_OR_UNAVAILABLE")
    try:
        name = ctypes.create_unicode_buffer(256)
        required = wintypes.DWORD()
        if (not user32.GetUserObjectInformationW(desktop, 2, name, ctypes.sizeof(name),
                                                 ctypes.byref(required)) or name.value != "Default"):
            raise GuardFailure("DESKTOP_LOCKED_OR_UNAVAILABLE")
    finally:
        user32.CloseDesktop(desktop)


def capture(handle, layout):
    import win32api
    import win32gui
    import win32process
    import win32ui
    import psutil
    from PIL import Image
    ensure_unlocked()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    user32.GetDpiForWindow.restype = wintypes.UINT
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user32.PrintWindow.restype = wintypes.BOOL
    size = win32gui.GetClientRect(handle)[2:]
    process_id = win32process.GetWindowThreadProcessId(handle)[1]
    process = psutil.Process(process_id)
    if process.name().lower() not in {"weixin.exe", "wechat.exe"}:
        raise GuardFailure("WINDOW_PROCESS_CHANGED")
    info = win32api.GetFileVersionInfo(process.exe(), "\\")
    version = ".".join(str(value) for value in (
        info["FileVersionMS"] >> 16, info["FileVersionMS"] & 65535,
        info["FileVersionLS"] >> 16, info["FileVersionLS"] & 65535))
    dpi = user32.GetDpiForWindow(handle)
    verify_layout(size, dpi, version, layout)
    if win32gui.IsIconic(handle):
        raise GuardFailure("WINDOW_MINIMIZED")
    dc = win32gui.GetDC(handle)
    source = win32ui.CreateDCFromHandle(dc)
    target = source.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(source, *size)
    previous = target.SelectObject(bitmap)
    try:
        if not user32.PrintWindow(handle, target.GetSafeHdc(), 1):
            raise GuardFailure("WINDOW_CAPTURE_FAILED")
        image = Image.frombuffer("RGB", size, bitmap.GetBitmapBits(True), "raw", "BGRX", 0, 1)
        ensure_unlocked()
        if (win32gui.GetClientRect(handle)[2:] != size or win32gui.IsIconic(handle)
                or win32process.GetWindowThreadProcessId(handle)[1] != process_id):
            raise GuardFailure("WINDOW_CHANGED_DURING_CAPTURE")
        return image
    finally:
        target.SelectObject(previous)
        win32gui.DeleteObject(bitmap.GetHandle())
        target.DeleteDC()
        # source wraps the borrowed GetDC handle; ReleaseDC owns its cleanup.
        win32gui.ReleaseDC(handle, dc)


def create_local_engine():
    import rapidocr
    from rapidocr import RapidOCR
    lock = json.loads((Path(__file__).resolve().parents[1] / "dependency-lock.json").read_text(encoding="utf-8"))["ocr_engine"]
    if (importlib.metadata.version("rapidocr") != lock["version"]
            or importlib.metadata.version("onnxruntime") != lock["onnxruntime"]):
        raise GuardFailure("OCR_VERSION_CHANGED")
    models = Path(rapidocr.__file__).parent / "models"
    for model in lock["models"]:
        path = models / model["name"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != model["sha256"]:
            raise GuardFailure("OCR_MODEL_HASH_MISMATCH")
    return RapidOCR(params={
        "Global.log_level": "error",
        "Det.model_path": str(models / "PP-OCRv6_det_small.onnx"),
        "Rec.model_path": str(models / "PP-OCRv6_rec_small.onnx"),
        "Cls.model_path": str(models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx"),
        "Det.limit_type": "max",
        "EngineConfig.onnxruntime.intra_op_num_threads": 2,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    })


def recognize(image, box, layout, work_dir, name, engine=None):
    from PIL import Image, ImageOps
    x, y, width, height = box
    region = image.crop((x, y, x + width, y + height))
    # ponytail: only this light-theme calibration is verified; do not guess new layouts.
    region = region.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    if engine is not None:
        import numpy as np
        result = engine(np.array(region.convert("RGB"))[:, :, ::-1])
        if result.txts is None:
            return []
        return [{"text": text, "confidence": float(score),
                 "rect": [float(box[:, 0].min()), float(box[:, 1].min()),
                          float(box[:, 0].max() - box[:, 0].min()),
                          float(box[:, 1].max() - box[:, 1].min())]}
                for text, score, box in zip(result.txts, result.scores, result.boxes)]
    region = ImageOps.grayscale(region)
    region = region.point(lambda value: 0 if value < layout["threshold"] else 255).convert("RGB")
    path = work_dir / (name + ".png")
    region.save(path)
    powershell = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
    completed = subprocess.run([str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                str(Path(__file__).with_name("windows_ocr.ps1")), "-ImagePath", str(path),
                                "-LanguageTag", layout["language"]], capture_output=True,
                               text=True, encoding="utf-8", timeout=20)
    result = json.loads(completed.stdout)
    if completed.returncode or not result.get("ok"):
        raise GuardFailure("NATIVE_OCR_FAILED")
    path.unlink()
    return result["lines"]


def read_frame(image, layout, expected_chat, expected_input, salt, work_dir, engine=None,
               message_check=None):
    header = recognize(image, layout["header_box"], layout, work_dir, "header", engine)
    if not title_matches(header, expected_chat):
        raise GuardFailure("OCR_TITLE_MISMATCH")
    # The message/input images come from the same frame as the verified title.
    messages = recognize(image, layout["message_box"], layout, work_dir, "messages", engine)
    inputs = recognize(image, layout["input_box"], layout, work_dir, "input", engine)
    sample = {
        "title_exact_match": True,
        "visible_message_line_count": len(messages),
        "visible_input_line_count": len(inputs),
        "expected_input_matched": title_matches(inputs, expected_input) if expected_input else None,
        "message_lines": redact_lines(messages, salt),
        "input_lines": redact_lines(inputs, salt),
        "note": "OCR lines are not message events or full input values; identity/direction are unverified.",
    }
    if message_check:
        sample["prepared_messages"] = assess_prepared_messages(messages, layout, message_check)
        sample["marker_diagnostics"] = [
            {"marker_index": index, "exact_in_input": title_matches(inputs, marker),
             "embedded_in_message_line": any(marker != "".join(line["text"].split())
                                             and marker in "".join(line["text"].split())
                                             for line in messages)}
            for index, (marker, _, _) in enumerate(PREPARED_MARKERS[message_check])]
    return sample


def run_probe(args, layout):
    report = {"schema_version": 1, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "effective_mode": "OFF", "read_only": True, "auto_eligible": False,
              "route": "UNVERIFIED", "engine": args.engine, "checks": {}, "samples": []}
    checks = report["checks"]
    for name in ("contact_identity", "message_direction", "input_empty", "live_listener",
                 "voice_transcription", "send_receipt", "four_hour_observation"):
        checks[name] = check("UNVERIFIED")
    try:
        if sys.platform != "win32":
            raise GuardFailure("WINDOWS_REQUIRED")
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SetProcessDpiAwarenessContext.argtypes = [wintypes.HANDLE]
        user32.SetProcessDpiAwarenessContext(wintypes.HANDLE(-4))
        ensure_unlocked()
        handle = find_wechat_window()
        engine = create_local_engine() if args.engine == "rapidocr" else None
        salt = secrets.token_bytes(32)
        for _ in range(2):
            if find_wechat_window() != handle:
                raise GuardFailure("MAIN_WINDOW_CHANGED")
            sample = read_frame(capture(handle, layout), layout, args.expected_chat,
                                args.expected_input, salt, Path(args.work_dir), engine,
                                args.message_check)
            report["samples"].append(sample)
            time.sleep(0.3)
        checks["title_ocr"] = check("PASS", samples=2)
        checks["visible_text_ocr"] = check("PASS", note="OCR completed; correctness not implied")
        checks["two_sample_consistency"] = check("PASS" if all(
            report["samples"][0][key] == report["samples"][1][key]
            for key in ("message_lines", "input_lines")) else "FAIL")
        if args.expected_input:
            checks["input_marker"] = check("PASS" if all(sample["expected_input_matched"]
                                                      for sample in report["samples"]) else "FAIL")
        if args.message_check:
            checks["prepared_" + args.message_check] = check(
                "PASS" if all(sample["prepared_messages"]["status"] == "PASS"
                              for sample in report["samples"]) else "FAIL",
                scope="Two visible snapshots of manually labelled test markers only")
    except (GuardFailure, ValueError) as error:
        report["samples"] = []
        checks["guard"] = check("BLOCKED", reason=str(error) if isinstance(error, GuardFailure)
                                or str(error) in {"NO_UNIQUE_VISIBLE_MAIN_WINDOW", "WINDOW_MINIMIZED"}
                                else "INVALID_OCR_RESPONSE")
    except Exception as error:
        report["samples"] = []
        checks["probe"] = check("FAIL", error_type=type(error).__name__)
    return report


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only", action="store_true", required=True)
    parser.add_argument("--expected-chat", required=True)
    parser.add_argument("--expected-input", help="Optional known draft marker; the tool never types it")
    parser.add_argument("--message-check", choices=tuple(PREPARED_MARKERS),
                        help="Check manually prepared public test markers, never send them")
    parser.add_argument("--engine", choices=("rapidocr", "windows"), default="rapidocr")
    parser.add_argument("--layout", type=Path, default=root / "ocr-layout.json")
    parser.add_argument("--output", type=Path, default=root / "runtime/ocr-probe-latest.json")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--work-dir", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.expected_chat.strip():
        parser.error("Expected chat cannot be empty")
    if args.message_check and args.engine != "rapidocr":
        parser.error("Prepared message checks require RapidOCR confidence values")
    if args.worker:
        print(json.dumps(run_probe(args, json.loads(args.layout.read_text(encoding="utf-8"))), ensure_ascii=True))
        return 0
    runtime = (root / "runtime").resolve()
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ocr-", dir=runtime) as temporary:
        work_dir = Path(temporary).resolve()
        if work_dir.parent != runtime:
            raise RuntimeError("Unexpected temporary directory")
        command = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--read-only", "--worker",
                   "--expected-chat", args.expected_chat, "--layout", str(args.layout.resolve()),
                   "--engine", args.engine, "--work-dir", str(work_dir)]
        if args.expected_input:
            command += ["--expected-input", args.expected_input]
        if args.message_check:
            command += ["--message-check", args.message_check]
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, encoding="utf-8")
        try:
            output, _ = child.communicate(timeout=45)
            report = json.loads(output) if child.returncode == 0 else None
        except subprocess.TimeoutExpired:
            # Only our worker tree is terminated; Weixin was not spawned by this process.
            subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            child.communicate()
            report = None
        except ValueError:
            report = None
    if report is None:
        report = {"read_only": True, "effective_mode": "OFF", "auto_eligible": False,
                  "route": "UNVERIFIED", "checks": {"worker": check("FAIL", reason="WORKER_FAILED_OR_TIMEOUT")}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 2 if any(item["status"] in {"FAIL", "BLOCKED"} for item in report["checks"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
