"""SBOM CycloneDX cho môi trường serving bằng cyclonedx-py, và các phép kiểm trên SBOM."""

import json
import re
import subprocess
import sys
from pathlib import Path


def generate(source: Path, out: Path, kind: str = "requirements", timeout: int = 300) -> dict:
    if kind not in ("requirements", "environment"):
        raise ValueError(f"kind không hợp lệ: {kind}")
    command = [sys.executable, "-m", "cyclonedx_py", kind, "--sv", "1.6", "--of", "JSON", "-o", str(out), str(source)]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    return json.loads(Path(out).read_text(encoding="utf-8"))


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def packages(sbom: dict) -> dict[str, str | None]:
    return {normalize(c["name"]): c.get("version") for c in sbom.get("components") or []}


def unpinned(sbom: dict) -> list[str]:
    return sorted(name for name, version in packages(sbom).items() if not version)


def diff(old: dict, new: dict) -> dict:
    before, after = packages(old), packages(new)
    return {
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
        "changed": {n: [before[n], after[n]] for n in sorted(set(before) & set(after)) if before[n] != after[n]},
    }


def check(sbom: dict, required: dict[str, str]) -> list[str]:
    found = packages(sbom)
    problems = [f"unpinned:{name}" for name in unpinned(sbom)]
    for name, version in required.items():
        key = normalize(name)
        if key not in found:
            problems.append(f"missing:{key}")
        elif found[key] and found[key] != version:
            problems.append(f"mismatch:{key}")
    return sorted(problems)
