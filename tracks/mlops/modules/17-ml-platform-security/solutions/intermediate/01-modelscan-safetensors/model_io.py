"""Lưu model không kèm code (safetensors) và cổng nhận model: allowlist định dạng theo nội dung + modelscan."""

import json
import struct
from pathlib import Path
from typing import Callable

import numpy as np
from safetensors.numpy import load_file, save_file

ALLOWED = {"safetensors", "json"}
BLOCKING = {"MEDIUM", "HIGH", "CRITICAL"}


def export_linear(model, path: Path) -> None:
    coef = np.asarray(model.coef_, dtype=np.float64).reshape(-1)
    intercept = np.asarray(model.intercept_, dtype=np.float64).reshape(-1)
    save_file({"coef": coef, "intercept": intercept}, str(path),
              metadata={"format": "linear", "n_features": str(coef.size)})


def load_linear(path: Path) -> Callable[[np.ndarray], np.ndarray]:
    tensors = load_file(str(path))
    coef, intercept = tensors["coef"], float(tensors["intercept"][0])

    def predict(X):
        return np.asarray(X, dtype=np.float64) @ coef + intercept

    return predict


def _is_safetensors(data: bytes) -> bool:
    if len(data) < 8:
        return False
    (size,) = struct.unpack("<Q", data[:8])
    if size == 0 or 8 + size > len(data):
        return False
    try:
        header = json.loads(data[8:8 + size].decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False
    return isinstance(header, dict)


def _is_json(data: bytes) -> bool:
    try:
        json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False
    return True


def sniff(path: Path) -> str:
    data = Path(path).read_bytes()
    if _is_safetensors(data):
        return "safetensors"
    if _is_json(data):
        return "json"
    if len(data) >= 2 and data[0] == 0x80 and 2 <= data[1] <= 5:
        return "pickle"
    return "other"


def file_formats(model_dir: Path) -> dict[str, str]:
    model_dir = Path(model_dir)
    formats = {}
    for path in sorted(model_dir.rglob("*")):
        name = path.relative_to(model_dir).as_posix()
        if path.is_symlink():
            formats[name] = "symlink"
        elif path.is_file():
            formats[name] = sniff(path)
    return formats


def read_scan(returncode: int, report: str) -> dict:
    try:
        data = json.loads(report)
    except (TypeError, ValueError):
        data = None
    if returncode not in (0, 1, 3) or not isinstance(data, dict) or data.get("errors"):
        return {"ok": False, "findings": [], "scanned": set()}
    issues = data.get("issues") or []
    if returncode == 1 and not issues:
        return {"ok": False, "findings": [], "scanned": set()}
    findings = {f"scan-issue:{i.get('module')}.{i.get('operator')}" for i in issues if i.get("severity") in BLOCKING}
    scanned = set(((data.get("summary") or {}).get("scanned") or {}).get("scanned_files") or [])
    return {"ok": True, "findings": sorted(findings), "scanned": scanned}


def gate(model_dir: Path, scan, allow_pickle: bool = False) -> dict:
    model_dir = Path(model_dir)
    formats = file_formats(model_dir)
    reasons = [] if formats else ["empty"]
    allowed = ALLOWED | ({"pickle"} if allow_pickle else set())
    reasons += [f"format:{name}" for name, kind in formats.items() if kind not in allowed]
    result = scan(model_dir)
    report = read_scan(result.returncode, result.stdout)
    reasons += report["findings"]
    if not report["ok"]:
        reasons.append("scan-error")
    else:
        reasons += [f"unscanned:{name}" for name, kind in formats.items()
                    if kind == "pickle" and allow_pickle and name not in report["scanned"]]
    return {"allowed": not reasons, "reasons": sorted(reasons)}
