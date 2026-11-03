import hashlib
import os
import subprocess
from pathlib import Path


def git_commit(cwd: Path | None = None) -> str:
    if os.environ.get("GIT_COMMIT"):
        return os.environ["GIT_COMMIT"]
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=cwd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if head.returncode != 0:
        return "unknown"
    return head.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")


def data_version(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(p) for p in paths):
        digest.update(path.name.encode())
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
    return f"sha256:{digest.hexdigest()[:16]}"
