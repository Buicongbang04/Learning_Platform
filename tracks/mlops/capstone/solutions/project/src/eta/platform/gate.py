"""Cổng deploy của nền tảng: allowlist định dạng theo nội dung, modelscan, chữ ký, tag bắt buộc. Không nạp tệp model nào."""

import json
import re
from pathlib import Path

from eta.platform.formats import ALLOWED, file_formats
from eta.platform.signing import verify

TEAMS = ("eta", "pricing", "fraud", "search", "ads")
TAG_RULES = {
    "owner": re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}"),
    "team": re.compile("|".join(TEAMS)),
    "cost_center": re.compile(r"CC-[0-9]{4}"),
}
METADATA = "metadata.json"


def scan_clean(result) -> bool:
    try:
        report = json.loads(result.stdout)
    except (TypeError, ValueError):
        return False
    if not isinstance(report, dict) or report.get("errors") or report.get("issues"):
        return False
    return result.returncode in (0, 3)


def tag_problems(model_dir: Path, formats: dict[str, str]) -> list[str]:
    tags = {}
    if formats.get(METADATA) == "json":
        try:
            data = json.loads((Path(model_dir) / METADATA).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError, RecursionError):
            data = None
        if isinstance(data, dict) and isinstance(data.get("tags"), dict):
            tags = data["tags"]
    return [f"tag:{key}" for key, rule in TAG_RULES.items() if not (isinstance(tags.get(key), str) and rule.fullmatch(tags[key]))]


def deploy_gate(model_dir: Path, signature: Path, public_key: Path, scan) -> dict:
    model_dir = Path(model_dir)
    formats = file_formats(model_dir)
    reasons = [] if formats else ["empty"]
    reasons += [f"format:{name}" for name, kind in formats.items() if kind not in ALLOWED]
    if not verify(model_dir, public_key, signature):
        reasons.append("signature")
    try:
        clean = scan_clean(scan(model_dir))
    except Exception:
        clean = False
    if not clean:
        reasons.append("scan")
    reasons += tag_problems(model_dir, formats)
    return {"allowed": not reasons, "reasons": sorted(reasons)}


def docker_modelscan(model_dir: Path, image: str = "mlops-modelscan:0.8.8", timeout: int = 300):
    import os
    import shutil
    import subprocess
    import tempfile

    target = Path(model_dir).resolve()
    out = Path(tempfile.mkdtemp(prefix="eta-modelscan-"))
    try:
        cmd = ["docker", "run", "--rm", "--pull", "never", "--network", "none", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--read-only", "--tmpfs", "/tmp",
               "--user", f"{os.getuid()}:{os.getgid()}", "-v", f"{target}:/scan/model:ro", "-v", f"{out}:/out", image,
               "modelscan", "-p", "/scan/model", "-r", "json", "-o", "/out/report.json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 125 and "No such image" in result.stderr:
            raise RuntimeError(f"chưa có image {image}: build trước (xem module 17, mục 0)")
        report = out / "report.json"
        stdout = report.read_text(encoding="utf-8") if report.is_file() and not report.is_symlink() else ""
        return subprocess.CompletedProcess(cmd, result.returncode, stdout, result.stdout + result.stderr)
    finally:
        shutil.rmtree(out, ignore_errors=True)
