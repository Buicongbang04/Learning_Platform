import json
import re
import sys
from pathlib import Path

ERRORS = [
    ("not_installed", re.compile(r"nvidia-smi: (command )?not found")),
    ("driver_not_loaded", re.compile(r"couldn't communicate with the NVIDIA driver")),
    ("driver_mismatch", re.compile(r"Driver/library version mismatch")),
    ("nvml_unknown", re.compile(r"Failed to initialize NVML: Unknown Error")),
    ("gpu_lost", re.compile(r"Unable to determine the device handle|GPU is lost")),
    ("no_gpu", re.compile(r"No devices were found")),
]
MEMORY = re.compile(r"^\|[^|]*\|\s*(\d+)MiB\s*/\s*(\d+)MiB\s*\|[^|]*\|$")


def gpus(text: str) -> list[dict]:
    found = []
    lines = text.splitlines()
    for number, line in enumerate(lines):
        if line.startswith("| Processes:") or line.startswith("| MIG devices:"):
            break
        match = MEMORY.match(line)
        if not match:
            continue
        mig = lines[number + 1].rstrip("|").split("|")[-1].strip() if number + 1 < len(lines) else ""
        found.append({"used_mb": int(match.group(1)), "total_mb": int(match.group(2)), "mig": mig == "Enabled"})
    return found


def diagnose(text: str, need_mb: int) -> str:
    for code, pattern in ERRORS:
        if pattern.search(text):
            return code
    devices = gpus(text)
    if not devices:
        return "unknown"
    if any(device["mig"] for device in devices):
        return "mig_enabled"
    if max(device["total_mb"] - device["used_mb"] for device in devices) < need_mb:
        return "gpu_busy"
    return "ok"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Cách dùng: python diagnose_gpu.py <output nvidia-smi> <need_mb>", file=sys.stderr)
        return 2
    text = Path(argv[0]).read_text(encoding="utf-8", errors="replace")
    print(json.dumps({"diagnosis": diagnose(text, int(argv[1]))}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
