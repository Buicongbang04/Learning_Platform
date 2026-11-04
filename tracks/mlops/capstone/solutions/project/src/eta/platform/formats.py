"""Nhận diện định dạng tệp model theo nội dung, không theo đuôi, và không bao giờ nạp tệp."""

import json
import struct
from pathlib import Path

ALLOWED = {"safetensors", "json"}


def _is_safetensors(data: bytes) -> bool:
    if len(data) < 8:
        return False
    (size,) = struct.unpack("<Q", data[:8])
    if size == 0 or 8 + size > len(data):
        return False
    try:
        return isinstance(json.loads(data[8:8 + size].decode("utf-8")), dict)
    except (UnicodeDecodeError, ValueError):
        return False


def sniff(path: Path) -> str:
    data = Path(path).read_bytes()
    if _is_safetensors(data):
        return "safetensors"
    try:
        json.loads(data.decode("utf-8"))
        return "json"
    except (UnicodeDecodeError, ValueError):
        pass
    if len(data) >= 2 and data[0] == 0x80 and 2 <= data[1] <= 5:
        return "pickle"
    return "other"


def file_formats(model_dir: Path) -> dict[str, str]:
    model_dir = Path(model_dir)
    found = {}
    for path in sorted(model_dir.rglob("*")):
        name = path.relative_to(model_dir).as_posix()
        if path.is_symlink():
            found[name] = "symlink"
        elif path.is_file():
            found[name] = sniff(path)
    return found
