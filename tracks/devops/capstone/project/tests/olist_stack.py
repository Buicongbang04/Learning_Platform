"""Phần dùng chung của M03 và M04: dựng repo Olist Shop từ sample-app cộng tệp của người học, build hai target api và
worker bằng `DockerLab.build`, chạy trivy với env dựng từ đầu."""

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from testkit import ROOT, DockerLab, Exercise, build_failed_on_network

APP = ROOT / "tracks" / "devops" / "sample-app"
TARGETS = ("api", "worker")
DOCKERFILE = "container/Dockerfile"
COMPOSE = "container/compose.yaml"
LEARNER_PARTS = ("container", "ci", ".github")
FAKE_TOKEN = "ghp_" + "DevopsExCapstoneFakeToken9f3c2a1b7d10e4"[:36]
DOTENV = f"GITHUB_TOKEN={FAKE_TOKEN}\nPOSTGRES_PASSWORD=olist-dev-only\n"
TRIVY_MIN = "0.76"
TRIVY_CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "devops-track" / "trivy"
TRIVY_FLAGS = ["--cache-dir", str(TRIVY_CACHE), "--skip-db-update", "--offline-scan", "--skip-version-check",
               "--disable-telemetry", "--cache-backend", "memory", "--quiet"]
TRIVY_DOWNLOAD = "trivy image --download-db-only --cache-dir ~/.cache/devops-track/trivy"


def shown(path: Path) -> Path:
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def missing(path: Path, doc: str) -> str:
    return f"Chưa có tệp {shown(path)}. Xem tracks/devops/capstone/milestones/{doc}"


def assemble(dest: Path, project_root: Path, *, dotenv: bool = True, extra: dict[str, Path] | None = None) -> Path:
    """Repo giống repo portfolio: mã và test của sample-app ở gốc, cộng `container/`, `ci/`, `.github/` của người học.
    Không chép `.dockerignore` của sample-app: Dockerfile của bạn tự lo phần loại trừ. `.env` chứa một token giả để
    kiểm image không mang bí mật của máy dev."""
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("olist_shop", "tests"):
        shutil.copytree(APP / name, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.db", ".pytest_cache"))
    for name in ("conftest.py", "requirements.txt", "compose.yaml", ".env.example"):
        shutil.copyfile(APP / name, dest / name)
    for part in LEARNER_PARTS:
        if (project_root / part).is_dir():
            shutil.copytree(project_root / part, dest / part, ignore=shutil.ignore_patterns("__pycache__"))
    for rel, source in (extra or {}).items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if dotenv:
        (dest / ".env").write_text(DOTENV, encoding="utf-8")
    return dest


def leak_hashes() -> list[str]:
    files = [APP / "tests" / "test_api.py", APP / "tests" / "test_worker.py"]
    return [hashlib.sha256(DOTENV.encode()).hexdigest()] + [hashlib.sha256(p.read_bytes()).hexdigest() for p in files]


def build_targets(lab: DockerLab, root: Path, build_args: dict[str, str], *, prefix: str = "") -> dict[str, str]:
    """Build `container/Dockerfile` hai lần với `--target api` và `--target worker` từ context là gốc repo."""
    tags = {}
    for target in TARGETS:
        try:
            tags[target] = lab.build(root, f"{prefix}{target}", dockerfile=DOCKERFILE, target=target, build_args=build_args)
        except pytest.fail.Exception as error:
            if build_failed_on_network(str(error)):
                pytest.skip("Build cần mạng ở lần đầu để tải gói pip (BuildKit giữ cache cho lần sau). Kiểm kết nối mạng "
                            "rồi chạy lại.")
            raise
    return tags


def trivy_env() -> dict[str, str]:
    """Env dựng từ đầu cho trivy quét image qua socket Docker: giữ PATH, HOME và biến tìm daemon, bỏ mọi `TRIVY_*`."""
    keep = ("PATH", "HOME", "DOCKER_HOST", "DOCKER_CONTEXT", "XDG_RUNTIME_DIR")
    return {"LANG": "C.UTF-8", **{key: os.environ[key] for key in keep if key in os.environ}}


def require_trivy() -> None:
    Exercise.require_tool("trivy", TRIVY_MIN)


def require_trivy_db(workdir: Path) -> None:
    require_trivy()
    db = TRIVY_CACHE / "db" / "trivy.db"
    if not db.is_file():
        TRIVY_CACHE.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["trivy", "image", "--download-db-only", "--cache-dir", str(TRIVY_CACHE), "--no-progress",
                            "--quiet"], capture_output=True, text=True, timeout=900, env=trivy_env(), cwd=workdir)
        except subprocess.TimeoutExpired:
            pass
    if not db.is_file():
        pytest.skip(f"Chưa có DB lỗ hổng của trivy trong {TRIVY_CACHE} và không tải được (không có mạng?). Tải bằng: "
                    f"{TRIVY_DOWNLOAD}")


def trivy_image(tag: str, workdir: Path, *args: str, config: Path | None = None,
                cwd: Path | None = None) -> tuple[int, dict, str]:
    """`trivy image --image-src docker` với cấu hình `config` (mặc định một tệp rỗng), chạy trong `cwd` (mặc định thư mục
    của `config`); trả mã thoát, report JSON (hay CycloneDX) và stderr."""
    work = workdir / uuid.uuid4().hex[:8]
    work.mkdir(parents=True)
    if config is None:
        config = work / "empty.yaml"
        config.write_text("", encoding="utf-8")
    out = work / "report.json"
    cmd = ["trivy", "image", "--image-src", "docker", *TRIVY_FLAGS, "--config", str(config), *args, "--output", str(out), tag]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=trivy_env(), cwd=cwd or config.parent)
    except subprocess.TimeoutExpired:
        pytest.fail(f"trivy image {tag} chạy quá 600 giây")
    text = out.read_text(encoding="utf-8") if out.is_file() else ""
    return result.returncode, json.loads(text) if text.strip() else {}, result.stderr
