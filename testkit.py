"""Tiện ích dùng chung cho test của mọi bài tập.

Mỗi bài tập có `starter/` (bạn sửa) và `tests/`. Lời giải mẫu nằm ở thư mục `solutions/`
song song với `exercises/`, cùng tên tệp với `starter/`.

    uv run pytest <thư mục bài tập> -q              # kiểm tra code của bạn trong starter/
    SOLUTION=1 uv run pytest <thư mục bài tập> -q   # kiểm tra lời giải mẫu

Trong test:

    from testkit import Exercise
    ex = Exercise(__file__)
    transform = ex.module("transform.py")   # import starter/transform.py (hoặc lời giải)
    analysis = ex.notebook("analysis.ipynb") # chạy code cell (trừ cell tag `explore`), dùng như module
    sql = ex.read("query.sql")              # đọc tệp văn bản
    ex.require_service("postgres")          # skip nếu dịch vụ Docker chưa chạy
    wb = ex.workbook("report.xlsx")         # bài Excel: wb.formula("Sheet", "B2"), wb.value("Sheet", "B2")
    ex.require_tool("shellcheck", "0.10")   # bài DevOps: skip nếu thiếu công cụ hoặc phiên bản cũ
    ex.require_cluster()                    # bài DevOps: skip nếu chưa có cluster kind devops-lab
    ex.require_image("nginx:1.30.6-alpine") # bài DevOps: skip nếu image Docker chưa pull
    with DockerLab() as lab: lab.start("web", "nginx:1.30.6-alpine", ports=[80])  # dựng mọi thứ trong `with`
    tag = lab.build(ctx, "api"); project = lab.compose(ctx / "compose.yaml"); project.port("api", 8000)  # trong `with`
    run_sandboxed(cmd, writable=[tmp_path], cwd=tmp_path, env={...})  # bài DevOps: chạy script trong bwrap
    repo = GitRepo(tmp_path / "repo", tmp_path / "home", writable=[tmp_path]); repo.out("log"); repo.taint()  # bài git
    result = act_run(project_dir, job="build"); act_job_results(result) == {"build": True}  # bài CI: workflow chạy bằng act
    registry = ex.require_registry(); ref = lab.push(tag, "api")  # registry local, close() xoá manifest đã push
    with TofuLab(ex.path("infra")) as lab: lab.init(); lab.apply(); lab.output("bucket")  # bài IaC: tofu trong sandbox, LocalStack riêng, close() destroy
"""

from __future__ import annotations

import importlib.util
import linecache
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parent


def _load_env_file(path: Path) -> None:
    """Đọc setup/.env (cổng đã đổi khi trùng dự án khác). Biến môi trường thật vẫn được ưu tiên."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(ROOT / "setup" / ".env")

# Cổng mặc định khớp setup/docker-compose.yml. Ghi đè bằng biến môi trường nếu cần.
SERVICES = {
    "postgres": ("POSTGRES_HOST", "localhost", "POSTGRES_PORT", 5432),
    "mongo": ("MONGO_HOST", "localhost", "MONGO_PORT", 27017),
    "redis": ("REDIS_HOST", "localhost", "REDIS_PORT", 6379),
    "cassandra": ("CASSANDRA_HOST", "localhost", "CASSANDRA_PORT", 9042),
    "neo4j": ("NEO4J_HOST", "localhost", "NEO4J_PORT", 7687),
    "minio": ("MINIO_HOST", "localhost", "MINIO_PORT", 9000),
    "kafka": ("KAFKA_HOST", "localhost", "KAFKA_PORT", 9094),
    "metabase": ("METABASE_HOST", "localhost", "METABASE_PORT", 3000),
    "superset": ("SUPERSET_HOST", "localhost", "SUPERSET_PORT", 8088),
    "airflow": ("AIRFLOW_HOST", "localhost", "AIRFLOW_PORT", 8080),
    "localstack": ("LOCALSTACK_HOST", "localhost", "LOCALSTACK_PORT", 4566),
    "mailpit": ("MAILPIT_HOST", "localhost", "MAILPIT_SMTP_PORT", 11025),
    "registry": ("REGISTRY_HOST", "localhost", "DEVOPS_REGISTRY_PORT", 15000),
    "localstack-devops": ("LOCALSTACK_DEVOPS_HOST", "localhost", "LOCALSTACK_DEVOPS_PORT", 14566),
}

def _port(name: str) -> int:
    return int(os.environ.get(SERVICES[name][2], SERVICES[name][3]))


POSTGRES_DSN = os.environ.get("POSTGRES_DSN", f"postgresql://de:de@localhost:{_port('postgres')}/de")
MONGO_URI = os.environ.get("MONGO_URI", f"mongodb://localhost:{_port('mongo')}")
REDIS_URL = os.environ.get("REDIS_URL", f"redis://localhost:{_port('redis')}/0")
NEO4J_URI = os.environ.get("NEO4J_URI", f"bolt://localhost:{_port('neo4j')}")
NEO4J_AUTH = ("neo4j", os.environ.get("NEO4J_PASSWORD", "password123"))
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", f"http://localhost:{_port('minio')}")
MINIO_AUTH = ("minioadmin", "minioadmin")
LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", f"http://localhost:{_port('localstack')}")
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9094")


def use_solution() -> bool:
    return os.environ.get("SOLUTION") == "1"


def service_up(name: str, timeout: float = 0.5) -> bool:
    host_env, host_default, port_env, port_default = SERVICES[name]
    host = os.environ.get(host_env, host_default)
    port = int(os.environ.get(port_env, port_default))
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


TOOL_VERSION_ARGS = {
    "docker": ["--version"],
    "nginx": ["-v"],
    "shellcheck": ["--version"],
    "kubectl": ["version", "--client"],
    "kind": ["version"],
    "helm": ["version", "--short"],
    "tofu": ["version"],
    "openssl": ["version"],
    "dig": ["-v"],
    "ssh": ["-V"],
}

_VERSION = re.compile(r"\d+(?:\.\d+)+")


def parse_version(text: str) -> tuple[int, ...] | None:
    match = _VERSION.search(text)
    if not match:
        return None
    return tuple(int(part) for part in match.group().split("."))


def version_at_least(have: tuple[int, ...], need: tuple[int, ...]) -> bool:
    """So phiên bản sau khi đệm số 0: (1, 27) bằng (1, 27, 0)."""
    width = max(len(have), len(need))
    return have + (0,) * (width - len(have)) >= need + (0,) * (width - len(need))


def _run_tool(args: list[str]) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None


def tool_version(name: str) -> tuple[int, ...] | None:
    if not shutil.which(name):
        return None
    result = _run_tool([name, *TOOL_VERSION_ARGS.get(name, ["--version"])])
    if result is None:
        return None
    return parse_version(f"{result.stdout}\n{result.stderr}")


def docker_ready() -> bool:
    result = _run_tool(["docker", "info"])
    return result is not None and result.returncode == 0


def docker_cpu_args() -> list[str]:
    cpuset = os.environ.get("DEVOPS_CPUSET", "")
    if cpuset == "none":
        return []
    if cpuset:
        return ["--cpuset-cpus", cpuset]
    if (os.cpu_count() or 0) >= 36:
        return ["--cpuset-cpus", "12-35"]
    return []


DOCKER_PREFIX = "devops-ex-"
DOCKER_LABEL = "devops-ex=1"
DOCKER_MEMORY = "256m"
DOCKER_PIDS_LIMIT = 256
DOCKER_LOG_LINES = 40
DOCKER_LOG_CHARS = 4000
DOCKER_LAB_LABEL = "devops-ex.lab"
DOCKER_BUILD_MEMORY = "1g"
COMPOSE_MIN_VERSION = (2, 24, 4)
_PORT_TAKEN = ("port is already allocated", "address already in use")
_IMAGE_ALIAS = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,62}$")
_DOCKER_ENV_KEEP = ("PATH", "HOME", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CERT_PATH", "DOCKER_TLS_VERIFY", "XDG_RUNTIME_DIR")
_COMPOSE_TOP_KEYS = {"services", "volumes", "networks", "name"}
_COMPOSE_SERVICE_KEYS = {
    "image", "build", "command", "entrypoint", "environment", "env_file", "ports", "expose", "depends_on", "healthcheck",
    "volumes", "working_dir", "user", "labels", "restart", "stop_signal", "stop_grace_period", "tmpfs", "read_only", "init",
    "networks", "cap_drop", "profiles", "hostname", "deploy", "logging", "ulimits", "cpuset", "mem_limit", "pids_limit",
    "memswap_limit", "container_name", "pull_policy",
}
_COMPOSE_GENERIC = "không có trong danh sách khoá được phép của bài tập; xem docstring `DockerLab.compose`"
_HOST_NAMESPACE = "bỏ cách ly namespace hay cgroup với máy host hoặc container khác"
_HOST_DEVICE = "cho container truy cập thiết bị của máy host, ví dụ đọc ghi thẳng ổ đĩa"
_COMPOSE_REASONS = {
    "privileged": "cho container gần như toàn quyền trên máy host",
    "cap_add": "thêm capability cho container, có thể thành quyền quản trị máy host",
    "security_opt": "đổi seccomp, AppArmor hay no-new-privileges; testkit tự đặt no-new-privileges",
    "devices": _HOST_DEVICE,
    "device_cgroup_rules": _HOST_DEVICE,
    "gpus": _HOST_DEVICE,
    "runtime": "đổi runtime của container, có thể bỏ lớp cách ly",
    "network_mode": _HOST_NAMESPACE,
    "pid": _HOST_NAMESPACE,
    "ipc": _HOST_NAMESPACE,
    "uts": _HOST_NAMESPACE,
    "userns_mode": _HOST_NAMESPACE,
    "cgroup": _HOST_NAMESPACE,
    "cgroup_parent": _HOST_NAMESPACE,
    "volumes_from": "lấy volume của container khác",
    "sysctls": "đổi tham số kernel của container",
    "extra_hosts": "đổi phân giải tên của container",
    "configs": "đọc tệp hay biến môi trường của máy host",
    "secrets": "đọc tệp hay biến môi trường của máy host",
    "include": "kéo thêm tệp compose khác",
}
_BUILD_KEYS = {"context", "dockerfile", "args", "target"}
_COPY_IGNORE = (".git", ".venv", "node_modules", "__pycache__", ".pytest_cache")
_BUILDER: str | None = None


_NETWORK_ERRORS = re.compile(
    r"Temporary failure in name resolution|Temporary failure resolving|Could not resolve|Name or service not known|"
    r"Failed to establish a new connection|Network is unreachable|NewConnectionError|Connection timed out|Read timed out"
)
_FETCH_PROGRESS = re.compile(r"\b(?:Collecting|Downloading|Using cached|Successfully|Installing collected|Get:\d+|Fetched)\b")


def build_failed_on_network(output: str) -> bool:
    """True khi bước build bị lỗi chết vì mạng: xét output của đúng bước lỗi (`#N ERROR:` của BuildKit), có dòng lỗi mạng và
    sau dòng lỗi mạng cuối cùng không còn dấu hiệu tải thành công. Retry đã hồi phục rồi mới lỗi thật (gói không tồn tại,
    lỗi ở bước khác) thì False, để test fail thay vì skip."""
    lines = output.splitlines()
    failed = re.findall(r"^#(\d+) ERROR:", output, re.M)
    if failed:
        lines = [line for line in lines if line.startswith(f"#{failed[-1]} ")]
    hits = [i for i, line in enumerate(lines) if _NETWORK_ERRORS.search(line)]
    return bool(hits) and not any(_FETCH_PROGRESS.search(line) for line in lines[hits[-1] + 1:])


_ACT_NETWORK_ERRORS = re.compile(
    _NETWORK_ERRORS.pattern + r"|ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ETIMEDOUT|UND_ERR_CONNECT_TIMEOUT|dns error|"
    r"error sending request|Failed to fetch|Could not connect|fetch failed"
)
_ACT_FETCH_PROGRESS = re.compile(_FETCH_PROGRESS.pattern + r"|\b(?:Downloaded|Prepared|Installed) ")
_ACT_STEP_START = re.compile(r"^\[([^\]]+)\]\s+⭐\s+Run (?:Pre |Main |Post )?(.+?)\s*$")
_ACT_STEP_FAILED = re.compile(r"^\[([^\]]+)\]\s+❌\s+Failure - (?:Pre |Main |Post )?(.+?) \[[^\]]*\]\s*$")


def act_failed_on_network(result: subprocess.CompletedProcess, step_names) -> bool:
    """True khi trong output của `act_run` có một bước tên thuộc `step_names` bị fail và chính output của bước đó (các dòng
    giữa `⭐ Run ... <bước>` và `❌ Failure - ... <bước>` của cùng job) có lỗi mạng, sau lỗi mạng cuối không còn dấu hiệu tải
    thành công. Lỗi mạng ở bước khác, hay bước cài đặt fail vì lý do khác, đều False: test fail thay vì skip."""
    wanted = set(step_names)
    current: dict[str, tuple[str, list[str]]] = {}
    for line in f"{result.stdout or ''}\n{result.stderr or ''}".splitlines():
        start = _ACT_STEP_START.match(line)
        if start:
            current[start.group(1)] = (start.group(2), [])
            continue
        failed = _ACT_STEP_FAILED.match(line)
        if failed:
            job, step = failed.groups()
            name, lines = current.pop(job, ("", []))
            if step in wanted and name == step:
                hits = [i for i, text in enumerate(lines) if _ACT_NETWORK_ERRORS.search(text)]
                if hits and not any(_ACT_FETCH_PROGRESS.search(text) for text in lines[hits[-1] + 1:]):
                    return True
            continue
        job = re.match(r"^\[([^\]]+)\]", line)
        if job and job.group(1) in current:
            current[job.group(1)][1].append(line)
    return False


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _docker(*args: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def docker_leftovers(lab_id: str) -> list[str]:
    """Container, network, volume (theo tiền tố `devops-ex-<id>`) và image (theo nhãn `devops-ex.lab=<id>`) còn sót của
    một DockerLab; rỗng nghĩa là đã dọn sạch."""
    prefix = f"{DOCKER_PREFIX}{lab_id}"
    containers = _docker("ps", "-a", "--filter", f"name={prefix}", "--format", "{{.Names}}").stdout.split()
    networks = _docker("network", "ls", "--filter", f"name={prefix}", "--format", "{{.Name}}").stdout.split()
    volumes = _docker("volume", "ls", "--filter", f"name={prefix}", "--format", "{{.Name}}").stdout.split()
    images = _docker("images", "-q", "--filter", f"label={DOCKER_LAB_LABEL}={lab_id}").stdout.split()
    return containers + networks + volumes + sorted(set(images))


REGISTRY_MANIFEST_TYPES = (
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
)


def registry_address() -> str:
    host_env, host_default, _, _ = SERVICES["registry"]
    return f"{os.environ.get(host_env, host_default)}:{_port('registry')}"


def _registry_request(method: str, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str]]:
    """Gọi API HTTP của registry local, bỏ qua proxy của máy. Trả (mã HTTP, header viết thường); 0 khi không kết nối được."""
    import urllib.error
    import urllib.request

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(f"http://{registry_address()}{path}", method=method, headers=headers or {})
    try:
        with opener.open(request, timeout=10) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}
    except (OSError, ValueError):
        return 0, {}


def _docker_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Env dựng từ đầu cho `docker buildx build` và `docker compose`: chỉ giữ biến để tìm daemon, không mang biến cloud,
    `BUILDX_*` hay `COMPOSE_*` của người học vào build hay vào phép thay biến của compose."""
    env = {key: os.environ[key] for key in _DOCKER_ENV_KEEP if key in os.environ}
    env.update({"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"})
    env.update(extra or {})
    return env


def _output_tail(result: subprocess.CompletedProcess) -> str:
    lines = f"{result.stdout or ''}{result.stderr or ''}".rstrip().splitlines()[-DOCKER_LOG_LINES:]
    return "\n".join(lines)[-DOCKER_LOG_CHARS:] or "(không có output)"


def _build_builder() -> str:
    """Builder driver `docker` của context hiện tại. Đã kiểm (buildx 0.38.1, BuildKit 0.34.0): driver này áp
    `--cpuset-cpus` và `--memory` lên cgroup của bước RUN, nên không cần builder `docker-container` riêng."""
    global _BUILDER
    if _BUILDER:
        return _BUILDER
    name = _docker("context", "show").stdout.strip() or "default"
    info = _docker("buildx", "inspect", name)
    driver = re.search(r"^Driver:\s*(\S+)", info.stdout or "", re.M)
    if info.returncode != 0 or not driver:
        pytest.skip("Cần docker buildx (BuildKit) để build image. Xem setup/DEVOPS-TOOLS.md")
    if driver.group(1) != "docker":
        pytest.skip(f"Builder {name} dùng driver {driver.group(1)}, không phải docker; test cần builder driver docker để "
                    "giới hạn CPU và RAM của bước build có hiệu lực")
    _BUILDER = name
    return name


def _compose_version_ok() -> str | None:
    result = _run_tool(["docker", "compose", "version", "--short"])
    have = parse_version(result.stdout) if result is not None and result.returncode == 0 else None
    if have is None:
        return "Chưa có docker compose v2. Xem setup/DEVOPS-TOOLS.md"
    if not version_at_least(have, COMPOSE_MIN_VERSION):
        need = ".".join(map(str, COMPOSE_MIN_VERSION))
        return f"docker compose {'.'.join(map(str, have))} cũ hơn {need} (cần `!reset`/`!override` trong tệp override)"
    return None


def _inside(path: str | Path, root: Path) -> bool:
    return Path(path).resolve().is_relative_to(root.resolve())


def _compose_problems(config: dict, root: Path, lab_id: str) -> list[str]:
    """Lý do từ chối một project compose, xét trên output của `docker compose config --no-env-resolution`.

    Danh sách cho phép (allowlist), khoá khác đều bị từ chối kèm lý do:
    - Service: image, build (context trong `root`; dockerfile; args; target), command, entrypoint, environment, env_file
      (trong `root`), ports, expose, depends_on, healthcheck, volumes (bind trong `root`, volume có tên của project,
      tmpfs), working_dir, user, labels, restart, stop_signal, stop_grace_period, tmpfs, read_only, init, networks,
      cap_drop, profiles, hostname, deploy (chỉ resources.limits cpus/memory/pids và replicas), logging (driver
      json-file/local), ulimits (chỉ nofile); cộng các khoá testkit ghi đè: cpuset, mem_limit, pids_limit,
      memswap_limit, container_name, pull_policy.
    - Cấp trên cùng: services, volumes, networks, name, khoá mở rộng `x-*`.
    - Volume/network cấp trên cùng: tên phải bắt đầu bằng `devops-ex-<lab id>`, driver mặc định (local/bridge), không
      external, không driver_opts.
    """
    problems = []
    prefix = f"{DOCKER_PREFIX}{lab_id}"
    for key in config:
        if key not in _COMPOSE_TOP_KEYS and not key.startswith("x-"):
            problems.append(f"khoá cấp trên cùng `{key}` không được hỗ trợ ({_COMPOSE_REASONS.get(key, _COMPOSE_GENERIC)})")
    for name, svc in (config.get("services") or {}).items():
        where = f"service {name}"
        for key, value in svc.items():
            if key in _COMPOSE_SERVICE_KEYS or value in (None, "", [], {}, False):
                continue
            shown = f"`{key}: {value}`" if isinstance(value, (str, bool, int)) else f"`{key}`"
            problems.append(f"{where}: {shown} bị từ chối ({_COMPOSE_REASONS.get(key, _COMPOSE_GENERIC)})")
        for volume in svc.get("volumes") or []:
            kind, source = volume.get("type"), volume.get("source", "")
            if kind == "bind" and not _inside(source, root):
                hint = " (socket Docker = quyền root trên máy host)" if str(source).endswith("docker.sock") else ""
                problems.append(f"{where}: bind mount {source}{hint} nằm ngoài thư mục {root}")
            elif kind not in ("bind", "volume", "tmpfs"):
                problems.append(f"{where}: volume kiểu {kind} không được hỗ trợ")
        for env_file in svc.get("env_file") or []:
            path = env_file.get("path") if isinstance(env_file, dict) else env_file
            if path and not _inside(path, root):
                problems.append(f"{where}: env_file {path} nằm ngoài thư mục {root}")
        build = svc.get("build")
        if build:
            context = Path(build.get("context", root))
            if not _inside(context, root):
                problems.append(f"{where}: build context {context} nằm ngoài thư mục {root}")
            elif not _inside(context / build.get("dockerfile", "Dockerfile"), context):
                problems.append(f"{where}: build dockerfile {build.get('dockerfile')} nằm ngoài build context")
            extra = sorted(k for k, v in build.items() if k not in _BUILD_KEYS and v not in (None, "", [], {}))
            if extra:
                problems.append(f"{where}: build chỉ hỗ trợ {', '.join(sorted(_BUILD_KEYS))}, không hỗ trợ {', '.join(extra)}")
        deploy = {k: v for k, v in (svc.get("deploy") or {}).items() if v not in (None, {}, [])}
        resources = {k: v for k, v in (deploy.get("resources") or {}).items() if v not in (None, {}, [])}
        limits = set((resources.get("limits") or {})) - {"cpus", "memory", "pids"}
        extra = sorted((set(deploy) - {"resources", "replicas"}) | (set(resources) - {"limits"}) | limits)
        if extra:
            problems.append(f"{where}: deploy chỉ hỗ trợ resources.limits (cpus, memory, pids) và replicas, không hỗ trợ "
                            f"{', '.join(extra)} (reservations.devices cho container dùng thiết bị của máy host)")
        driver = (svc.get("logging") or {}).get("driver")
        if driver not in (None, "", "json-file", "local"):
            problems.append(f"{where}: logging driver {driver} gửi log ra ngoài máy; chỉ hỗ trợ json-file, local")
        ulimits = sorted(set(svc.get("ulimits") or {}) - {"nofile"})
        if ulimits:
            problems.append(f"{where}: ulimits chỉ hỗ trợ nofile, không hỗ trợ {', '.join(ulimits)}")
    for kind, drivers, keys in (("volumes", ("local",), {"name", "driver", "labels"}),
                                ("networks", ("bridge",), {"name", "driver", "labels", "ipam", "internal"})):
        for name, spec in (config.get(kind) or {}).items():
            spec = spec or {}
            where = f"{kind} {name}"
            if spec.get("external"):
                problems.append(f"{where}: external: true gắn vào tài nguyên có sẵn không do bài tập tạo")
            if spec.get("driver_opts"):
                problems.append(f"{where}: driver_opts có thể bind thư mục hay thiết bị của máy host")
            if spec.get("driver") not in (None, "", *drivers):
                problems.append(f"{where}: driver {spec['driver']} không được hỗ trợ, chỉ {', '.join(drivers)}")
            if kind == "networks" and spec.get("ipam") not in (None, {}):
                problems.append(f"{where}: ipam tự đặt dải địa chỉ có thể đụng mạng khác trên máy")
            label = spec.get("name") or ""
            if label and not label.startswith(prefix):
                problems.append(f"{where}: name: {label} trỏ tới tài nguyên ngoài project (có thể là dữ liệu thật của "
                                f"bạn); bỏ `name:` hoặc đặt tên bắt đầu bằng {prefix}")
            extra = sorted(k for k, v in spec.items() if k not in keys and k not in ("external", "driver_opts") and v)
            if extra:
                problems.append(f"{where}: không hỗ trợ {', '.join(extra)}")
    return problems


def _dockerfile_bases(text: str, build_args: dict | None = None) -> list[str]:
    """Image base trong các dòng FROM, bỏ tên stage, `scratch` và tham chiếu ARG không resolve được."""
    build_args = {k: str(v) for k, v in (build_args or {}).items()}
    args: dict[str, str | None] = {}
    stages: set[str] = set()
    bases: list[str] = []
    seen_from = False

    def resolve(match: re.Match) -> str:
        name = match.group(1) or match.group(3)
        value = args.get(name)
        if value is None and match.group(2) is not None:
            value = match.group(2)
        if value is None:
            raise KeyError(name)
        return value

    for raw in re.sub(r"\\\r?\n", " ", text).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        word, _, rest = line.partition(" ")
        word = word.upper()
        if word == "ARG" and not seen_from:
            for item in rest.split():
                key, eq, value = item.partition("=")
                args[key] = build_args.get(key, value.strip("\"'") if eq else None)
        elif word == "FROM":
            seen_from = True
            parts = [part for part in rest.split() if not part.startswith("--")]
            if not parts:
                continue
            alias = parts[2].lower() if len(parts) >= 3 and parts[1].lower() == "as" else None
            try:
                ref = re.sub(r"\$\{(\w+)(?::?-([^}]*))?\}|\$(\w+)", resolve, parts[0])
            except KeyError:
                ref = None
            if ref and ref.lower() not in stages and ref.lower() != "scratch" and ref not in bases:
                bases.append(ref)
            if alias:
                stages.add(alias)
    return bases


class _Reset:
    pass


class _Override(list):
    pass


def _dump_override(data: dict) -> str:
    import yaml

    class Dumper(yaml.SafeDumper):
        pass

    Dumper.add_representer(_Reset, lambda dumper, _: dumper.represent_scalar("!reset", "null"))
    Dumper.add_representer(_Override, lambda dumper, value: dumper.represent_sequence("!override", list(value)))
    return yaml.dump(data, Dumper=Dumper, sort_keys=False, allow_unicode=True)


class ComposeProject:
    """Project compose do `DockerLab.compose` dựng; mọi lệnh chạy với `-p devops-ex-<id>`, tệp của người học và tệp
    override do testkit sinh ra."""

    def __init__(self, file: Path, name: str, override: Path, env: dict[str, str]) -> None:
        self.file = file
        self.name = name
        self.override = override
        self.env = env
        self.ports: dict[str, dict[int, int]] = {}

    def command(self, *args: str, override: bool = True) -> list[str]:
        files = ["-f", str(self.file)] + (["-f", str(self.override)] if override else [])
        return ["docker", "compose", "-p", self.name, "--project-directory", str(self.file.parent), *files, *args]

    def run(self, *args: str, override: bool = True, timeout: float = 120) -> subprocess.CompletedProcess:
        return subprocess.run(self.command(*args, override=override), capture_output=True, text=True, timeout=timeout,
                              env=_docker_env(self.env))

    def port(self, service: str, container_port: int) -> int:
        return self.ports[service][container_port]

    def ps(self) -> list[dict]:
        import json

        result = self.run("ps", "-a", "--format", "json")
        text = result.stdout.strip()
        if not text:
            return []
        if text.startswith("["):
            return json.loads(text)
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def container(self, service: str) -> str:
        names = [row["Name"] for row in self.ps() if row.get("Service") == service]
        if not names:
            pytest.fail(f"Không thấy container của service {service} trong project {self.name}")
        return names[0]

    def logs(self, service: str | None = None, tail: int | None = None) -> str:
        args = ["logs", "--no-color"] + (["--tail", str(tail)] if tail else []) + ([service] if service else [])
        result = self.run(*args)
        return result.stdout + result.stderr

    def exec(self, service: str, *command: str, timeout: float = 30) -> subprocess.CompletedProcess:
        return self.run("exec", "-T", service, *command, timeout=timeout)

    def down(self) -> None:
        self.run("down", "-v", "--remove-orphans", "--timeout", "5", timeout=180)


class DockerLab:
    """Network và container riêng của một test. Chỉ dùng bằng `with DockerLab() as lab:` và dựng mọi container BÊN TRONG
    khối `with` (kể cả trong fixture: `with DockerLab() as lab: ...; yield lab`): lỗi hay Ctrl-C ở bất kỳ bước nào cũng
    chạy `close()`. `start()` ngoài `with` bị từ chối.

    Mọi container: tên `devops-ex-<uuid8>-<alias>`, nhãn `devops-ex=1`, `--security-opt no-new-privileges`, ghim CPU theo
    `docker_cpu_args()`, giới hạn RAM và số tiến trình, cổng chỉ mở trên 127.0.0.1 ở cổng trống do test chọn, mount chỉ
    đọc. Container nền (`start`) KHÔNG dùng `--rm` để còn đọc được `docker logs` khi nó chết; `close()` luôn xoá mọi
    container đã tạo. `run_once` dùng `--rm`. Không đụng container hay network nào khác.
    """

    def __init__(self) -> None:
        self.id = uuid.uuid4().hex[:8]
        self.network = f"{DOCKER_PREFIX}{self.id}"
        self.names: list[str] = []
        self.ports: dict[str, dict[int, int]] = {}
        self.images: list[str] = []
        self.pushed: list[tuple[str, str | None]] = []
        self.project: ComposeProject | None = None
        self._tmp: Path | None = None
        self._network_created = False
        self._entered = False

    def __enter__(self) -> "DockerLab":
        self._entered = True
        try:
            self._open()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _open(self) -> None:
        self._network_created = True
        result = _docker("network", "create", "--label", DOCKER_LABEL, self.network)
        if result.returncode != 0:
            pytest.fail(f"Không tạo được docker network {self.network}: {result.stderr.strip()}")

    def _require_entered(self) -> None:
        if not self._entered:
            raise RuntimeError("Dùng DockerLab bằng `with DockerLab() as lab:` để container luôn được dọn")

    def name(self, alias: str) -> str:
        return f"{self.network}-{alias}"

    def run_args(self, alias: str, image: str, *command: str, detach: bool = True, mounts=(), publish=(),
                 env: dict[str, str] | None = None, entrypoint: str | None = None, memory: str = DOCKER_MEMORY,
                 pids_limit: int = DOCKER_PIDS_LIMIT) -> list[str]:
        args = ["docker", "run", "-d" if detach else "--rm"]
        args += ["--name", self.name(alias), "--label", DOCKER_LABEL, "--network", self.network, "--network-alias", alias]
        args += ["--security-opt", "no-new-privileges", "--memory", memory, "--pids-limit", str(pids_limit), *docker_cpu_args()]
        for source, target in mounts:
            args += ["-v", f"{Path(source).resolve()}:{target}:ro"]
        for container_port, host_port in publish:
            args += ["-p", f"127.0.0.1:{host_port}:{container_port}"]
        for key, value in (env or {}).items():
            args += ["-e", f"{key}={value}"]
        if entrypoint:
            args += ["--entrypoint", entrypoint]
        return [*args, image, *command]

    def _track(self, alias: str) -> str:
        name = self.name(alias)
        if name not in self.names:
            self.names.append(name)
        return name

    def start(self, alias: str, image: str, *command: str, ports=(), mounts=(), env=None, entrypoint=None,
              memory: str = DOCKER_MEMORY, pids_limit: int = DOCKER_PIDS_LIMIT) -> str:
        """Chạy container nền; `ports` là cổng trong container, cổng host lấy bằng `lab.port(alias, cổng)`."""
        self._require_entered()
        name = self._track(alias)
        result = None
        for _ in range(3):
            publish = [(port, free_port()) for port in ports]
            args = self.run_args(alias, image, *command, mounts=mounts, publish=publish, env=env, entrypoint=entrypoint,
                                 memory=memory, pids_limit=pids_limit)
            result = subprocess.run(args, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                self.ports[alias] = dict(publish)
                return name
            _docker("rm", "-f", name)
            if not any(text in result.stderr for text in _PORT_TAKEN):
                break
        pytest.fail(f"docker run {alias} ({image}) lỗi: {result.stderr.strip()}")

    def run_once(self, alias: str, image: str, *command: str, mounts=(), entrypoint=None, timeout: float = 60,
                 memory: str = DOCKER_MEMORY, pids_limit: int = DOCKER_PIDS_LIMIT) -> subprocess.CompletedProcess:
        """Chạy container tới khi xong (vd. `nginx -t`) và trả kết quả; container vẫn được dọn nếu quá giờ."""
        self._require_entered()
        self._track(alias)
        args = self.run_args(alias, image, *command, detach=False, mounts=mounts, entrypoint=entrypoint, memory=memory,
                             pids_limit=pids_limit)
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"Container {alias} chạy quá {timeout} giây")

    def port(self, alias: str, container_port: int) -> int:
        return self.ports[alias][container_port]

    def logs(self, alias: str) -> str:
        result = _docker("logs", self.name(alias))
        return result.stdout + result.stderr

    def _log_tail(self, alias: str) -> str:
        try:
            result = _docker("logs", "--tail", str(DOCKER_LOG_LINES), self.name(alias))
        except (OSError, subprocess.TimeoutExpired) as error:
            return f"(Không lấy được docker logs của {alias}: {error})"
        text = (result.stdout + result.stderr).rstrip()[-DOCKER_LOG_CHARS:] or "(không có log)"
        return f"{DOCKER_LOG_LINES} dòng log cuối của {alias}:\n{text}"

    def exec(self, alias: str, *command: str, timeout: float = 30) -> subprocess.CompletedProcess:
        return _docker("exec", self.name(alias), *command, timeout=timeout)

    def running(self, alias: str) -> bool:
        result = _docker("inspect", "-f", "{{.State.Running}}", self.name(alias))
        return result.returncode == 0 and result.stdout.strip() == "true"

    def wait_log(self, alias: str, text: str, timeout: float = 60) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if text in self.logs(alias):
                return
            if not self.running(alias):
                pytest.fail(f"Container {alias} đã dừng trước khi in '{text}'. {self._log_tail(alias)}")
            time.sleep(0.2)
        pytest.fail(f"Container {alias} không in '{text}' sau {timeout} giây. {self._log_tail(alias)}")

    def stop(self, alias: str, timeout: int = 10) -> float:
        """`docker stop -t timeout`: gửi STOPSIGNAL của image, quá `timeout` giây thì SIGKILL. Trả số giây đã chờ, để test
        đo được container có dừng sạch khi nhận SIGTERM hay không (mã thoát đọc bằng `state`)."""
        self._require_entered()
        start = time.monotonic()
        result = _docker("stop", "-t", str(timeout), self.name(alias), timeout=timeout + 60)
        if result.returncode != 0:
            pytest.fail(f"docker stop {alias} lỗi: {result.stderr.strip()}")
        return time.monotonic() - start

    def state(self, alias: str) -> dict:
        """Mục `State` của container: `Status`, `Running`, `ExitCode`, `OOMKilled`, `Health` (khi image có HEALTHCHECK)."""
        import json

        result = _docker("inspect", "-f", "{{json .State}}", self.name(alias))
        if result.returncode != 0:
            pytest.fail(f"Không đọc được trạng thái container {alias}: {result.stderr.strip()}")
        return json.loads(result.stdout)

    def ip(self, alias: str) -> str:
        result = _docker("inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", self.name(alias))
        return result.stdout.strip()

    def wait_http(self, alias: str, url: str, headers: dict[str, str] | None = None, timeout: float = 60) -> None:
        """Chờ tới khi `url` trả một response HTTP bất kỳ (kể cả 4xx/5xx); fail sớm nếu container đã dừng."""
        import httpx

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                httpx.get(url, headers=headers or {}, timeout=2, verify=False)
                return
            except httpx.HTTPError:
                pass
            if not self.running(alias):
                pytest.fail(f"Container {alias} đã dừng ngay sau khi khởi động. {self._log_tail(alias)}")
            time.sleep(0.2)
        pytest.fail(f"{url} không trả lời sau {timeout} giây. {self._log_tail(alias)}")

    def build(self, context: Path, alias: str, *, dockerfile: str = "Dockerfile", build_args: dict | None = None,
              target: str | None = None, memory: str = DOCKER_BUILD_MEMORY, timeout: float = 600) -> str:
        """Build image từ `context` (tệp của người học) bằng builder driver docker, trả tag `devops-ex-<id>/<alias>:test`.

        Bước RUN bị ghim CPU theo `docker_cpu_args()` và giới hạn RAM `memory`. Image base trong các dòng FROM phải có sẵn
        (thiếu thì skip kèm lệnh `docker pull`), cộng `--pull=false` nên build không tự kéo image. Không truyền `--network`, `--ssh`, `--secret`, `--allow` nên Dockerfile không lấy được mạng
        host, SSH agent hay bí mật. Image mang nhãn `devops-ex=1` và `devops-ex.lab=<id>`, bị `rmi -f` khi đóng.
        """
        self._require_entered()
        if not _IMAGE_ALIAS.match(alias):
            raise ValueError(f"alias {alias!r} phải là chữ thường, số, '.', '_', '-'")
        context = Path(context).resolve()
        path = (context / dockerfile).resolve()
        if not path.is_relative_to(context):
            pytest.fail(f"Dockerfile {dockerfile} nằm ngoài build context {context}")
        for base in _dockerfile_bases(path.read_text(encoding="utf-8", errors="replace"), build_args):
            Exercise.require_image(base)
        builder = _build_builder()
        tag = f"{self.network}/{alias}:test"
        if tag not in self.images:
            self.images.append(tag)
        args = ["docker", "buildx", "build", "--builder", builder, "--load", "--pull=false", "--progress=plain",
                "--label", DOCKER_LABEL, "--label", f"{DOCKER_LAB_LABEL}={self.id}", "--memory", memory, *docker_cpu_args(),
                "-f", str(path), "-t", tag]
        for key, value in (build_args or {}).items():
            args += ["--build-arg", f"{key}={value}"]
        if target:
            args += ["--target", target]
        args.append(str(context))
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=_docker_env())
        except subprocess.TimeoutExpired:
            pytest.fail(f"docker build {alias} chạy quá {timeout} giây")
        if result.returncode != 0:
            pytest.fail(f"docker build {alias} lỗi (mã {result.returncode}). {DOCKER_LOG_LINES} dòng cuối:\n{_output_tail(result)}")
        return tag

    def push(self, image: str, name: str, tag: str = "test") -> str:
        """Đẩy `image` (chỉ image do chính lab build) lên registry local thành `<registry>/devops-ex-<id>/<name>:<tag>`
        và trả tên đó. `close()` xoá manifest trên registry (registry bật `REGISTRY_STORAGE_DELETE_ENABLED`) và tag local.
        Registry chưa chạy thì skip."""
        self._require_entered()
        if not _IMAGE_ALIAS.match(name) or not _IMAGE_ALIAS.match(tag):
            raise ValueError(f"Tên {name!r} hoặc tag {tag!r} không hợp lệ: chữ thường, số, '.', '_', '-'")
        if image not in self.images and not image.startswith(f"{self.network}/"):
            pytest.fail(f"lab.push chỉ đẩy image do chính lab này build (lab.build), không đẩy {image}")
        ref = f"{Exercise.require_registry()}/{self.network}/{name}:{tag}"
        tagged = _docker("tag", image, ref)
        if tagged.returncode != 0:
            pytest.fail(f"Không gắn tag {ref} cho {image}: {tagged.stderr.strip()}")
        self.pushed.append((ref, None))
        result = _docker("push", ref, timeout=300)
        if result.returncode != 0:
            pytest.fail(f"Không push được {ref}:\n{_output_tail(result)}")
        digest = re.search(r"digest: (sha256:[0-9a-f]{64})", result.stdout or "")
        self.pushed[-1] = (ref, digest.group(1) if digest else None)
        return ref

    def _delete_pushed(self) -> None:
        for ref, digest in self.pushed:
            repo, tag = ref.split("/", 1)[1].rsplit(":", 1)
            try:
                if digest is None:
                    accept = {"Accept": ", ".join(REGISTRY_MANIFEST_TYPES)}
                    digest = _registry_request("HEAD", f"/v2/{repo}/manifests/{tag}", accept)[1].get("docker-content-digest")
                if digest:
                    _registry_request("DELETE", f"/v2/{repo}/manifests/{digest}")
                _docker("rmi", ref)
            except (OSError, subprocess.TimeoutExpired):
                pass

    def image_inspect(self, tag: str) -> dict:
        import json

        result = _docker("image", "inspect", tag)
        if result.returncode != 0:
            pytest.fail(f"Không có image {tag}: {result.stderr.strip()}")
        return json.loads(result.stdout)[0]

    def history(self, tag: str) -> list[dict]:
        """Các layer của image, mới nhất trước (`docker history --no-trunc`)."""
        import json

        result = _docker("history", "--no-trunc", "--format", "{{json .}}", tag)
        if result.returncode != 0:
            pytest.fail(f"Không đọc được history của {tag}: {result.stderr.strip()}")
        return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

    def compose(self, file: Path, *, env: dict | None = None, memory: str = DOCKER_MEMORY,
                pids_limit: int = DOCKER_PIDS_LIMIT, wait: bool = True, timeout: float = 180) -> ComposeProject:
        """`docker compose up -d` tệp `file` của người học với project `devops-ex-<id>` và một tệp override sinh ra.

        Thư mục chứa `file` được chép vào thư mục tạm của lab và compose chạy từ bản chép, nên container không ghi được
        vào repo của người học. Cấu hình được xét theo allowlist (xem `_compose_problems`); khoá ngoài danh sách, bind
        mount, `env_file` hay build context ngoài thư mục, volume/network có `name:` không bắt đầu bằng `devops-ex-<id>`
        đều bị từ chối kèm lý do. Mọi service bị override: cpuset, `mem_limit`, `pids_limit`, nhãn `devops-ex=1`,
        `security_opt: [no-new-privileges:true]`, cổng remap về `127.0.0.1:<cổng trống>` (đọc bằng
        `project.port(service, cổng)`), mọi bind mount thành chỉ đọc (cần ghi thì dùng named volume hay tmpfs), bỏ
        `container_name` và `restart`. Volume và network của project mang nhãn `devops-ex=1`. Service có `build:` được
        build bằng `DockerLab.build`; image khác phải có sẵn (`--pull never`, thiếu thì skip). Compose chạy với env dựng
        từ đầu cộng `env`. `close()` chạy `down -v --remove-orphans`. Mỗi lab một project.
        """
        import json

        self._require_entered()
        if self.project is not None:
            raise RuntimeError("Mỗi DockerLab chỉ dựng một project compose")
        reason = _compose_version_ok()
        if reason:
            pytest.skip(reason)
        source = Path(file).resolve()
        if self._tmp is None:
            self._tmp = Path(tempfile.mkdtemp(prefix=f"{self.network}-"))
        root = self._tmp / "project"
        shutil.copytree(source.parent, root, symlinks=True, ignore=shutil.ignore_patterns(*_COPY_IGNORE))
        file = root / source.name
        cpus = docker_cpu_args()
        cpuset = cpus[1] if cpus else ""
        project = ComposeProject(file, self.network, self._tmp / "compose.override.yaml",
                                 {"DEVOPS_CPUSET": cpuset, **{k: str(v) for k, v in (env or {}).items()}})
        self.project = project
        result = project.run("config", "--no-env-resolution", "--format", "json", override=False)
        if result.returncode != 0:
            pytest.fail(f"docker compose config lỗi với {file.name}: {result.stderr.strip()}")
        config = json.loads(result.stdout)
        problems = _compose_problems(config, root, self.id)
        if problems:
            pytest.fail(f"Tệp {source.name} bị từ chối vì phá cách ly của bài tập:\n- " + "\n- ".join(problems))
        services = config.get("services") or {}
        built: dict[tuple, str] = {}
        images: dict[str, str] = {}
        for name, svc in services.items():
            spec = svc.get("build")
            if spec:
                key = (spec.get("context"), spec.get("dockerfile", "Dockerfile"), json.dumps(spec.get("args") or {}, sort_keys=True),
                       spec.get("target"))
                if key not in built:
                    built[key] = self.build(Path(spec["context"]), name.lower(), dockerfile=spec.get("dockerfile", "Dockerfile"),
                                            build_args=spec.get("args"), target=spec.get("target"))
                images[name] = built[key]
            elif svc.get("image") and _docker("image", "inspect", svc["image"]).returncode != 0:
                pytest.skip(f"Chưa có image {svc['image']}. Tải bằng: docker pull {svc['image']}")
        up = ["up", "-d", "--pull", "never", "--no-build"] + (["--wait", "--wait-timeout", str(int(timeout))] if wait else [])
        for _ in range(3):
            override, ports = self._compose_override(config, images, cpuset, memory, pids_limit)
            project.override.write_text(_dump_override(override), encoding="utf-8")
            try:
                result = project.run(*up, timeout=timeout + 60)
            except subprocess.TimeoutExpired:
                pytest.fail(f"docker compose up chạy quá {timeout} giây. {DOCKER_LOG_LINES} dòng log cuối:\n"
                            f"{project.logs(tail=DOCKER_LOG_LINES)[-DOCKER_LOG_CHARS:]}")
            if result.returncode == 0:
                project.ports = ports
                return project
            if not any(text in result.stderr for text in _PORT_TAKEN):
                break
            project.down()
        logs = project.logs(tail=DOCKER_LOG_LINES).rstrip()[-DOCKER_LOG_CHARS:] or "(không có log)"
        pytest.fail(f"docker compose up lỗi: {result.stderr.strip()[-DOCKER_LOG_CHARS:]}\n{DOCKER_LOG_LINES} dòng log cuối:\n{logs}")

    def _compose_override(self, config: dict, images: dict[str, str], cpuset: str, memory: str,
                          pids_limit: int) -> tuple[dict, dict[str, dict[int, int]]]:
        labels = {"devops-ex": "1", DOCKER_LAB_LABEL: self.id}
        override: dict[str, dict] = {}
        ports: dict[str, dict[int, int]] = {}
        for name, svc in (config.get("services") or {}).items():
            item: dict[str, Any] = {
                "labels": dict(labels),
                "restart": _Reset(),
                "security_opt": _Override(["no-new-privileges:true"]),
                "cpuset": cpuset if cpuset else _Reset(),
                "mem_limit": memory,
                "pids_limit": pids_limit,
                "deploy": {"resources": {"limits": {"memory": memory, "pids": pids_limit}}},
                "pull_policy": "never",
            }
            if "memswap_limit" in svc:
                item["memswap_limit"] = _Reset()
            if "container_name" in svc:
                item["container_name"] = _Reset()
            if any(v.get("type") == "bind" for v in svc.get("volumes") or []):
                item["volumes"] = _Override([{**v, "read_only": True} if v.get("type") == "bind" else v for v in svc["volumes"]])
            if name in images:
                item["build"] = _Reset()
                item["image"] = images[name]
            if svc.get("ports"):
                mapping = {int(p["target"]): free_port() for p in svc["ports"]}
                item["ports"] = _Override([f"127.0.0.1:{mapping[int(p['target'])]}:{p['target']}/{p.get('protocol', 'tcp')}"
                                           for p in svc["ports"]])
                ports[name] = mapping
            override[name] = item
        result: dict[str, Any] = {"services": override}
        for kind in ("volumes", "networks"):
            if config.get(kind):
                result[kind] = {key: {"labels": dict(labels)} for key in config[kind]}
        return result, ports

    def close(self) -> None:
        if self.project is not None:
            try:
                self.project.down()
            except (OSError, subprocess.TimeoutExpired):
                pass
        for name in self.names:
            try:
                _docker("rm", "-f", name)
            except (OSError, subprocess.TimeoutExpired):
                pass
        self._delete_pushed()
        for tag in self.images:
            try:
                _docker("rmi", "-f", tag)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if self.images:
            try:
                ids = _docker("images", "-q", "--filter", f"label={DOCKER_LAB_LABEL}={self.id}").stdout.split()
                if ids:
                    _docker("rmi", "-f", *sorted(set(ids)))
            except (OSError, subprocess.TimeoutExpired):
                pass
        if self._network_created:
            try:
                _docker("network", "rm", self.network)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if self._tmp is not None:
            shutil.rmtree(self._tmp, ignore_errors=True)


_BWRAP_ISOLATION = ["--unshare-user", "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--die-with-parent", "--new-session"]
_UNSAFE_ENV = re.compile(r"^(?:BASH_ENV|ENV|BASH_FUNC_.*|LD_PRELOAD|LD_LIBRARY_PATH|SHELLOPTS|BASHOPTS|PROMPT_COMMAND|PS4)$")
SANDBOX_SKIP = (
    "Bài này chạy script của bạn trong sandbox bubblewrap (bwrap) để một script viết sai không xoá hay sửa được tệp "
    "nào ngoài thư mục tạm của test; test từ chối chạy khi không có sandbox. {reason} Cài: sudo apt install bubblewrap "
    "(Fedora: sudo dnf install bubblewrap). Xem setup/DEVOPS-TOOLS.md"
)


CREDENTIAL_PATHS = (
    ".docker", ".kube", ".aws", ".ssh", ".config/gcloud", ".azure", ".config/gh", ".git-credentials", ".netrc", ".terraform.d",
)


def _real_homes() -> list[Path]:
    homes = {Path(os.path.expanduser("~"))}
    try:
        import pwd

        homes.add(Path(pwd.getpwuid(os.getuid()).pw_dir))
    except (ImportError, KeyError):
        pass
    return sorted(h.resolve() for h in homes if h.is_dir())


def _credential_targets() -> list[Path]:
    """Đích thật (đã resolve symlink, tuyệt đối hay tương đối) của `CREDENTIAL_PATHS` trong mọi home thật; bỏ đích không
    tồn tại và đích dưới /tmp (đã bị che sẵn). bwrap không mount được lên chính symlink, nên phải mount lên đích."""
    targets: list[Path] = []
    for home in _real_homes():
        for rel in CREDENTIAL_PATHS:
            target = (home / rel).resolve()
            if target.exists() and not target.is_relative_to("/tmp") and target not in targets:
                targets.append(target)
    return targets


def _base_flags(bwrap: str) -> list[str]:
    """Cờ chung cho lần thử và lần chạy thật: / chỉ đọc, /tmp và /run là tmpfs rỗng (che socket docker, D-Bus), thư mục
    thông tin đăng nhập bị phủ tmpfs, tệp thông tin đăng nhập bị thay bằng /dev/null."""
    args = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", "/run"]
    for target in _credential_targets():
        if target.is_dir():
            args += ["--tmpfs", str(target)]
        else:
            args += ["--ro-bind", "/dev/null", str(target)]
    return args


_SANDBOX_OK: set[tuple[str, ...]] = set()


def sandbox_ready() -> str | None:
    """Trả None khi bwrap tạo được sandbox với đúng bộ cờ của lần chạy thật, ngược lại trả lý do. Chỉ cache lần thử thành
    công (theo bộ cờ), nên lỗi tạm thời không làm skip cả phiên."""
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return "Chưa cài bwrap."
    argv = (*_base_flags(bwrap), *_BWRAP_ISOLATION, "--clearenv", "--", "true")
    if argv in _SANDBOX_OK:
        return None
    probe = _run_tool(list(argv))
    if probe is not None and probe.returncode == 0:
        _SANDBOX_OK.add(argv)
        return None
    detail = (probe.stderr.strip() if probe is not None else "") or "không rõ lỗi"
    return f"bwrap có nhưng không tạo được sandbox ({detail}); có thể kernel chặn user namespace không đặc quyền."


def _clean_env(env: dict[str, str], home: Path) -> dict[str, str]:
    base = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": str(home), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    base.update({k: v for k, v in env.items() if not _UNSAFE_ENV.match(k)})
    return base


def _hidden_by_tmpfs() -> list[Path]:
    hidden = (Path("/tmp"), Path("/run"))
    candidates = {ROOT, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), Path(sys.executable).resolve().parent}
    return sorted(p for p in candidates if any(p.is_relative_to(h) and p != h for h in hidden))


def sandbox_command(cmd: list, *, writable: list[Path], cwd: Path, env: dict[str, str]) -> list[str]:
    """argv chạy `cmd` trong bwrap: / chỉ đọc, /tmp và /run là tmpfs rỗng, `CREDENTIAL_PATHS` của home thật bị che, chỉ
    `writable` ghi được, môi trường dựng lại từ đầu.

    Mạng KHÔNG bị tách (không --unshare-net): test healthcheck cần gọi server giả trên loopback của máy. Chấp nhận được vì
    mô hình đe doạ là script viết sai vô tình phá dữ liệu, không phải mã độc; socket của docker và D-Bus vẫn bị che.
    """
    reason = sandbox_ready()
    if reason:
        pytest.skip(SANDBOX_SKIP.format(reason=reason))
    args = _base_flags(shutil.which("bwrap"))
    for path in _hidden_by_tmpfs():
        args += ["--ro-bind", str(path), str(path)]
    for path in writable:
        real = str(Path(path).resolve())
        args += ["--bind", real, real]
    home = Path(cwd).resolve()
    args += ["--chdir", str(home), *_BWRAP_ISOLATION, "--clearenv"]
    for key, value in _clean_env(env, home).items():
        args += ["--setenv", key, value]
    return [*args, "--", *map(str, cmd)]


def run_sandboxed(
    cmd: list,
    *,
    writable: list[Path],
    cwd: Path,
    env: dict[str, str],
    timeout: float = 30,
    input: str | None = None,
) -> subprocess.CompletedProcess:
    """Chạy lệnh của người học trong sandbox bwrap; skip (không bao giờ chạy trần) khi không có sandbox.

    Không tách mạng (xem `sandbox_command`): đủ cho mục tiêu chặn script lỗi xoá hay sửa tệp thật.
    """
    argv = sandbox_command(cmd, writable=writable, cwd=cwd, env=env)
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, input=input, env={})


SAFE_GIT_CONFIG = (
    "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main",
)
GIT_DATE = "2026-05-01T10:00:00+00:00"


def git_env(home: Path, *, date: str | None = None) -> dict[str, str]:
    """Env dựng từ đầu cho git của test: HOME tạm, không đọc cấu hình global/system của người học, tác giả và ngày cố
    định (commit tất định), không hỏi mật khẩu hay mở editor, không dò repo lên quá thư mục chứa `home`."""
    stamp = date or GIT_DATE
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CEILING_DIRECTORIES": str(Path(home).resolve().parent),
        "GIT_AUTHOR_NAME": "Olist Dev",
        "GIT_AUTHOR_EMAIL": "dev@olist-shop.example",
        "GIT_COMMITTER_NAME": "Olist Dev",
        "GIT_COMMITTER_EMAIL": "dev@olist-shop.example",
        "GIT_AUTHOR_DATE": stamp,
        "GIT_COMMITTER_DATE": stamp,
        "GIT_EDITOR": "true",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


class GitRepo:
    """Repo git tạm của một test. Trước `taint()`: git chạy trực tiếp kèm `SAFE_GIT_CONFIG` (dựng lịch sử nhanh). Gọi
    `taint()` ngay khi code người học đã chạy trong repo: cấu hình repo có thể đã bị sửa (filter driver, alias, pager...)
    mà `SAFE_GIT_CONFIG` không chặn hết, nên từ đó mọi lệnh git chạy qua `run_sandboxed`.

    `writable` mặc định là `path` và `home`; truyền `[tmp_path]` khi git cần ghi chỗ khác (remote bare, clone khác).
    """

    def __init__(self, path: Path, home: Path, *, writable: list[Path] | None = None) -> None:
        self.path = Path(path)
        self.home = Path(home)
        self.writable = list(writable) if writable is not None else [self.path, self.home]
        self.tainted = False

    def taint(self) -> None:
        self.tainted = True

    def git(self, *args: str, timeout: float = 30) -> subprocess.CompletedProcess:
        cmd = ["git", *SAFE_GIT_CONFIG, *args]
        env = git_env(self.home)
        if self.tainted:
            return run_sandboxed(cmd, writable=self.writable, cwd=self.path, env=env, timeout=timeout)
        return subprocess.run(cmd, cwd=self.path, env=env, capture_output=True, text=True, timeout=timeout)

    def out(self, *args: str, check: bool = True, timeout: float = 30) -> str:
        """stdout đã strip; `check` thì lệnh lỗi là AssertionError kèm stderr."""
        result = self.git(*args, timeout=timeout)
        if check and result.returncode != 0:
            raise AssertionError(f"git {' '.join(args)}: {result.stderr}")
        return result.stdout.strip()


ACT_RUNNER_DIR = ROOT / "setup" / "act-runner"
ACT_RUNNER_FILES = ("Dockerfile", "requirements-ci.txt")
ACT_RUNNER_VERSION = "1.0"
ACT_BASE_IMAGE = "node:24.22.2-trixie-slim"


def act_runner_tag() -> str:
    """Tag của image runner: `<ACT_RUNNER_VERSION>-<8 ký tự đầu SHA-256 của Dockerfile nối requirements-ci.txt>`, bằng đúng
    `cat Dockerfile requirements-ci.txt | sha256sum | cut -c1-8` trong README. Đổi phiên bản, ARG hay wheel trong hai tệp đó
    là đổi tag, nên image cũ không bao giờ được dùng nhầm."""
    import hashlib

    digest = hashlib.sha256(b"".join((ACT_RUNNER_DIR / name).read_bytes() for name in ACT_RUNNER_FILES)).hexdigest()
    return f"{ACT_RUNNER_VERSION}-{digest[:8]}"


def _act_base_digest() -> str:
    match = re.search(rf"^FROM\s+{re.escape(ACT_BASE_IMAGE)}@(sha256:[0-9a-f]{{64}})\s*$",
                      (ACT_RUNNER_DIR / "Dockerfile").read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else ""


ACT_IMAGE = f"devops-track/act-runner:{act_runner_tag()}"
ACT_IMAGE_BUILD = (
    f"docker pull {ACT_BASE_IMAGE} && docker image inspect --format '{{{{index .RepoDigests 0}}}}' {ACT_BASE_IMAGE} | "
    f"grep -qx 'node@{_act_base_digest()}' && nice -n 15 docker build --pull=false "
    '${DEVOPS_CPUSET:+--cpuset-cpus "$DEVOPS_CPUSET"} '
    f"-t {ACT_IMAGE} setup/act-runner"
)
ACT_CHECKOUT_INPUTS = frozenset({
    "persist-credentials", "fetch-depth", "fetch-tags", "clean", "lfs", "submodules", "show-progress", "filter",
    "sparse-checkout", "sparse-checkout-cone-mode", "set-safe-directory", "path",
})
ACT_STATUS_FUNCTIONS = frozenset({"always()", "success()", "failure()", "cancelled()", "!cancelled()"})
ACT_MIN_VERSION = "0.2.94"
ACT_MEMORY = "1g"
ACT_PIDS_LIMIT = 512
ACT_CONCURRENT_JOBS = 2
ACT_RUN_LABEL = "devops-ex.act"
ACT_ALLOWED_ACTIONS = ("actions/checkout",)
ACT_REMOTE = "https://github.com/olist-shop/olist-shop.git"
ACT_SECRET_MIN_LENGTH = 4
_ACT_ENV_NAMES = {"PATH", "HOME", "LANG", "LC_ALL", "DOCKER_HOST", "ACT"}
_ACT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ACT_EVENT = re.compile(r"[a-z_]+")
_ACT_JOB_RESULT = re.compile(r"^\[([^\]]+)\]\s+🏁\s+Job (succeeded|failed)\s*$", re.M)
_ACT_OUTPUT = re.compile(r"^\[([^\]]+)\]\s+\|\s+devops-ex-output ([A-Za-z_][A-Za-z0-9_.-]*)=(.*?)\r?$", re.M)
_ACT_CLONE_FAILED = re.compile(
    r"Unable to clone https://github\.com/(\S+?)(?:\.git)? \S+: .*?"
    r"(?:dial tcp|lookup |network is unreachable|Could not resolve|no such host|i/o timeout|connection refused)"
)


def act_cache_dir() -> Path:
    """Cache action dùng chung giữa các lần chạy (HOME của act là thư mục tạm): action tải một lần, sau đó chấm offline."""
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "devops-track" / "act"


def act_job_results(result: subprocess.CompletedProcess) -> dict[str, bool]:
    """Kết quả từng job (theo job id) đọc từ output của `act_run`: True là succeeded, False là failed."""
    text = f"{result.stdout or ''}\n{result.stderr or ''}"
    return {job: status == "succeeded" for job, status in _ACT_JOB_RESULT.findall(text)}


def act_outputs(result: subprocess.CompletedProcess) -> dict[str, dict[str, str]]:
    """Giá trị workflow gửi ra cho harness, theo job id: mỗi dòng `devops-ex-output <key>=<value>` mà một bước in ra stdout
    (vd. `echo "devops-ex-output tag=$TAG"`). Cần vì workspace của job là bản chép, tệp job ghi ra không về tới test."""
    found: dict[str, dict[str, str]] = {}
    for job, key, value in _ACT_OUTPUT.findall(f"{result.stdout or ''}\n{result.stderr or ''}"):
        found.setdefault(job, {})[key] = value
    return found


def _act_workflow_files(repo: Path) -> list[Path]:
    folder = repo / ".github" / "workflows"
    return sorted([*folder.rglob("*.yml"), *folder.rglob("*.yaml")]) if folder.is_dir() else []


def _act_skipped_locally(condition) -> bool:
    """True khi `if:` chắc chắn sai dưới act: biểu thức (bỏ `${{ }}` và khoảng trắng) đúng bằng `!env.ACT`, hoặc là chuỗi
    `&&` ở cấp trên cùng có một vế đúng bằng `!env.ACT` và mọi vế có ngoặc khác đúng bằng một hàm trạng thái
    (`always()`, `success()`, `failure()`, `cancelled()`, `!cancelled()`). Chuỗi trong nháy đơn được thay bằng chỗ giữ trước
    khi xét; có `||`, nháy kép, `!=`, `$`, `{`, `}`, `[`, `]` hay ngoặc ở chỗ khác thì không công nhận."""
    text = str(condition or "").strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    text = re.sub(r"'(?:[^']|'')*'", "'S'", text)
    text = re.sub(r"\s+", "", text)
    if any(token in text for token in ("||", '"', "!=", "$", "{", "}", "[", "]")):
        return False
    terms = text.split("&&")
    if "!env.ACT" not in terms:
        return False
    return all(term in ACT_STATUS_FUNCTIONS for term in terms if "(" in term or ")" in term)


_ACT_REMOTE_ACTION = re.compile(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)((?:/[A-Za-z0-9_.-]+)*)@([A-Za-z0-9_.-][A-Za-z0-9_./-]*)")
_ACT_STUB = "name: devops-ex-stub\nruns:\n  using: composite\n  steps: []\n"


def _act_remote_action(uses) -> tuple[str, str] | None:
    """`owner/repo[/path]@ref` hợp lệ thì trả (`owner/repo@ref`, `path`), ngược lại None. Không nhận đoạn `.`, `..` hay đoạn
    rỗng, nên `path` không bao giờ thoát ra ngoài thư mục stub."""
    match = _ACT_REMOTE_ACTION.fullmatch(str(uses or ""))
    if not match:
        return None
    owner, repo, path, ref = match.groups()
    segments = [owner, repo, *path.split("/")[1:]]
    if any(not s or set(s) == {"."} for s in segments):
        return None
    return f"{owner}/{repo}@{ref}", path.lstrip("/")


def _act_step_problem(where: str, step) -> str | None:
    uses = step.get("uses") if isinstance(step, dict) else None
    if uses is not None and (not isinstance(uses, str) or re.search(r"\s", uses) or not uses):
        return f"{where}: `uses: {uses!r}` không hợp lệ: không được rỗng hay chứa khoảng trắng, xuống dòng"
    if not uses:
        return None
    if uses.split("@", 1)[0] == "actions/checkout":
        options = step.get("with") or {}
        extra = sorted(str(k) for k in options) if isinstance(options, dict) else ["(không phải bảng key: value)"]
        extra = [k for k in extra if k not in ACT_CHECKOUT_INPUTS]
        if extra:
            return (f"{where}: actions/checkout có `with:` {', '.join(extra)}; khi chấm, act chỉ chép thẳng repo vào job khi "
                    "không đặt ref/repository (và input lạ khác), nếu không nó tải actions/checkout thật từ GitHub. Bỏ các "
                    f"input đó; được dùng: {', '.join(sorted(ACT_CHECKOUT_INPUTS))}")
        return None
    if uses.split("@", 1)[0] in ACT_ALLOWED_ACTIONS:
        return None
    allowed = ", ".join(ACT_ALLOWED_ACTIONS)
    if str(uses).startswith(("docker://", "./", "../", "/")):
        return f"{where}: `uses: {uses}` (image Docker hoặc action cục bộ) không được dùng trong bài chấm bằng act, kể cả có `if:`"
    if _act_remote_action(uses) is None:
        return f"{where}: `uses: {uses}` không phải dạng owner/repo[/đường-dẫn]@ref hợp lệ"
    if _act_skipped_locally(step.get("if")):
        return None
    return (f"{where}: action {uses} không chạy được khi chấm; chỉ dùng bước run: và {allowed}, hoặc gắn đúng "
            "`if: ${{ !env.ACT }}` (có thể nối thêm điều kiện bằng `&&`) để bước đó chỉ chạy trên GitHub")


def _act_guarded_stubs(repo: Path, root: Path) -> list[str]:
    """Bước `uses:` có `if: !env.ACT` không chạy dưới act, nhưng act vẫn clone action của nó lúc dựng job. Thay mỗi action
    đó bằng một action composite rỗng cục bộ (`--local-repository`) để không tải gì từ mạng và không có mã lạ nào trên máy.
    Mọi `actions/checkout@<ref>` cũng được thay (act chép repo cục bộ nên không cần mã của action): nếu act vì lý do nào đó
    không nhận ra checkout cục bộ, nó vẫn không tải gì."""
    import yaml

    stubs: dict[str, Path] = {}
    base = (root / "stubs").resolve()
    for path in _act_workflow_files(repo):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        jobs = data.get("jobs") if isinstance(data, dict) else None
        for job in (jobs or {}).values() if isinstance(jobs, dict) else ():
            for step in (job.get("steps") or []) if isinstance(job, dict) else []:
                if not isinstance(step, dict) or not step.get("uses"):
                    continue
                allowed = str(step["uses"]).split("@", 1)[0] in ACT_ALLOWED_ACTIONS
                if not allowed and not _act_skipped_locally(step.get("if")):
                    continue
                parsed = _act_remote_action(step["uses"])
                if parsed is None:
                    pytest.fail(f"Không tạo được action thay thế cho `uses: {step['uses']}`")
                key, subpath = parsed
                stub = stubs.setdefault(key, base / str(len(stubs)))
                folder = (stub / subpath).resolve()
                if not folder.is_relative_to(base):
                    pytest.fail(f"`uses: {step['uses']}` trỏ ra ngoài thư mục action thay thế")
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "action.yml").write_text(_ACT_STUB, encoding="utf-8")
    return [arg for key, stub in stubs.items() for arg in ("--local-repository", f"{key}={stub}")]


def _act_env_problem(where: str, env) -> str | None:
    """`!env.ACT` chỉ đáng tin khi workflow không tự đặt `ACT`: đặt `ACT: ''` ở `env:` sẽ làm bước chỉ dành cho GitHub
    chạy luôn dưới act."""
    if env is None:
        return None
    if not isinstance(env, dict):
        return f"{where}: `env:` phải là bảng key: value cố định khi chấm bằng act (không dùng biểu thức)"
    if any(str(key).upper() == "ACT" for key in env):
        return (f"{where}: không được đặt biến `ACT` trong `env:`; act dùng biến này để bỏ qua bước `if: ${{{{ !env.ACT }}}}`, "
                "ghi đè nó sẽ làm bước chỉ dành cho GitHub chạy trên máy chấm")
    return None


def _act_workflow_problems(repo: Path) -> list[str]:
    import yaml

    folder = repo / ".github" / "workflows"
    files = _act_workflow_files(repo)
    if not files:
        return ["không có workflow nào trong .github/workflows/"]
    problems = []
    for path in files:
        rel = path.relative_to(repo)
        if path.parent != folder:
            problems.append(f"{rel}: workflow phải nằm ngay trong .github/workflows/, không nằm trong thư mục con")
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            problems.append(f"{rel}: YAML không hợp lệ: {error}")
            continue
        jobs = data.get("jobs") if isinstance(data, dict) else None
        problems += filter(None, [_act_env_problem(str(rel), data.get("env") if isinstance(data, dict) else None)])
        for job_id, job in (jobs or {}).items() if isinstance(jobs, dict) else ():
            if not isinstance(job, dict):
                continue
            where = f"{rel}, job {job_id}"
            problems += filter(None, [_act_env_problem(where, job.get("env"))])
            if "uses" in job:
                problems.append(f"{where}: gọi workflow khác ({job['uses']}) chưa được hỗ trợ khi chấm")
                continue
            for key in ("services", "container"):
                if key in job:
                    problems.append(f"{where}: `{key}:` chưa được hỗ trợ khi chấm (container phụ không bị giới hạn CPU, RAM như job)")
            runs_on = job.get("runs-on")
            if (runs_on if isinstance(runs_on, list) else [runs_on]) != ["ubuntu-latest"]:
                problems.append(f"{where}: runs-on phải là ubuntu-latest (đang là {runs_on!r})")
            for index, step in enumerate(job.get("steps") or [], 1):
                problems += filter(None, [
                    _act_step_problem(where, step),
                    _act_env_problem(f"{where}, bước {index}", step.get("env")) if isinstance(step, dict) else None,
                ])
    return problems


def _act_rename_workflow(path: Path, prefix: str) -> None:
    """Đổi `name:` cấp trên cùng thành `<prefix>-<tên cũ hoặc tên tệp>`. act đặt tên container và volume là
    `act-<name>-<job>-<hash>` không phụ thuộc lần chạy; tiền tố riêng giúp không bao giờ trùng (và xoá nhầm) tài nguyên của
    lần chạy khác hay của người học."""
    import json

    import yaml

    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    original = data.get("name") if isinstance(data, dict) else None
    wanted = f"{prefix}-{original if isinstance(original, str) and original.strip() else path.stem}"
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if re.match(r"name\s*:", line)), None)
    if start is not None:
        end = start + 1
        while end < len(lines) and (lines[end][:1] in (" ", "\t") or not lines[end].strip()):
            end += 1
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        lines[start:end] = []
    head = 0
    while head < len(lines) and (not lines[head].strip() or lines[head].startswith(("#", "%"))):
        head += 1
    insert_at = head + 1 if head < len(lines) and re.match(r"---(\s|$)", lines[head]) else 0
    lines.insert(insert_at, f"name: {json.dumps(wanted, ensure_ascii=False)}\n")
    renamed = "".join(lines)
    check = yaml.safe_load(renamed)
    if not isinstance(check, dict) or check.get("name") != wanted or {k: v for k, v in check.items() if k != "name"} != {
        k: v for k, v in (data or {}).items() if k != "name"
    }:
        pytest.fail(f"Không đổi được tên workflow {path.name} an toàn; kiểm lại dòng `name:` cấp trên cùng")
    path.write_text(renamed, encoding="utf-8")


def _act_repo(workflow_dir: Path, root: Path, run_id: str) -> Path:
    repo = root / "repo"
    shutil.copytree(workflow_dir, repo, symlinks=True, ignore=shutil.ignore_patterns(*_COPY_IGNORE))
    (repo / ".actrc").unlink(missing_ok=True)
    problems = _act_workflow_problems(repo)
    if problems:
        pytest.fail("Workflow dùng thứ mà bài chấm bằng act không hỗ trợ:\n- " + "\n- ".join(problems))
    for path in _act_workflow_files(repo):
        _act_rename_workflow(path, f"{DOCKER_PREFIX}{run_id}")
    git = GitRepo(repo, root / "git-home")
    git.home.mkdir()
    git.out("init", "-q")
    git.out("remote", "add", "origin", ACT_REMOTE)
    git.out("add", "-A")
    git.out("commit", "-q", "--allow-empty", "-m", "bài nộp")
    return repo


def _act_docker_host() -> str:
    result = _docker("context", "inspect", "--format", "{{.Endpoints.docker.Host}}")
    host = result.stdout.strip() if result.returncode == 0 else ""
    return host or "unix:///var/run/docker.sock"


def _act_command(repo: Path, run_id: str, *, event: str, job: str | None, env: dict, secret_names: list[str]) -> list[str]:
    options = [
        *docker_cpu_args(), "--memory", ACT_MEMORY, "--pids-limit", str(ACT_PIDS_LIMIT), "--security-opt", "no-new-privileges",
        "--label", DOCKER_LABEL, "--label", f"{ACT_RUN_LABEL}={run_id}",
    ]
    argv = [
        "act", event, "-C", str(repo), "-W", f"{repo / '.github' / 'workflows'}/", "--no-recurse",
        "-P", f"ubuntu-latest={ACT_IMAGE}", "--pull=false",
        "--container-options", " ".join(options), "--container-daemon-socket", "-", "--container-options-policy", "restrict",
        "--network", f"{DOCKER_PREFIX}{run_id}", "--action-cache-path", str(act_cache_dir()), "--action-offline-mode",
        "--no-cache-server", "--rm", "--log-prefix-job-id", "--concurrent-jobs", str(ACT_CONCURRENT_JOBS),
        "--env-file", "/dev/null", "--secret-file", "/dev/null", "--var-file", "/dev/null", "--input-file", "/dev/null",
    ]
    if job:
        argv += ["-j", job]
    for key, value in env.items():
        argv += ["--env", f"{key}={value}"]
    for name in secret_names:
        argv += ["-s", name]
    return argv


def _act_cleanup(run_id: str) -> None:
    """Dọn tài nguyên của đúng một lần chạy: container vừa có nhãn `devops-ex.act=<id>` vừa có tên bắt đầu bằng
    `act-devops-ex-<id>`, volume và network do act tạo có tên bắt đầu bằng `act-devops-ex-<id>` (tên riêng của lần chạy nhờ
    `_act_rename_workflow`), và network `devops-ex-<id>` có nhãn của lần chạy. Volume dùng chung `act-toolcache` không
    bao giờ bị xoá (act 0.2.94 không cho đổi tên volume này)."""
    prefix = f"act-{DOCKER_PREFIX}{run_id}"
    label = f"label={ACT_RUN_LABEL}={run_id}"

    def names(*args: str) -> list[str]:
        try:
            return _docker(*args).stdout.split()
        except (OSError, subprocess.TimeoutExpired):
            return []

    containers = [n for n in names("ps", "-a", "--filter", label, "--format", "{{.Names}}") if n.startswith(prefix)]
    networks = [n for n in names("network", "ls", "--filter", label, "--format", "{{.Name}}") if n == f"{DOCKER_PREFIX}{run_id}"]
    networks += [n for n in names("network", "ls", "--filter", f"name={prefix}", "--format", "{{.Name}}") if n.startswith(prefix)]
    if containers:
        names("rm", "-f", *containers)
    volumes = [n for n in names("volume", "ls", "--filter", f"name={prefix}", "--format", "{{.Name}}") if n.startswith(prefix)]
    if volumes:
        names("volume", "rm", *volumes)
    for network in networks:
        names("network", "rm", network)


def _act_kill(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _act_execute(argv: list[str], repo: Path, env: dict[str, str], run_id: str, timeout: float) -> tuple[str, str, int, bool]:
    try:
        network = f"{DOCKER_PREFIX}{run_id}"
        created = _docker("network", "create", "--label", DOCKER_LABEL, "--label", f"{ACT_RUN_LABEL}={run_id}", network)
        if created.returncode != 0:
            pytest.fail(f"Không tạo được docker network {network}: {created.stderr.strip()}")
        process = subprocess.Popen(
            argv, cwd=repo, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return stdout, stderr, process.returncode, False
        except subprocess.TimeoutExpired:
            _act_kill(process)
            stdout, stderr = process.communicate()
            return stdout, stderr, process.returncode, True
        except BaseException:
            _act_kill(process)
            process.wait()
            raise
    finally:
        _act_cleanup(run_id)


def act_run(
    workflow_dir: Path,
    *,
    event: str = "push",
    job: str | None = None,
    env: dict | None = None,
    secrets: dict | None = None,
    timeout: float = 600,
) -> subprocess.CompletedProcess:
    """Chạy workflow GitHub Actions trong `workflow_dir/.github/workflows/` bằng `act` và trả CompletedProcess (kết quả từng
    job: `act_job_results`; giá trị gửi ra: `act_outputs`). Skip khi thiếu `act`, git hay image runner `ACT_IMAGE`.

    act chạy trên host (cần socket Docker nên không vào được bwrap) trên bản chép tạm của `workflow_dir` (bỏ `.git`,
    `.actrc`) thành repo git mới, với `name:` của mọi workflow đổi thành `devops-ex-<id>-<tên cũ>` để container, volume
    của act mang tên riêng của lần chạy. Env dựng từ đầu (`HOME` tạm nên không đọc `~/.actrc`, `~/.config/act`; không mang
    `GITHUB_TOKEN`, `ACTIONS_*`, `AWS_*`, `DOCKER_*`; `DOCKER_HOST` lấy từ context Docker hiện tại); `.env`, `.secrets`,
    `.vars`, `.input` của repo không được đọc; chỉ chạy workflow ngay trong `.github/workflows/` (`-W`, `--no-recurse`).
    Job chạy trong `ACT_IMAGE` (`--pull=false`) trên network riêng `devops-ex-<id>`, ghim CPU theo `docker_cpu_args()`,
    RAM 1g, 512 tiến trình, `no-new-privileges`, nhãn `devops-ex=1` và `devops-ex.act=<id>`, không có socket Docker
    (`--container-daemon-socket -`), options của workflow bị chặn (`--container-options-policy restrict`), không cache
    server.

    Workflow (kể cả tệp trong thư mục con) chỉ được `runs-on: ubuntu-latest`, bước `run:`, action trong
    `ACT_ALLOWED_ACTIONS`, và action khác chỉ ở bước có `if:` chứa `!env.ACT` (act bỏ qua bước đó, chỉ GitHub chạy);
    không `services:`, `container:`, workflow gọi workflow (fail kèm lý do).

    `actions/checkout` không tải gì: act chép thẳng bản chép tạm vào job. Action khác (khi được thêm vào danh sách) tải về
    `act_cache_dir()` lần đầu rồi dùng lại offline (`--action-offline-mode`); thiếu action mà không có mạng thì skip.

    `secrets` đi qua env của tiến trình act (argv chỉ có tên), act che giá trị thành `***` trong log, testkit che thêm
    lần nữa trong output trả về; giá trị ngắn hơn `ACT_SECRET_MIN_LENGTH` bị từ chối (che chuỗi quá ngắn làm hỏng output
    mà không bảo vệ được gì). Quá `timeout` thì SIGKILL cả nhóm tiến trình và fail kèm output cuối. Mọi đường thoát (xong,
    lỗi, timeout, Ctrl-C) đều dọn container, volume, network mang tên riêng của lần chạy đó (xem `_act_cleanup`).
    """
    env = {str(k): str(v) for k, v in (env or {}).items()}
    secrets = {str(k): str(v) for k, v in (secrets or {}).items()}
    bad = [n for n in [*env, *secrets] if not _ACT_NAME.fullmatch(n) or n.upper() in _ACT_ENV_NAMES or n.upper().startswith("GITHUB_")]
    if bad:
        pytest.fail(f"Tên biến hoặc secret không dùng được với act_run: {bad} (chữ, số, '_'; không trùng PATH, HOME, ACT..., không bắt đầu bằng GITHUB_)")
    short = sorted(name for name, value in secrets.items() if len(value) < ACT_SECRET_MIN_LENGTH)
    if short:
        pytest.fail(f"Secret {short} ngắn hơn {ACT_SECRET_MIN_LENGTH} ký tự: act_run không che được an toàn, dùng giá trị dài hơn")
    if not _ACT_EVENT.fullmatch(event):
        raise ValueError(f"Tên event không hợp lệ: {event!r}")
    Exercise.require_tool("act", ACT_MIN_VERSION)
    Exercise.require_tool("git")
    Exercise.require_image(ACT_IMAGE, hint=f"Image runner do track tự build một lần. Từ gốc repo chạy: {ACT_IMAGE_BUILD} "
                           "(xem module 07, mục 0. Cài đặt)")
    run_id = uuid.uuid4().hex[:8]
    root = Path(tempfile.mkdtemp(prefix=f"{DOCKER_PREFIX}{run_id}-act-"))
    try:
        repo = _act_repo(Path(workflow_dir), root, run_id)
        home = root / "home"
        home.mkdir()
        argv = _act_command(repo, run_id, event=event, job=job, env=env, secret_names=list(secrets)) + _act_guarded_stubs(repo, root)
        act_env = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": str(home), "LANG": "C.UTF-8",
                   "LC_ALL": "C.UTF-8", "DOCKER_HOST": _act_docker_host(), **secrets}
        stdout, stderr, returncode, timed_out = _act_execute(argv, repo, act_env, run_id, timeout)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    for value in secrets.values():
        stdout, stderr = stdout.replace(value, "***"), stderr.replace(value, "***")
    result = subprocess.CompletedProcess(argv, returncode, stdout, stderr)
    if timed_out:
        pytest.fail(f"Workflow chạy quá {timeout:g} giây nên bị dừng; container của lần chạy đã được dọn. Output cuối:\n{_output_tail(result)}")
    missing = _ACT_CLONE_FAILED.search(f"{stdout}\n{stderr}")
    if missing and returncode != 0:
        pytest.skip(
            f"act chưa có action {missing.group(1)} trong cache {act_cache_dir()} và không tải được từ GitHub (mất mạng?). "
            "Chạy lại test một lần khi có mạng; sau đó chấm offline được."
        )
    return result


TOFU_VERSION = "1.13.2"
TOFU_MIN_VERSION = "1.10"
TOFU_AWS_PROVIDER = "6.12.0"
TOFU_TIMEOUT = 300
TOFU_REGION = "us-east-1"
LOCALSTACK_DEVOPS_START = "docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops"
_TOFU_PREFIX = re.compile(rf"{DOCKER_PREFIX}[a-z0-9]{{6,}}")
_TOFU_NETWORK_ERRORS = re.compile(
    r"could not connect to|failed to request discovery document|no such host|i/o timeout|connection refused|connection reset"
    r"|TLS handshake timeout|network is unreachable|Temporary failure in name resolution|server misbehaving"
    r"|context deadline exceeded|proxyconnect",
    re.I,
)
_TOFU_COPY_IGNORE = (*_COPY_IGNORE, ".terraform", "terraform.tfstate", "terraform.tfstate.backup", ".terraform.tfstate.lock.info")
_BLACKHOLE: socket.socket | None = None


def tofu_plugin_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "devops-track" / "tofu-plugins"


def localstack_devops_endpoint() -> str:
    host = os.environ.get(SERVICES["localstack-devops"][0], SERVICES["localstack-devops"][1])
    return f"http://{'127.0.0.1' if host == 'localhost' else host}:{_port('localstack-devops')}"


def _localstack_devops_checked() -> str:
    if _port("localstack-devops") == _port("localstack"):
        raise RuntimeError(
            f"Cổng localstack-devops ({_port('localstack-devops')}) trùng cổng localstack của track DE; từ chối đụng vào "
            "LocalStack của DE. Đổi LOCALSTACK_DEVOPS_PORT trong setup/.env")
    return localstack_devops_endpoint()


def _localstack_health(endpoint: str) -> dict | None:
    import json
    import urllib.request

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"{endpoint}/_localstack/health", timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None


def _blackhole_proxy() -> str:
    """Cổng loopback đã bind nhưng không listen (giữ suốt phiên pytest): mọi kết nối tới đó bị từ chối ngay."""
    global _BLACKHOLE
    if _BLACKHOLE is None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        _BLACKHOLE = sock
    return f"http://127.0.0.1:{_BLACKHOLE.getsockname()[1]}"


def tofu_failed_on_network(output: str) -> bool:
    return bool(_TOFU_NETWORK_ERRORS.search(output))


def tofu_env(home: Path, *, prefix: str, endpoint: str | None = None, fetch: bool = False) -> dict[str, str]:
    """Env dựng từ đầu cho `tofu` trong sandbox: `HOME` tạm, thông tin đăng nhập giả, endpoint LocalStack riêng của DevOps.

    Không bao giờ ra AWS thật: `AWS_ENDPOINT_URL` (provider AWS và backend s3 đều đọc) trỏ mọi service về LocalStack nên
    provider không khai báo endpoint vẫn gọi LocalStack; mọi request không tới loopback (kể cả endpoint AWS thật ghi thẳng
    trong `endpoints {}`) đi qua proxy chết `HTTPS_PROXY` và bị từ chối trước cả bước tra DNS.

    Provider lấy offline: tệp CLI config sinh trong `home` chỉ cài từ `filesystem_mirror` ở `tofu_plugin_dir()` (OpenTofu
    tạo symlink, không chép). `fetch=True` là env của bước tải lần đầu: có mạng, không proxy, `TF_PLUGIN_CACHE_DIR` và
    `plugin_cache_dir` cùng thư mục đó (cache của OpenTofu có đúng bố cục của mirror dạng unpacked).
    """
    home = Path(home)
    plugins = tofu_plugin_dir()
    plugins.mkdir(parents=True, exist_ok=True)
    endpoint = endpoint or localstack_devops_endpoint()
    config_dir = home / ".devops-tofu"
    config_dir.mkdir(parents=True, exist_ok=True)
    if fetch:
        config = config_dir / "fetch.tfrc"
        config.write_text(f'disable_checkpoint = true\nplugin_cache_dir = "{plugins}"\n', encoding="utf-8")
    else:
        config = config_dir / "cli.tfrc"
        config.write_text(
            f'disable_checkpoint = true\nprovider_installation {{\n  filesystem_mirror {{\n    path = "{plugins}"\n  }}\n}}\n',
            encoding="utf-8")
    env = {
        "HOME": str(home),
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_REGION": TOFU_REGION,
        "AWS_CONFIG_FILE": "/dev/null",
        "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
        "AWS_EC2_METADATA_DISABLED": "true",
        "AWS_ENDPOINT_URL": endpoint,
        "TF_CLI_CONFIG_FILE": str(config),
        "TF_IN_AUTOMATION": "1",
        "TF_INPUT": "0",
        "CHECKPOINT_DISABLE": "1",
        "TF_VAR_prefix": prefix,
    }
    if fetch:
        env["TF_PLUGIN_CACHE_DIR"] = str(plugins)
        return env
    proxy = _blackhole_proxy()
    no_proxy = ",".join(dict.fromkeys(["127.0.0.1", "localhost", "::1", urlsplit(endpoint).hostname or "127.0.0.1"]))
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        env[key] = proxy
    env["NO_PROXY"] = env["no_proxy"] = no_proxy
    return env


def localstack_sweep(prefix: str) -> list[str]:
    """Xoá trên `localstack-devops` (không bao giờ trên `localstack` của DE) mọi bucket S3, bảng DynamoDB, IAM role và IAM
    policy có tên bắt đầu bằng `prefix` (`devops-ex-<id>`); trả danh sách `loại:tên` đã xoá."""
    if not _TOFU_PREFIX.fullmatch(prefix):
        raise ValueError(f"Tiền tố {prefix!r} quá rộng; chỉ nhận devops-ex-<id> của một lab")
    endpoint = _localstack_devops_checked()
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    options = {"endpoint_url": endpoint, "region_name": TOFU_REGION, "aws_access_key_id": "test", "aws_secret_access_key": "test",
               "config": Config(connect_timeout=3, read_timeout=30, retries={"max_attempts": 2}, proxies={})}
    removed: list[str] = []
    errors = (BotoCoreError, ClientError)

    s3 = boto3.client("s3", **options)
    try:
        names = [b["Name"] for b in s3.list_buckets().get("Buckets", []) if b["Name"].startswith(prefix)]
    except errors:
        names = []
    for name in names:
        try:
            for page in s3.get_paginator("list_object_versions").paginate(Bucket=name):
                objects = [{"Key": o["Key"], "VersionId": o["VersionId"]} for o in page.get("Versions", []) + page.get("DeleteMarkers", [])]
                if objects:
                    s3.delete_objects(Bucket=name, Delete={"Objects": objects, "Quiet": True})
            s3.delete_bucket(Bucket=name)
            removed.append(f"s3:{name}")
        except errors:
            pass

    dynamodb = boto3.client("dynamodb", **options)
    try:
        tables = [t for page in dynamodb.get_paginator("list_tables").paginate() for t in page.get("TableNames", []) if t.startswith(prefix)]
    except errors:
        tables = []
    for name in tables:
        try:
            dynamodb.delete_table(TableName=name)
            removed.append(f"dynamodb:{name}")
        except errors:
            pass

    iam = boto3.client("iam", **options)
    try:
        roles = [r["RoleName"] for page in iam.get_paginator("list_roles").paginate() for r in page.get("Roles", [])
                 if r["RoleName"].startswith(prefix)]
    except errors:
        roles = []
    for name in roles:
        try:
            for policy in iam.list_attached_role_policies(RoleName=name).get("AttachedPolicies", []):
                iam.detach_role_policy(RoleName=name, PolicyArn=policy["PolicyArn"])
            for policy in iam.list_role_policies(RoleName=name).get("PolicyNames", []):
                iam.delete_role_policy(RoleName=name, PolicyName=policy)
            for profile in iam.list_instance_profiles_for_role(RoleName=name).get("InstanceProfiles", []):
                iam.remove_role_from_instance_profile(InstanceProfileName=profile["InstanceProfileName"], RoleName=name)
            iam.delete_role(RoleName=name)
            removed.append(f"iam-role:{name}")
        except errors:
            pass
    try:
        policies = [p for page in iam.get_paginator("list_policies").paginate(Scope="Local") for p in page.get("Policies", [])
                    if p["PolicyName"].startswith(prefix)]
    except errors:
        policies = []
    for policy in policies:
        try:
            for version in iam.list_policy_versions(PolicyArn=policy["Arn"]).get("Versions", []):
                if not version["IsDefaultVersion"]:
                    iam.delete_policy_version(PolicyArn=policy["Arn"], VersionId=version["VersionId"])
            iam.delete_policy(PolicyArn=policy["Arn"])
            removed.append(f"iam-policy:{policy['PolicyName']}")
        except errors:
            pass
    return removed


class TofuLab:
    """Thư mục làm việc OpenTofu riêng của một test. Chỉ dùng bằng `with TofuLab(thư_mục_cấu_hình) as lab:` (không truyền
    thư mục thì bắt đầu rỗng, ghi tệp bằng `lab.write`).

    Cấu hình được chép vào thư mục tạm (bỏ `.terraform`, state), `init/plan/apply/output/state/destroy` chạy `tofu` qua
    `run_sandboxed` với env `tofu_env` (endpoint `localstack-devops`, không ra AWS thật). Tên tài nguyên dùng
    `var.prefix` = `lab.prefix` (`devops-ex-<id>`). `close()` luôn chạy `destroy -auto-approve -lock=false`, kể cả khi lỗi
    hay Ctrl-C, rồi `localstack_sweep(lab.prefix)` xoá tài nguyên mồ côi (state mất khi apply bị ngắt) và xoá thư mục tạm.

    `init` cài provider offline từ mirror `tofu_plugin_dir()`; thiếu provider thì tải một lần (`tofu init -backend=false`
    có mạng, ghi vào cùng thư mục) rồi init offline lại; không tải được vì mạng thì skip. `endpoint=` chỉ dành cho test
    của testkit (server giả): khi đó không cần LocalStack và không sweep.
    """

    def __init__(self, source: Path | None = None, *, endpoint: str | None = None, timeout: float = TOFU_TIMEOUT) -> None:
        self.id = uuid.uuid4().hex[:8]
        self.prefix = f"{DOCKER_PREFIX}{self.id}"
        self.source = Path(source) if source is not None else None
        self.endpoint = endpoint
        self.timeout = timeout
        self.root: Path | None = None
        self.home: Path | None = None
        self.workdir: Path | None = None
        self.env: dict[str, str] = {}
        self.destroy_result: subprocess.CompletedProcess | None = None
        self.swept: list[str] = []
        self._sweep = endpoint is None
        self._entered = False

    def __enter__(self) -> "TofuLab":
        self._entered = True
        try:
            self._open()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _open(self) -> None:
        Exercise.require_tool("tofu", TOFU_MIN_VERSION)
        reason = sandbox_ready()
        if reason:
            pytest.skip(SANDBOX_SKIP.format(reason=reason))
        if self.endpoint is None:
            self.endpoint = Exercise.require_localstack_devops()
        self.root = Path(tempfile.mkdtemp(prefix=f"{self.prefix}-"))
        self.home = self.root / "home"
        self.home.mkdir()
        self.workdir = self.root / "work"
        if self.source is not None:
            shutil.copytree(self.source, self.workdir, ignore=shutil.ignore_patterns(*_TOFU_COPY_IGNORE))
        else:
            self.workdir.mkdir()
        self.env = tofu_env(self.home, prefix=self.prefix, endpoint=self.endpoint)

    def _require_entered(self) -> None:
        if not self._entered or self.workdir is None:
            raise RuntimeError("Dùng TofuLab bằng `with TofuLab(...) as lab:` để tài nguyên luôn được destroy")

    def _execute(self, args: list[str], env: dict[str, str], writable: list[Path], timeout: float | None) -> subprocess.CompletedProcess:
        limit = timeout or self.timeout
        try:
            return run_sandboxed(["tofu", *args], writable=writable, cwd=self.workdir, env=env, timeout=limit)
        except subprocess.TimeoutExpired:
            pytest.fail(f"tofu {' '.join(args)} chạy quá {limit:.0f}s")

    @staticmethod
    def _failure(args, result: subprocess.CompletedProcess) -> str:
        output = f"{result.stdout}\n{result.stderr}".strip()
        return f"tofu {' '.join(args)} lỗi (mã {result.returncode}):\n{output[-DOCKER_LOG_CHARS:]}"

    def write(self, name: str, text: str) -> Path:
        self._require_entered()
        path = self.workdir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run(self, *args: str, check: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
        """Chạy `tofu <args>` trong sandbox (ví dụ `lab.run("validate")`, `lab.run("fmt", "-check")`)."""
        self._require_entered()
        result = self._execute(list(args), self.env, [self.workdir, self.home], timeout)
        if check and result.returncode != 0:
            pytest.fail(self._failure(args, result))
        return result

    def _fetch_env(self) -> dict[str, str]:
        return tofu_env(self.home, prefix=self.prefix, endpoint=self.endpoint, fetch=True)

    def _fetch(self) -> None:
        args = ["init", "-backend=false", "-input=false"]
        result = self._execute(args, self._fetch_env(), [self.workdir, self.home, tofu_plugin_dir()], self.timeout)
        if result.returncode == 0:
            return
        output = f"{result.stdout}\n{result.stderr}"
        if tofu_failed_on_network(output):
            last = next((line.strip() for line in reversed(output.splitlines()) if line.strip()), "")
            pytest.skip(
                f"Provider chưa có trong {tofu_plugin_dir()} và không tải được: lần đầu cần mạng để tải provider, sau đó "
                f"test chạy offline. Có mạng rồi chạy lại test. Lỗi: {last}")
        pytest.fail(self._failure(args, result))

    def init(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        self._require_entered()
        argv = ["init", "-input=false", *args]
        result = self.run(*argv, check=False)
        if result.returncode != 0:
            self._fetch()
            result = self.run(*argv, check=False)
        if check and result.returncode != 0:
            pytest.fail(self._failure(argv, result))
        return result

    def plan(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """`-detailed-exitcode` thì mã 2 (có thay đổi) cũng tính là thành công."""
        result = self.run("plan", "-input=false", *args, check=False)
        ok = {0, 2} if "-detailed-exitcode" in args else {0}
        if check and result.returncode not in ok:
            pytest.fail(self._failure(["plan", *args], result))
        return result

    def apply(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return self.run("apply", "-auto-approve", "-input=false", *args, check=check)

    def output(self, name: str | None = None) -> Any:
        """Không có `name`: dict tên output -> giá trị; có `name`: giá trị của output đó."""
        import json

        data = json.loads(self.run("output", "-json", *([name] if name else [])).stdout)
        return data if name else {key: value["value"] for key, value in data.items()}

    def state(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return self.run("state", *args, check=check)

    def destroy(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return self.run("destroy", "-auto-approve", "-input=false", *args, check=check)

    def close(self) -> None:
        outcome = (Exception, pytest.fail.Exception, pytest.skip.Exception)
        try:
            if self.workdir is not None and (self.workdir / ".terraform").is_dir():
                try:
                    self.destroy_result = self._execute(["destroy", "-auto-approve", "-input=false", "-lock=false"], self.env,
                                                        [self.workdir, self.home], self.timeout)
                except outcome:
                    self.destroy_result = None
        finally:
            try:
                if self._sweep and self.root is not None:
                    self.swept = localstack_sweep(self.prefix)
            except outcome:
                pass
            finally:
                if self.root is not None:
                    shutil.rmtree(self.root, ignore_errors=True)


# Dòng magic `%...`, shell `!...` hoặc gán từ shell `x = !ls`; nhóm 1 giữ thụt lề.
_MAGIC = re.compile(r"^(\s*)(?:[%!]|[\w, ]+=\s*[%!]).*$")


def _unique_name(path: Path) -> str:
    return "ex_" + "_".join(path.relative_to(ROOT).with_suffix("").parts).replace("-", "_")


def _load(path: Path, unique: str, execute, spec=None) -> ModuleType:
    if unique in sys.modules:
        return sys.modules[unique]
    module = importlib.util.module_from_spec(spec) if spec else ModuleType(unique)
    module.__file__ = str(path)
    sys.path.insert(0, str(path.parent))
    try:
        sys.modules[unique] = module
        execute(module)
    except BaseException:
        del sys.modules[unique]
        raise
    finally:
        sys.path.remove(str(path.parent))
    return module


_RECALC_CACHE: dict[tuple, Any] = {}  # (đường dẫn, mtime_ns, size) -> openpyxl workbook đã tính lại


def _open_workbook(path: Path, **kwargs):
    import openpyxl
    from openpyxl.utils.exceptions import InvalidFileException

    try:
        return openpyxl.load_workbook(path, **kwargs)
    except (zipfile.BadZipFile, InvalidFileException, KeyError, OSError) as exc:
        pytest.fail(f"Không mở được workbook {path.name} ({exc}) — lưu lại tệp/đóng Excel rồi chạy lại")


def _recalculate(path: Path):
    """Chép sang thư mục tạm, để LibreOffice tính lại rồi đọc giá trị (data_only)."""
    soffice = shutil.which("soffice")
    if not soffice:
        pytest.skip("Cần LibreOffice (soffice) để tính lại công thức")
    with tempfile.TemporaryDirectory(prefix="wbcalc-") as tmp:
        src = Path(tmp) / "in" / path.name
        out = Path(tmp) / "out"
        src.parent.mkdir()
        out.mkdir()
        shutil.copy(path, src)
        cmd = [
            soffice, f"-env:UserInstallation=file://{tmp}/profile", "--headless",
            "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", str(out), str(src),
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
        )
        try:
            _, stderr = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)  # soffice sinh process con (soffice.bin)
            _, stderr = proc.communicate()
            pytest.fail(f"LibreOffice quá 120 giây khi tính lại {path.name}. stderr: {stderr.strip()}")
        result = out / src.name
        if proc.returncode != 0 or not result.exists():
            pytest.fail(
                f"LibreOffice không tính lại được {path.name} (exit {proc.returncode}, "
                f"{'có' if result.exists() else 'không có'} tệp kết quả). stderr: {stderr.strip()}"
            )
        return _open_workbook(result, data_only=True)


class WorkbookView:
    """Workbook .xlsx của người học: đọc công thức (không cần LibreOffice) và giá trị đã tính lại."""

    def __init__(self, path: Path):
        self.path = path
        self._formulas = None

    def _formula_book(self):
        if self._formulas is None:
            self._formulas = _open_workbook(self.path)  # data_only=False: giữ chuỗi công thức
        return self._formulas

    @property
    def sheetnames(self) -> list[str]:
        return list(self._formula_book().sheetnames)

    def _sheet(self, book, sheet: str):
        if sheet not in book.sheetnames:
            pytest.fail(f"Workbook {self.path.name} không có sheet '{sheet}'. Có: {book.sheetnames}")
        return book[sheet]

    def formula(self, sheet: str, cell: str) -> str | None:
        """Chuỗi công thức (`"=SUM(A1:A3)"`) nếu ô là công thức, ngược lại `None` (ô gõ cứng hoặc trống)."""
        c = self._sheet(self._formula_book(), sheet)[cell]
        if c.data_type != "f":
            return None
        raw = c.value
        return raw if isinstance(raw, str) else getattr(raw, "text", None)  # ArrayFormula có .text

    def pivot_tables(self, sheet: str) -> list:
        """Pivot table của sheet; openpyxl chỉ giữ chúng ở thuộc tính riêng `_pivots`."""
        import openpyxl

        ws = self._sheet(self._formula_book(), sheet)
        if not hasattr(ws, "_pivots"):
            raise RuntimeError(f"openpyxl {openpyxl.__version__} không còn thuộc tính _pivots: cập nhật testkit.pivot_tables")
        return list(ws._pivots)

    def value(self, sheet: str, cell: str) -> Any:
        """Giá trị đã tính lại bằng LibreOffice (cache cấp module theo đường dẫn + mtime + size)."""
        stat = self.path.stat()
        key = (str(self.path.resolve()), stat.st_mtime_ns, stat.st_size)
        if key not in _RECALC_CACHE:
            _RECALC_CACHE[key] = _recalculate(self.path)
        return self._sheet(_RECALC_CACHE[key], sheet)[cell].value


class Exercise:
    """Một bài tập, xác định từ đường dẫn tệp test đang chạy."""

    def __init__(self, test_file: str):
        tests_dir = Path(test_file).resolve().parent
        self.dir = tests_dir.parent
        self.fixtures = tests_dir / "fixtures"
        parts = list(self.dir.parts)
        if use_solution():
            index = len(parts) - 1 - parts[::-1].index("exercises")
            parts[index] = "solutions"
            self.target = Path(*parts)
        else:
            self.target = self.dir / "starter"

    def path(self, name: str) -> Path:
        path = self.target / name
        if not path.exists() and use_solution() and "advanced" in self.dir.parts:
            pytest.skip("Bài advanced chỉ có SOLUTION.md (hướng làm + rubric), không có code lời giải để chạy")
        if not path.exists():
            pytest.fail(f"Không thấy tệp {path.relative_to(ROOT)}")
        return path

    def workbook(self, name: str) -> WorkbookView:
        """Workbook .xlsx của bài (starter hoặc lời giải với SOLUTION=1)."""
        return WorkbookView(self.path(name))

    def read(self, name: str) -> str:
        return self.path(name).read_text(encoding="utf-8")

    def module(self, name: str) -> ModuleType:
        path = self.path(name)
        spec = importlib.util.spec_from_file_location(_unique_name(path), path)
        return _load(path, spec.name, lambda module: spec.loader.exec_module(module), spec)

    def notebook(self, name: str) -> ModuleType:
        """Chạy các code cell của notebook (trừ cell gắn tag `explore`) rồi trả về như một module.

        Dòng magic/shell (`%time ...`, `!ls`, `x = !ls`) thành `pass`, cell magic (`%%bash`) bị bỏ,
        `display()` in ra như `print`. Output đã lưu trong notebook không ảnh hưởng. Lỗi được báo theo
        cell: `analysis.ipynb[cell 5]`, dòng tính trong cell.
        """
        import nbformat

        path = self.path(name)
        book = nbformat.read(path, as_version=4)
        cells = []
        for number, cell in enumerate(book.cells, start=1):
            if cell.cell_type != "code" or "explore" in cell.get("metadata", {}).get("tags", []):
                continue
            if cell.source.lstrip().startswith("%%"):
                continue
            source = "\n".join(_MAGIC.sub(r"\1pass", line) for line in cell.source.splitlines()) + "\n"
            filename = f"{path}[cell {number}]"
            linecache.cache[filename] = (len(source), None, source.splitlines(keepends=True), filename)
            cells.append(compile(source, filename, "exec"))
        os.environ.setdefault("MPLBACKEND", "Agg")

        def execute(module: ModuleType) -> None:
            module.__dict__.setdefault("display", print)
            for code in cells:
                exec(code, module.__dict__)

        return _load(path, _unique_name(path), execute)

    @staticmethod
    def dataset(name: str) -> Path:
        """Thư mục bộ dữ liệu thật `data/raw/<name>/`; skip test nếu chưa tải."""
        path = ROOT / "data" / "raw" / name
        if not path.is_dir() or not any(path.iterdir()):
            pytest.skip(f"Chưa tải bộ {name}. Chạy: uv run python data/download_dataset.py {name}")
        return path

    @staticmethod
    def require_service(name: str) -> None:
        if not service_up(name):
            pytest.skip(
                f"Dịch vụ {name} chưa chạy. Bật bằng: docker compose -f setup/docker-compose.yml up -d {name}"
            )

    @staticmethod
    def require_registry() -> str:
        """Skip khi registry local (service `registry`, profile `devops`) chưa chạy hoặc cổng của nó là server khác; trả
        `host:cổng` để gắn vào tên image. Test push lên đây dùng `DockerLab.push` (tiền tố `devops-ex-<id>/`, xoá khi xong)."""
        start = "docker compose -f setup/docker-compose.yml --profile devops up -d registry"
        if not service_up("registry"):
            pytest.skip(f"Registry local chưa chạy. Bật bằng: {start}")
        status, headers = _registry_request("GET", "/v2/")
        if status != 200 or not headers.get("docker-distribution-api-version", "").startswith("registry/2"):
            pytest.skip(
                f"Cổng {_port('registry')} đang mở nhưng không phải registry Docker (GET /v2/ trả {status}). Đổi "
                f"DEVOPS_REGISTRY_PORT trong setup/.env rồi chạy: {start}"
            )
        return registry_address()

    @staticmethod
    def require_localstack_devops() -> str:
        """Skip khi `localstack-devops` (profile `devops`) chưa chạy, cổng của nó trùng `localstack` của DE, hoặc cổng đó là
        server khác (LocalStack của DE bật S3/IAM/STS nhưng tắt DynamoDB); trả endpoint. Test IaC dùng qua `TofuLab`."""
        if _port("localstack-devops") == _port("localstack"):
            pytest.skip(
                f"LOCALSTACK_DEVOPS_PORT ({_port('localstack-devops')}) trùng LOCALSTACK_PORT của track DE; bài DevOps không "
                "dùng LocalStack của DE. Đổi LOCALSTACK_DEVOPS_PORT trong setup/.env")
        endpoint = localstack_devops_endpoint()
        if not service_up("localstack-devops"):
            pytest.skip(f"LocalStack của track DevOps chưa chạy. Bật bằng: {LOCALSTACK_DEVOPS_START}")
        services = (_localstack_health(endpoint) or {}).get("services", {})
        if any(services.get(name) in (None, "disabled") for name in ("s3", "iam", "sts", "dynamodb")):
            pytest.skip(
                f"Cổng {_port('localstack-devops')} đang mở nhưng không phải localstack-devops (thiếu S3, IAM, STS hay "
                f"DynamoDB). Đổi LOCALSTACK_DEVOPS_PORT trong setup/.env rồi chạy: {LOCALSTACK_DEVOPS_START}")
        return endpoint

    @staticmethod
    def require_tool(name: str, min_version: str | None = None) -> None:
        if not shutil.which(name):
            pytest.skip(f"Chưa cài {name}. Xem setup/DEVOPS-TOOLS.md")
        if min_version:
            have = tool_version(name)
            need = tuple(int(part) for part in min_version.split("."))
            if have is None:
                command = " ".join([name, *TOOL_VERSION_ARGS.get(name, ["--version"])])
                pytest.skip(
                    f"Không đọc được phiên bản của {name} (bài này cần từ {min_version}). Chạy `{command}` để xem; "
                    "có thể bản cài bị hỏng hoặc không phải bản chính thức. Xem setup/DEVOPS-TOOLS.md"
                )
            if not version_at_least(have, need):
                shown = ".".join(map(str, have))
                pytest.skip(f"{name} {shown} cũ hơn {min_version} cần cho bài này. Xem setup/DEVOPS-TOOLS.md")
        if name == "docker" and not docker_ready():
            pytest.skip("Docker daemon chưa chạy hoặc user chưa có quyền dùng docker")

    @staticmethod
    def require_image(image: str, hint: str | None = None) -> None:
        Exercise.require_tool("docker")
        if _docker("image", "inspect", image).returncode != 0:
            pytest.skip(f"Chưa có image {image}. {hint or f'Tải bằng: docker pull {image}'}")

    @staticmethod
    def require_cluster(name: str = "devops-lab") -> None:
        Exercise.require_tool("kind")
        result = _run_tool(["kind", "get", "clusters"])
        if result is None or name not in result.stdout.split():
            pytest.skip(f"Chưa có cluster kind {name}. Xem setup/DEVOPS-TOOLS.md")
