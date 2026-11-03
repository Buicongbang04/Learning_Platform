"""Hỗ trợ test M08: repo git tạm chép từ project, dependency cho runner act, chạy workflow ngoại tuyến.

Dùng lại `cikit` của module 08 (git trong sandbox, đọc workflow, mô phỏng path filter vì act bỏ qua `paths`).
Dependency Python cho runner được cài một lần vào `~/.cache/mlops-ex/eta-ci-<hash>` (cùng phiên bản với môi trường
gốc của repo), mount chỉ đọc vào container cùng đường dẫn, và repo tạm có symlink `.ci-deps` trỏ tới đó.
"""

import hashlib
import importlib.metadata
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import mlopskit

sys.path.insert(0, str(mlopskit.ROOT / "tracks" / "mlops" / "modules" / "08-cicd-for-ml"))

import cikit

CI_PACKAGES = ["pandas", "numpy", "pyarrow", "scipy", "scikit-learn", "joblib", "pyyaml", "pandera", "mlflow-skinny",
               "sqlalchemy", "alembic", "skops", "pytest"]
IGNORED = ("tests", "data", "models", "mlruns", "reports", "notebooks", "__pycache__", ".pytest_cache", ".ruff_cache",
           ".ci-deps", ".venv", ".dvc", "*.db", "metrics.json", "dist")
WORKFLOWS = ("ci.yml", "ct.yml", "cd.yml")


def requirements() -> list[str]:
    pins = [f"{name}=={importlib.metadata.version(name)}" for name in CI_PACKAGES]
    return pins + [f"ruff=={cikit.RUFF_VERSION}"]


def deps_path() -> Path:
    pins = requirements()
    digest = hashlib.sha256(("\n".join(pins) + sys.version).encode()).hexdigest()[:12]
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "mlops-ex"
    cache = root / f"eta-ci-{digest}"
    if (cache / ".complete").is_file():
        return cache
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("Cần uv để chuẩn bị dependency cho runner act (xem module 08, mục 0)")
    root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="eta-ci-", dir=root))
    result = subprocess.run([uv, "pip", "install", "--quiet", "--target", str(staging), "--python", sys.executable, *pins],
                            capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        shutil.rmtree(staging, ignore_errors=True)
        pytest.skip(f"Không cài được dependency cho runner (cần mạng lần đầu): {result.stderr[-400:]}")
    (staging / ".complete").write_text("\n".join(pins) + "\n", encoding="utf-8")
    try:
        staging.rename(cache)
    except OSError:
        shutil.rmtree(staging, ignore_errors=True)
    return cache


def workflow_path(project: Path, name: str) -> Path:
    path = project / ".github" / "workflows" / name
    if not path.is_file():
        pytest.fail(f"Chưa có tệp .github/workflows/{name}", pytrace=False)
    return path


def check_run_only(project: Path) -> None:
    for name in WORKFLOWS:
        workflow = cikit.load_workflow(workflow_path(project, name))
        for job_name, job in workflow.get("jobs", {}).items():
            assert job.get("runs-on") == "ubuntu-latest", f"{name}/{job_name}: runs-on phải là ubuntu-latest"
            for step in job.get("steps", []):
                assert "uses" not in step, f"{name}/{job_name}: chỉ dùng bước run, không uses (act chạy ngoại tuyến)"


def make_repo(project: Path, root: Path) -> Path:
    for name in WORKFLOWS:
        workflow_path(project, name)
    repo = root / "repo"
    shutil.copytree(project, repo, ignore=shutil.ignore_patterns(*IGNORED), symlinks=False)
    (repo / ".ci-deps").symlink_to(deps_path())
    cikit.git(repo, "init", "-q", "-b", "main")
    (repo / ".git" / "info").mkdir(parents=True, exist_ok=True)
    (repo / ".git" / "info" / "exclude").write_text(".ci-deps\nmlflow/\ndata/\ntrain.json\ndist/\n", encoding="utf-8")
    cikit.commit_all(repo, "init")
    return repo


def run(repo: Path, *args: str, event: str = "push", env: dict[str, str] | None = None,
        timeout: int = 900) -> subprocess.CompletedProcess:
    deps = deps_path()
    flags = [item for key, value in (env or {}).items() for item in ("--env", f"{key}={value}")]
    options = f"--user {os.getuid()}:{os.getgid()} -v {deps}:{deps}:ro"
    return mlopskit.act_run(repo, *args, *flags, event=event, timeout=timeout, container_options=options)


log = cikit.log
load_workflow = cikit.load_workflow
triggers = cikit.triggers
commit_all = cikit.commit_all
