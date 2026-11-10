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
    ex.require_cluster()                    # bài DevOps: skip nếu Docker tắt, chưa có cluster kind devops-lab, node dừng hay API chưa sẵn sàng
    ex.require_image("nginx:1.30.6-alpine") # bài DevOps: skip nếu image Docker chưa pull
    with DockerLab() as lab: lab.start("web", "nginx:1.30.6-alpine", ports=[80])  # dựng mọi thứ trong `with`
    tag = lab.build(ctx, "api"); project = lab.compose(ctx / "compose.yaml"); project.port("api", 8000)  # trong `with`
    run_sandboxed(cmd, writable=[tmp_path], cwd=tmp_path, env={...})  # bài DevOps: chạy script trong bwrap
    repo = GitRepo(tmp_path / "repo", tmp_path / "home", writable=[tmp_path]); repo.out("log"); repo.taint()  # bài git
    result = act_run(project_dir, job="build"); act_job_results(result) == {"build": True}  # bài CI: workflow chạy bằng act
    registry = ex.require_registry(); ref = lab.push(tag, "api")  # registry local, close() xoá manifest đã push
    with TofuLab(ex.path("infra")) as lab: lab.init(); lab.apply(); lab.output("bucket")  # bài IaC: tofu trong sandbox, LocalStack riêng, close() destroy
    with AnsibleLab(["worker-1"]) as lab: run = lab.playbook("site.yml", cwd=lab.stage(ex.target)); run.changed  # bài Ansible: target SSH trong container
    with KubeLab() as lab: lab.apply_learner(ex.path("k8s")); lab.kubectl("get", "deploy", "api", "-o", "json")  # bài Kubernetes: namespace riêng trên devops-lab
    kind_node_exec("devops-lab-control-plane", "etcdctl", "version")  # lệnh cố định của testkit trong node kind, argv không qua shell
    key, public = age_keypair(tmp_path / "keys"); env = sops_env(tmp_path / "home", key)  # bài SOPS: sops chạy trong run_sandboxed
    ex.require_vault_devops(); env = vault_env(VAULT_DEV_TOKEN, tmp_path / "vault-home")  # bài Vault: vault CLI chạy trong run_sandboxed, Vault dev của lab
"""

from __future__ import annotations

import atexit
import importlib.util
import json
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
    "vault-devops": ("DEVOPS_VAULT_HOST", "localhost", "DEVOPS_VAULT_PORT", 18200),
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
    "sops": ["--version", "--disable-version-check"],
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


def _run_tool(args: list[str], env: dict[str, str] | None = None, cwd: str | None = None) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10, env=env, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired):
        return None


def tool_version(name: str) -> tuple[int, ...] | None:
    """Phiên bản của công cụ. Lệnh `ansible-*` chạy với `HOME` và thư mục làm việc tạm, `ANSIBLE_CONFIG=/dev/null`: không đọc
    `ansible.cfg` của người học, không tạo `~/.ansible`."""
    if not shutil.which(name):
        return None
    argv = [name, *TOOL_VERSION_ARGS.get(name, ["--version"])]
    if name.startswith("ansible"):
        with tempfile.TemporaryDirectory(prefix="devops-ex-version-") as home:
            env = {"PATH": os.environ.get("PATH", ""), "HOME": home, "LANG": "C.UTF-8", "ANSIBLE_CONFIG": os.devnull,
                   "ANSIBLE_HOME": f"{home}/.ansible", "ANSIBLE_LOCAL_TEMP": f"{home}/tmp"}
            result = _run_tool(argv, env=env, cwd=home)
    else:
        result = _run_tool(argv)
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


_ANONYMOUS_VOLUME = re.compile(r"[0-9a-f]{64}")
_ANONYMOUS_LABEL = "com.docker.volume.anonymous"
_VOLUME_MOUNTS = '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}} {{end}}{{end}}'


def _anonymous_volumes(names: list[str]) -> list[str]:
    """Volume ẩn danh (tên 64 ký tự hex, sinh từ `VOLUME` của image) đang gắn vào các container `names`."""
    if not names:
        return []
    found = _docker("inspect", "--format", _VOLUME_MOUNTS, *names).stdout.split()
    return list(dict.fromkeys(v for v in found if _ANONYMOUS_VOLUME.fullmatch(v)))


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
                 pids_limit: int = DOCKER_PIDS_LIMIT, user: str | None = None, workdir: str | None = None) -> list[str]:
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
        if user:
            args += ["--user", user]
        if workdir:
            args += ["--workdir", workdir]
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
            _docker("rm", "-f", "-v", name)
            if not any(text in result.stderr for text in _PORT_TAKEN):
                break
        pytest.fail(f"docker run {alias} ({image}) lỗi: {result.stderr.strip()}")

    def run_once(self, alias: str, image: str, *command: str, mounts=(), entrypoint=None, timeout: float = 60,
                 memory: str = DOCKER_MEMORY, pids_limit: int = DOCKER_PIDS_LIMIT, user: str | None = None,
                 workdir: str | None = None) -> subprocess.CompletedProcess:
        """Chạy container tới khi xong (vd. `nginx -t`) và trả kết quả; container vẫn được dọn nếu quá giờ."""
        self._require_entered()
        self._track(alias)
        args = self.run_args(alias, image, *command, detach=False, mounts=mounts, entrypoint=entrypoint, memory=memory,
                             pids_limit=pids_limit, user=user, workdir=workdir)
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
        try:
            volumes = _anonymous_volumes(self.names)
        except (OSError, subprocess.TimeoutExpired):
            volumes = []
        for name in self.names:
            try:
                _docker("rm", "-f", "-v", name)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if volumes:
            try:
                anonymous = set(_docker("volume", "ls", "-q", "-f", f"label={_ANONYMOUS_LABEL}").stdout.split())
                volumes = [v for v in volumes if v in anonymous]
                if volumes:
                    _docker("volume", "rm", *volumes)
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
    ".cache/devops-track/kube", ".config/sops", ".gnupg", ".vault-token",
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


def _resolv_conf_flags() -> list[str]:
    """/etc/resolv.conf của systemd-resolved là symlink vào /run (bị tmpfs che): bind lại đúng một tệp đích, chỉ đọc, để DNS
    chạy trong sandbox (mạng không tách). Không bind thư mục /run/systemd/resolve hay socket nào."""
    target = Path("/etc/resolv.conf").resolve()
    if target.is_relative_to("/run") and target.is_file():
        return ["--ro-bind", str(target), str(target)]
    return []


def _base_flags(bwrap: str) -> list[str]:
    """Cờ chung cho lần thử và lần chạy thật: / chỉ đọc, /tmp và /run là tmpfs rỗng (che socket docker, D-Bus), thư mục
    thông tin đăng nhập bị phủ tmpfs, tệp thông tin đăng nhập bị thay bằng /dev/null."""
    args = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", "/run"]
    args += _resolv_conf_flags()
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
    base = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": str(home), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "PYTHONNOUSERSITE": "1"}
    base.update({k: v for k, v in env.items() if not _UNSAFE_ENV.match(k)})
    return base


def _hidden_by_tmpfs() -> list[Path]:
    hidden = (Path("/tmp"), Path("/run"))
    candidates = {ROOT, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), Path(sys.executable).resolve().parent}
    return sorted(p for p in candidates if any(p.is_relative_to(h) and p != h for h in hidden))


def sandbox_command(cmd: list, *, writable: list[Path], cwd: Path, env: dict[str, str], readonly=()) -> list[str]:
    """argv chạy `cmd` trong bwrap: / chỉ đọc, /tmp và /run là tmpfs rỗng, `CREDENTIAL_PATHS` của home thật bị che, chỉ
    `writable` ghi được, môi trường dựng lại từ đầu. `readonly` là thư mục cần nhìn thấy nhưng không được ghi (cần khi nó
    nằm dưới /tmp hay /run, bị tmpfs che); mount sau tmpfs, trước `writable`.

    Mạng KHÔNG bị tách (không --unshare-net): test healthcheck cần gọi server giả trên loopback của máy. Chấp nhận được vì
    mô hình đe doạ là script viết sai vô tình phá dữ liệu, không phải mã độc; socket của docker và D-Bus vẫn bị che.
    """
    reason = sandbox_ready()
    if reason:
        pytest.skip(SANDBOX_SKIP.format(reason=reason))
    args = _base_flags(shutil.which("bwrap"))
    for path in _hidden_by_tmpfs():
        args += ["--ro-bind", str(path), str(path)]
    for path in readonly:
        real = str(Path(path).resolve())
        args += ["--ro-bind", real, real]
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
    readonly=(),
) -> subprocess.CompletedProcess:
    """Chạy lệnh của người học trong sandbox bwrap; skip (không bao giờ chạy trần) khi không có sandbox.

    Không tách mạng (xem `sandbox_command`): đủ cho mục tiêu chặn script lỗi xoá hay sửa tệp thật.
    """
    argv = sandbox_command(cmd, writable=writable, cwd=cwd, env=env, readonly=readonly)
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
ACT_DUMMY_GITHUB_TOKEN = "devops-ex-dummy-token"
ACT_GH_SHIM_MARKER = "gh-called"
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


def act_skipped_locally(condition) -> bool:
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
    if act_skipped_locally(step.get("if")):
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
                if not allowed and not act_skipped_locally(step.get("if")):
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
    return argv + ["-s", "GITHUB_TOKEN"]


def _act_gh_shim(root: Path) -> Path:
    """Thư mục đặt đầu `PATH` của act, chứa `gh` giả: chạy thì tạo `root/ACT_GH_SHIM_MARKER` rồi thoát 1, nên act (tìm `gh`
    bằng `exec.LookPath`) không bao giờ tới được `gh auth token` của máy."""
    import shlex

    shim = root / "gh-shim"
    shim.mkdir()
    gh = shim / "gh"
    gh.write_text(f"#!/bin/sh\n: > {shlex.quote(str(root / ACT_GH_SHIM_MARKER))}\nexit 1\n", encoding="utf-8")
    gh.chmod(0o755)
    return shim


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
    github_token: str | None = None,
) -> subprocess.CompletedProcess:
    """Chạy workflow GitHub Actions trong `workflow_dir/.github/workflows/` bằng `act` và trả CompletedProcess (kết quả từng
    job: `act_job_results`; giá trị gửi ra: `act_outputs`). Skip khi thiếu `act`, git hay image runner `ACT_IMAGE`.

    act chạy trên host (cần socket Docker nên không vào được bwrap) trên bản chép tạm của `workflow_dir` (bỏ `.git`,
    `.actrc`) thành repo git mới, với `name:` của mọi workflow đổi thành `devops-ex-<id>-<tên cũ>` để container, volume
    của act mang tên riêng của lần chạy. Env dựng từ đầu (`HOME` tạm nên không đọc `~/.actrc`, `~/.config/act`; không mang
    `GITHUB_TOKEN`, `GH_*`, `ACTIONS_*`, `AWS_*`, `DOCKER_*`, `DBUS_*`, `XDG_*` của máy; `DOCKER_HOST` lấy từ context Docker hiện tại); `.env`, `.secrets`,
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

    Luôn truyền secret `GITHUB_TOKEN` tường minh (`github_token`, mặc định `ACT_DUMMY_GITHUB_TOKEN`) nên act không bao giờ
    tới được token của `gh` trên máy (act 0.2.94 chạy `gh auth token` khi thiếu secret này); thêm vào đó `PATH` của act bắt
    đầu bằng một `gh` giả, act mà gọi nó thì fail.

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
    token = ACT_DUMMY_GITHUB_TOKEN if github_token is None else str(github_token)
    short = sorted(name for name, value in {**secrets, "GITHUB_TOKEN": token}.items() if len(value) < ACT_SECRET_MIN_LENGTH)
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
        path = f"{_act_gh_shim(root)}:{os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')}"
        act_env = {"PATH": path, "HOME": str(home), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "DOCKER_HOST": _act_docker_host(),
                   **secrets, "GITHUB_TOKEN": token}
        stdout, stderr, returncode, timed_out = _act_execute(argv, repo, act_env, run_id, timeout)
        gh_called = (root / ACT_GH_SHIM_MARKER).exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)
    for value in [*secrets.values(), token]:
        stdout, stderr = stdout.replace(value, "***"), stderr.replace(value, "***")
    result = subprocess.CompletedProcess(argv, returncode, stdout, stderr)
    if gh_called:
        pytest.fail("act đã gọi `gh` (định lấy token GitHub của máy); act_run phải luôn truyền GITHUB_TOKEN tường minh")
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
_TOFU_PREFIX = re.compile(rf"{DOCKER_PREFIX}[0-9a-f]{{8}}")
TOFU_PROVIDERS = {"hashicorp/aws": TOFU_AWS_PROVIDER}
TOFU_REGISTRY = "registry.opentofu.org"
_TOFU_FORBIDDEN_ARGS = ("no_proxy", "http_proxy", "https_proxy", "custom_ca_bundle")
_TOFU_FORBIDDEN = re.compile(rf'\b({'|'.join(_TOFU_FORBIDDEN_ARGS)})\b"?\s*[=:]')
_TOFU_JSON_ESCAPE = re.compile(r"\\u[0-9a-fA-F]{4}")
_TOFU_LOCK_ENTRY = re.compile(r'provider\s+"([^"]+)"\s*\{[^}]*?\bversion\s*=\s*"([^"]+)"', re.S)
_TOFU_VERSION_MISMATCH = re.compile(r"no available releases match|does not match|locked provider|doesn't match", re.I)
_TOFU_NETWORK_ERRORS = re.compile(
    r"could not connect to|failed to request discovery document|no such host|i/o timeout|connection refused|connection reset"
    r"|TLS handshake timeout|network is unreachable|Temporary failure in name resolution|server misbehaving"
    r"|context deadline exceeded|proxyconnect",
    re.I,
)
_TOFU_CONFIG_SUFFIXES = (".tf", ".tofu", ".tf.json", ".tofu.json", ".tftest.hcl", ".tofutest.hcl", ".tftest.json",
                         ".tofutest.json")
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
        atexit.register(sock.close)
        _BLACKHOLE = sock
    return f"http://127.0.0.1:{_BLACKHOLE.getsockname()[1]}"


def _tofu_platform() -> str:
    import platform

    machine = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower(), platform.machine())
    return f"{platform.system().lower()}_{machine}"


def tofu_providers_present() -> bool:
    """Mirror `tofu_plugin_dir()` đã có đúng các bản trong `TOFU_PROVIDERS` cho máy này chưa."""
    root = tofu_plugin_dir() / TOFU_REGISTRY
    return all(any((root / source / version / _tofu_platform()).glob("terraform-provider-*")) for source, version in TOFU_PROVIDERS.items())


def _tofu_fetch_env(home: Path) -> dict[str, str]:
    return tofu_env(home, prefix=f"{DOCKER_PREFIX}00000000", fetch=True)


def tofu_fetch_providers() -> None:
    """Tải một lần đúng các provider ghim trong `TOFU_PROVIDERS` vào `tofu_plugin_dir()`. Cấu hình do testkit viết (không
    bao giờ dùng HCL của người học, nên ràng buộc lỏng như `~> 6.0` không kéo bản mới về), chạy `tofu init -backend=false`
    trong sandbox với `plugin_cache_dir` là thư mục đó (bố cục cache trùng bố cục mirror unpacked). Lỗi mạng thì skip."""
    plugins = tofu_plugin_dir()
    plugins.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=f"{DOCKER_PREFIX}tofu-fetch-"))
    try:
        work, home = root / "work", root / "home"
        work.mkdir()
        home.mkdir()
        lines = [f'    {source.split("/")[1]} = {{ source = "{source}", version = "= {version}" }}' for source, version in TOFU_PROVIDERS.items()]
        (work / "main.tf").write_text("terraform {\n  required_providers {\n" + "\n".join(lines) + "\n  }\n}\n", encoding="utf-8")
        args = ["tofu", "init", "-backend=false", "-input=false"]
        try:
            result = run_sandboxed(args, writable=[root, plugins], cwd=work, env=_tofu_fetch_env(home), timeout=TOFU_TIMEOUT)
        except subprocess.TimeoutExpired:
            pytest.skip(f"Tải provider vào {plugins} quá {TOFU_TIMEOUT}s; kiểm tra mạng rồi chạy lại test")
        output = f"{result.stdout}\n{result.stderr}"
        if result.returncode != 0 and tofu_failed_on_network(output):
            last = next((line.strip() for line in reversed(output.splitlines()) if line.strip()), "")
            pytest.skip(
                f"Provider chưa có trong {plugins} và không tải được: lần đầu cần mạng để tải provider, sau đó test chạy "
                f"offline. Có mạng rồi chạy lại test. Lỗi: {last}")
        if result.returncode != 0 or not tofu_providers_present():
            pytest.fail(f"Tải provider {TOFU_PROVIDERS} vào {plugins} lỗi (mã {result.returncode}):\n{output.strip()[-DOCKER_LOG_CHARS:]}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _tofu_locked_versions(lock: Path) -> dict[str, str]:
    if not lock.is_file():
        return {}
    return dict(_TOFU_LOCK_ENTRY.findall(lock.read_text(encoding="utf-8")))


def _tofu_version_message() -> str:
    pins = ", ".join(f'{source} "{version}"' for source, version in TOFU_PROVIDERS.items())
    return (
        f"Provider phải đúng bản {pins} ({TOFU_AWS_PROVIDER}): LocalStack 4.4.0 của track chỉ chạy đúng tới bản này (từ 6.13 "
        "bảng DynamoDB kẹt khi tạo, bản mới hơn còn gọi S3 Control mà LocalStack không có). Đặt `version` trong "
        f'`required_providers` thành "{TOFU_AWS_PROVIDER}" hoặc ràng buộc cho phép bản này (ví dụ "~> 6.0"), và xoá '
        ".terraform.lock.hcl nếu nó khoá bản khác."
    )


def _tofu_json_keys(text: str) -> list[str]:
    keys = []

    def collect(pairs):
        keys.extend(key for key, _ in pairs)
        return dict(pairs)

    json.loads(text, object_pairs_hook=collect)
    return keys


def _tofu_json_problems(rel: Path, text: str) -> list[str]:
    found = []
    for match in _TOFU_JSON_ESCAPE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append(
            f"{rel}:{line}: escape `{match.group(0)}` bị từ chối: cấu hình JSON trong lab không được dùng escape `\\uXXXX` "
            "(ở khoá hay giá trị), vì OpenTofu giải mã nó và có thể ghép ra tên đối số bị cấm mà phép kiểm không thấy. Viết "
            "thẳng ký tự đó (tệp là UTF-8)")
    try:
        keys = _tofu_json_keys(text)
    except RecursionError:
        return [*found, f"{rel}: JSON lồng quá sâu: phép kiểm cấu hình không đọc hết được tệp này nên từ chối nó. Giảm độ "
                        "lồng của mảng/đối tượng rồi chạy lại"]
    except ValueError as error:
        return [*found, f"{rel}: JSON không hợp lệ ({error}): sửa cú pháp JSON rồi chạy lại; phép kiểm cấu hình không đọc "
                        "được tệp này nên từ chối nó"]
    for key in keys:
        if key.lower() in _TOFU_FORBIDDEN_ARGS:
            found.append(
                f"{rel}: khoá JSON `{key}` bị từ chối: test đặt proxy chặn mọi request không tới LocalStack để code không "
                f"bao giờ gọi AWS thật, đối số `{key.lower()}` mở đường vòng qua lớp đó. Xoá khoá này; LocalStack của "
                "track không cần proxy hay CA riêng")
    return found


def tofu_config_problems(root: Path) -> list[str]:
    """Đối số provider hay backend vô hiệu lớp chặn mạng của `tofu_env` (`no_proxy`, `http_proxy`, `https_proxy`,
    `custom_ca_bundle`) trong `*.tf`, `*.tofu`, tệp test `*.tftest.hcl`, `*.tofutest.hcl` và bản `.json` của chúng dưới
    `root` (bỏ `.terraform`). Quét văn bản thô, không bỏ chú thích: tên cấm theo sau bởi `=` hay `:` ở bất kỳ đâu đều bị
    từ chối. Tệp JSON còn bị cấm mọi escape `\\uXXXX`, phải parse được (lồng quá sâu cũng bị từ chối), và mọi khoá đã
    giải mã ở mọi độ sâu được so (không phân biệt hoa thường) với tên cấm."""
    root = Path(root)
    found = []
    for path in sorted(root.rglob("*")):
        if ".terraform" in path.relative_to(root).parts or not path.is_file():
            continue
        if not path.name.endswith(_TOFU_CONFIG_SUFFIXES):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.name.endswith(".json"):
            found.extend(_tofu_json_problems(path.relative_to(root), text))
        for match in _TOFU_FORBIDDEN.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            found.append(
                f"{path.relative_to(root)}:{line}: `{match.group(1)}` bị từ chối: test đặt proxy chặn mọi request không tới "
                "LocalStack để code không bao giờ gọi AWS thật, đối số này mở đường vòng qua lớp đó. Trong lab cấm hẳn "
                f"`{match.group(1)} =` (và khoá JSON), kể cả khi nằm trong chú thích hay chuỗi, để không mẹo chú thích hay "
                "heredoc nào lách được phép kiểm. Xoá dòng này; LocalStack của track không cần proxy hay CA riêng")
    return found


def _owned_by(name: str, prefix: str) -> bool:
    bare = name.removeprefix("alias/").lstrip("/")
    return bare == prefix or bare.startswith((f"{prefix}-", f"{prefix}/"))


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


def localstack_client(service: str):
    """Client boto3 cho `localstack-devops` (không bao giờ LocalStack của DE: cổng trùng thì RuntimeError trước khi tạo
    client), thông tin đăng nhập giả, không proxy, không đọc `~/.aws` hay biến `AWS_*` của người học. Test dùng nó để tạo
    trước tài nguyên (bucket backend, tài nguyên "tạo tay" để import, drift) và kiểm kết quả; đặt tên theo `lab.prefix` để
    `TofuLab.close()` sweep được."""
    endpoint = _localstack_devops_checked()
    import boto3
    from botocore.config import Config

    saved = {key: os.environ.pop(key) for key in list(os.environ) if key.startswith("AWS_")}
    os.environ.update({"AWS_CONFIG_FILE": "/dev/null", "AWS_SHARED_CREDENTIALS_FILE": "/dev/null"})
    try:
        session = boto3.session.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name=TOFU_REGION)
        return session.client(service, endpoint_url=endpoint,
                              config=Config(connect_timeout=3, read_timeout=30, retries={"max_attempts": 2}, proxies={}))
    finally:
        for key in ("AWS_CONFIG_FILE", "AWS_SHARED_CREDENTIALS_FILE"):
            os.environ.pop(key, None)
        os.environ.update(saved)


def localstack_sweep(prefix: str) -> list[str]:
    """Xoá trên `localstack-devops` (không bao giờ trên `localstack` của DE) mọi tài nguyên mang đúng tiền tố của một lab
    (`devops-ex-<8 hex>`): tên bằng tiền tố hoặc bắt đầu bằng `<tiền tố>-`/`<tiền tố>/` (bỏ `/` đầu và `alias/`). Gồm bucket
    S3 (mọi version), bảng DynamoDB, IAM role và policy, tham số SSM, secret của Secrets Manager (xoá ngay), alias KMS (kèm
    lên lịch xoá khoá khi không còn alias nào khác trỏ tới). Trả danh sách `loại:tên` đã xoá."""
    if not _TOFU_PREFIX.fullmatch(prefix):
        raise ValueError(f"Tiền tố {prefix!r} không phải devops-ex-<8 hex> của một lab")
    endpoint = _localstack_devops_checked()
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    options = {"endpoint_url": endpoint, "region_name": TOFU_REGION, "aws_access_key_id": "test", "aws_secret_access_key": "test",
               "config": Config(connect_timeout=3, read_timeout=30, retries={"max_attempts": 2}, proxies={})}
    errors = (BotoCoreError, ClientError)
    removed: list[str] = []

    def listed(client, operation: str, key: str, field: str | None, **kwargs) -> list:
        try:
            items = [item for page in client.get_paginator(operation).paginate(**kwargs) for item in page.get(key, [])]
        except errors:
            return []
        return [item for item in items if _owned_by(item[field] if field else item, prefix)]

    def attempt(label: str, *actions) -> bool:
        try:
            for action in actions:
                action()
        except errors:
            return False
        removed.append(label)
        return True

    s3 = boto3.client("s3", **options)
    try:
        buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", []) if _owned_by(b["Name"], prefix)]
    except errors:
        buckets = []

    def empty(name: str) -> None:
        for page in s3.get_paginator("list_object_versions").paginate(Bucket=name):
            objects = [{"Key": o["Key"], "VersionId": o["VersionId"]} for o in page.get("Versions", []) + page.get("DeleteMarkers", [])]
            if objects:
                s3.delete_objects(Bucket=name, Delete={"Objects": objects, "Quiet": True})

    for name in buckets:
        attempt(f"s3:{name}", lambda name=name: empty(name), lambda name=name: s3.delete_bucket(Bucket=name))

    dynamodb = boto3.client("dynamodb", **options)
    for name in listed(dynamodb, "list_tables", "TableNames", None):
        attempt(f"dynamodb:{name}", lambda name=name: dynamodb.delete_table(TableName=name))

    iam = boto3.client("iam", **options)

    def unhook(name: str) -> None:
        for policy in iam.list_attached_role_policies(RoleName=name).get("AttachedPolicies", []):
            iam.detach_role_policy(RoleName=name, PolicyArn=policy["PolicyArn"])
        for policy in iam.list_role_policies(RoleName=name).get("PolicyNames", []):
            iam.delete_role_policy(RoleName=name, PolicyName=policy)
        for profile in iam.list_instance_profiles_for_role(RoleName=name).get("InstanceProfiles", []):
            iam.remove_role_from_instance_profile(InstanceProfileName=profile["InstanceProfileName"], RoleName=name)

    for role in listed(iam, "list_roles", "Roles", "RoleName"):
        name = role["RoleName"]
        attempt(f"iam-role:{name}", lambda name=name: unhook(name), lambda name=name: iam.delete_role(RoleName=name))

    def drop_versions(arn: str) -> None:
        for version in iam.list_policy_versions(PolicyArn=arn).get("Versions", []):
            if not version["IsDefaultVersion"]:
                iam.delete_policy_version(PolicyArn=arn, VersionId=version["VersionId"])

    for policy in listed(iam, "list_policies", "Policies", "PolicyName", Scope="Local"):
        arn = policy["Arn"]
        attempt(f"iam-policy:{policy['PolicyName']}", lambda arn=arn: drop_versions(arn), lambda arn=arn: iam.delete_policy(PolicyArn=arn))

    ssm = boto3.client("ssm", **options)
    for parameter in listed(ssm, "describe_parameters", "Parameters", "Name"):
        name = parameter["Name"]
        attempt(f"ssm:{name}", lambda name=name: ssm.delete_parameter(Name=name))

    secrets = boto3.client("secretsmanager", **options)
    for secret in listed(secrets, "list_secrets", "SecretList", "Name"):
        name = secret["Name"]
        attempt(f"secretsmanager:{name}", lambda name=name: secrets.delete_secret(SecretId=name, ForceDeleteWithoutRecovery=True))

    kms = boto3.client("kms", **options)
    try:
        aliases = [a for page in kms.get_paginator("list_aliases").paginate() for a in page.get("Aliases", [])]
    except errors:
        aliases = []
    for alias in aliases:
        name, key = alias["AliasName"], alias.get("TargetKeyId")
        if not name.startswith("alias/") or not _owned_by(name, prefix):
            continue
        if not attempt(f"kms-alias:{name}", lambda name=name: kms.delete_alias(AliasName=name)):
            continue
        shared = any(other.get("TargetKeyId") == key and not _owned_by(other["AliasName"], prefix) for other in aliases)
        if key and not shared:
            try:
                kms.schedule_key_deletion(KeyId=key, PendingWindowInDays=7)
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

    `init` cài provider offline từ mirror `tofu_plugin_dir()`; mirror thiếu bản ghim thì `tofu_fetch_providers()` tải một
    lần bằng cấu hình của testkit (không phải HCL của người học); không tải được vì mạng thì skip. Sau `init`, lock file phải
    khoá đúng `TOFU_PROVIDERS`, khác thì fail kèm lý do. Mọi lệnh bị từ chối khi cấu hình có `no_proxy`, `http_proxy`,
    `https_proxy`, `custom_ca_bundle` (`tofu_config_problems`). `destroy` lúc đóng lỗi thì luôn có `UserWarning`, và test
    đang đạt sẽ fail (test đã lỗi thì giữ lỗi gốc). `endpoint=` chỉ dành cho test của testkit (server giả): khi đó không cần
    LocalStack và không sweep.
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
        self.destroy_error: str | None = None
        self._sweep = endpoint is None
        self._entered = False
        self._initialized = False

    def __enter__(self) -> "TofuLab":
        self._entered = True
        try:
            self._open()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, *exc) -> None:
        self.close()
        if exc_type is None and self.destroy_error:
            pytest.fail(self.destroy_error)

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

    def _writable(self) -> list[Path]:
        return [self.workdir, self.home]

    @staticmethod
    def _readonly() -> list[Path]:
        """Mirror luôn chỉ đọc với lệnh do người học điều khiển; bind lại để nhìn thấy cả khi nó nằm dưới /tmp hay /run."""
        plugins = tofu_plugin_dir()
        return [plugins] if plugins.is_dir() else []

    def _require_entered(self) -> None:
        if not self._entered or self.workdir is None:
            raise RuntimeError("Dùng TofuLab bằng `with TofuLab(...) as lab:` để tài nguyên luôn được destroy")

    def _execute(self, args: list[str], env: dict[str, str], writable: list[Path], timeout: float | None) -> subprocess.CompletedProcess:
        limit = timeout or self.timeout
        try:
            return run_sandboxed(["tofu", *args], writable=writable, readonly=self._readonly(), cwd=self.workdir, env=env,
                                 timeout=limit)
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
        problems = tofu_config_problems(self.workdir)
        if problems:
            pytest.fail("\n".join(problems))
        result = self._execute(list(args), self.env, self._writable(), timeout)
        if args and args[0] == "init" and result.returncode == 0:
            self._initialized = True
        if check and result.returncode != 0:
            pytest.fail(self._failure(args, result))
        return result

    def init(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        self._require_entered()
        problems = tofu_config_problems(self.workdir)
        if problems:
            pytest.fail("\n".join(problems))
        if not tofu_providers_present():
            tofu_fetch_providers()
        argv = ["init", "-input=false", *args]
        result = self.run(*argv, check=False)
        output = f"{result.stdout}\n{result.stderr}"
        if result.returncode != 0:
            if check:
                hint = _tofu_version_message() + "\n" if _TOFU_VERSION_MISMATCH.search(output) else ""
                pytest.fail(hint + self._failure(argv, result))
            return result
        pinned = {f"{TOFU_REGISTRY}/{source}": version for source, version in TOFU_PROVIDERS.items()}
        locked = _tofu_locked_versions(self.workdir / ".terraform.lock.hcl")
        wrong = {source: version for source, version in locked.items() if source in pinned and version != pinned[source]}
        if wrong:
            pytest.fail(f"{_tofu_version_message()}\nLock file đang khoá: {wrong}")
        return result

    def plan(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """`-detailed-exitcode` thì mã 2 (có thay đổi) cũng tính là thành công."""
        result = self.run("plan", "-input=false", *args, check=False)
        ok = {0, 2} if "-detailed-exitcode" in args else {0}
        if check and result.returncode not in ok:
            pytest.fail(self._failure(["plan", *args], result))
        return result

    def plan_json(self, *args: str) -> dict:
        """`plan -out` vào tệp tạm trong thư mục làm việc rồi `show -json` tệp đó; trả dict (`resource_changes`, mỗi mục có
        `change.actions`, `previous_address`, `change.importing`). Plan lỗi thì fail kèm output."""
        import json

        self._require_entered()
        name = f".devops-ex-{uuid.uuid4().hex[:8]}.tfplan"
        try:
            result = self.run("plan", "-input=false", f"-out={name}", *args, check=False)
            if result.returncode != 0:
                pytest.fail(self._failure(["plan", *args], result))
            return json.loads(self.run("show", "-json", name).stdout)
        finally:
            (self.workdir / name).unlink(missing_ok=True)

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
        import warnings

        outcome = (Exception, pytest.fail.Exception, pytest.skip.Exception)
        try:
            ready = self.workdir is not None and (self.workdir / ".terraform").is_dir()
            if ready and not tofu_config_problems(self.workdir):
                args = ["destroy", "-auto-approve", "-input=false", "-lock=false"]
                try:
                    self.destroy_result = self._execute(args, self.env, self._writable(), self.timeout)
                    if self.destroy_result.returncode != 0:
                        self.destroy_error = self._failure(args, self.destroy_result)
                except outcome as error:
                    self.destroy_error = f"tofu destroy lỗi: {error}"
                if self.destroy_error and self._initialized:
                    warnings.warn(f"{self.destroy_error}\nTài nguyên còn lại được sweep theo tiền tố {self.prefix}", UserWarning)
                else:
                    self.destroy_error = None
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


SOPS_VERSION = "3.13.3"
SOPS_MIN_VERSION = "3.9"
AGE_VERSION = "1.3.2"
AGE_MIN_VERSION = "1.2"
VAULT_VERSION = "2.2.1"
VAULT_IMAGE = f"hashicorp/vault:{VAULT_VERSION}@sha256:962a92876e168d68eaaa24b0b8b49bbce1cb63024060a67bba95cd158a366fc2"
VAULT_DEVOPS_START = "docker compose -f setup/docker-compose.yml --profile devops up -d --wait vault-devops"
VAULT_DEV_TOKEN = os.environ.get("DEVOPS_VAULT_TOKEN", "devops-lab-root")
_AGE_PUBLIC = re.compile(r"^# public key: (age1[0-9a-z]+)$", re.M)


def _key_outside(path: Path, outside) -> Path:
    real = Path(path).resolve()
    for root in (ROOT, *outside):
        if real.is_relative_to(Path(root).resolve()):
            raise ValueError(f"Khoá age phải nằm ngoài {root} (repo hay project của người học): {real}")
    return real


def sops_env(home: Path, key_file: Path, *, outside=()) -> dict[str, str]:
    """Env cho `sops` trong `run_sandboxed`: `HOME` và `XDG_CONFIG_HOME` tạm (không đọc `~/.config/sops`), `GNUPGHOME` là
    `home/.gnupg`, `SOPS_AGE_KEY_FILE` là khoá của lab; tạo `home`, `home/.config` và `home/.gnupg` (quyền 0700). Không mang
    `SOPS_*`, `AGE_*`, `GNUPGHOME` của máy. `key_file` nằm trong repo hay trong một thư mục của `outside` (project của người
    học), kể cả qua symlink hay `..`, thì ValueError. Khoá dưới /tmp (như `tmp_path`) bị tmpfs của sandbox che: truyền
    `readonly=[key_file.parent]` cho `run_sandboxed`."""
    home = Path(home).resolve()
    key = _key_outside(key_file, outside)
    (home / ".config").mkdir(parents=True, exist_ok=True)
    (home / ".gnupg").mkdir(mode=0o700, exist_ok=True)
    (home / ".gnupg").chmod(0o700)
    return {"HOME": str(home), "XDG_CONFIG_HOME": f"{home}/.config", "GNUPGHOME": f"{home}/.gnupg", "SOPS_AGE_KEY_FILE": str(key)}


def age_keypair(directory: Path, *, outside=()) -> tuple[Path, str]:
    """Sinh khoá age bằng `age-keygen -o` trong sandbox (chỉ `directory` ghi được); trả (đường dẫn khoá riêng, public key).
    `directory` nằm trong repo hay trong `outside` thì ValueError. Không bao giờ in khoá riêng."""
    directory = _key_outside(directory, outside)
    Exercise.require_tool("age-keygen", AGE_MIN_VERSION)
    directory.mkdir(parents=True, exist_ok=True)
    key = directory / "age-key.txt"
    if key.exists():
        raise ValueError(f"Đã có khoá {key}; dùng thư mục mới cho mỗi khoá")
    result = run_sandboxed(["age-keygen", "-o", str(key)], writable=[directory], cwd=directory, env={})
    found = _AGE_PUBLIC.search(key.read_text(encoding="utf-8")) if key.is_file() else None
    if result.returncode != 0 or found is None:
        pytest.fail(f"age-keygen lỗi (mã {result.returncode}): {result.stderr.strip()[-DOCKER_LOG_CHARS:]}")
    return key, found.group(1)


def vault_devops_address() -> str:
    host = os.environ.get(SERVICES["vault-devops"][0], SERVICES["vault-devops"][1])
    return f"http://{'127.0.0.1' if host == 'localhost' else host}:{_port('vault-devops')}"


def vault_env(token: str, home: Path) -> dict[str, str]:
    """Env cho `vault` CLI: `VAULT_ADDR` của `vault-devops`, `token` truyền vào, `HOME` là thư mục tạm `home` (tạo nếu chưa
    có) để `vault login` ghi `.vault-token` ở đó, không vào project của người học; không mang `VAULT_*` của máy. `home` nằm
    trong repo thì ValueError."""
    if not token:
        raise ValueError("vault_env cần token của lab")
    home = Path(home).resolve()
    if home.is_relative_to(ROOT):
        raise ValueError(f"HOME của vault phải nằm ngoài repo: {home}")
    home.mkdir(parents=True, exist_ok=True)
    return {"VAULT_ADDR": vault_devops_address(), "VAULT_TOKEN": token, "HOME": str(home)}


def _vault_health(address: str) -> dict | None:
    import urllib.error
    import urllib.request

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"{address}/v1/sys/health", timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return json.loads(error.read().decode("utf-8"))
        except ValueError:
            return None
    except (OSError, ValueError):
        return None


OBS_DIR = ROOT / "setup" / "observability"
OBS_IMAGES = {
    "prometheus": "prom/prometheus:v3.5.0@sha256:63805ebb8d2b3920190daf1cb14a60871b16fd38bed42b857a3182bc621f4996",
    "alertmanager": "prom/alertmanager:v0.34.1@sha256:e9733bafb1bdef9b00e25a21f8f99dc26a22224bf16641ad754d1649f4c3357a",
    "grafana": "grafana/grafana:13.2.5@sha256:9f7aa1e1e3246aade5792d35a738049f7f32f89cd51d1956cf426a4e86268a84",
    "loki": "grafana/loki:3.7.9@sha256:0db216b630ae1f348a1584c67f3cead8b4c1fc839169a39501db664744158e28",
    "otel-collector": "otel/opentelemetry-collector-contrib:0.163.2@sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849",
    "jaeger": "jaegertracing/jaeger:2.22.0@sha256:836b967b5abcf1f7758066aa6b348619267a2f1459f72d472840570f9bd88a17",
}
OBS_READY = {
    "otel-collector": (13133, "/"),
    "jaeger": (16686, "/"),
    "loki": (3100, "/ready"),
    "prometheus": (9090, "/-/ready"),
    "alertmanager": (9093, "/-/ready"),
    "grafana": (3000, "/api/health"),
}
OBS_CONFIG_DIR = "observability"
OBS_COMPOSE = "devops-ex-obs.compose.yaml"
OBS_PROJECT_FILES = ("compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml")
OBS_MEMORY = "512m"
OBS_TIMEOUT = 180
OBS_PULL = " && ".join(f"docker pull {image}" for image in OBS_IMAGES.values())


def _obs_stage(stage: Path, project: Path | None) -> Path:
    """Dựng thư mục project cho `ObsStack` trong `stage`: cấu hình mặc định của `setup/observability/` chép vào
    `observability/`, rồi chép đè thư mục `project` của người học (tệp cùng đường dẫn trong `observability/` thay tệp
    mặc định), rồi gộp service của stack vào tệp compose của người học (nếu có) thành một tệp `OBS_COMPOSE`."""
    import yaml

    shutil.copytree(OBS_DIR, stage / OBS_CONFIG_DIR, ignore=shutil.ignore_patterns("compose.yaml", *_COPY_IGNORE))
    merged: dict[str, Any] = {}
    if project is not None:
        project = Path(project).resolve()
        if not project.is_dir():
            pytest.fail(f"ObsStack: không có thư mục project {project}")
        shutil.copytree(project, stage, symlinks=True, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*_COPY_IGNORE))
        found = next((stage / name for name in OBS_PROJECT_FILES if (stage / name).is_file()), None)
        if found is not None:
            try:
                merged = yaml.safe_load(found.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as error:
                pytest.fail(f"ObsStack: không đọc được {found.name} của project: {error}")
            if not isinstance(merged, dict):
                pytest.fail(f"ObsStack: {found.name} của project phải là một mapping")
    obs = yaml.safe_load((OBS_DIR / "compose.yaml").read_text(encoding="utf-8"))["services"]
    own = dict(merged.get("services") or {})
    clash = sorted(set(own) & set(obs))
    if clash:
        pytest.fail(f"ObsStack: service {', '.join(clash)} trùng tên service của stack observability. Đổi tên service "
                    f"của bạn; muốn đổi cấu hình của stack thì đặt tệp vào {OBS_CONFIG_DIR}/<service>/ trong project")
    networks = list(merged.get("networks") or {})
    for name, svc in obs.items():
        svc["volumes"] = [f"./{OBS_CONFIG_DIR}/{volume[2:]}" if volume.startswith("./") else volume
                          for volume in svc.get("volumes") or []]
        if networks:
            svc["networks"] = list(dict.fromkeys(["default", *networks]))
        own[name] = svc
    merged.pop("name", None)
    merged["services"] = own
    file = stage / OBS_COMPOSE
    file.write_text(yaml.safe_dump(merged, sort_keys=False, allow_unicode=True), encoding="utf-8")
    for path in [stage, *stage.rglob("*")]:
        if not path.is_symlink():
            path.chmod(path.stat().st_mode | (0o755 if path.is_dir() else 0o644))
    return file


def _otlp_value(value: dict):
    for key in ("stringValue", "boolValue", "doubleValue"):
        if key in value:
            return value[key]
    if "intValue" in value:
        return int(value["intValue"])
    if "arrayValue" in value:
        return [_otlp_value(item) for item in value["arrayValue"].get("values", [])]
    return None


def _otlp_traces(result: dict) -> list:
    """OTLP JSON (`resourceSpans`) thành danh sách trace, mỗi trace một mục, span kèm `service` và `attributes` dạng dict."""
    traces: dict[str, list] = {}
    for resource in result.get("resourceSpans") or []:
        attributes = {a["key"]: _otlp_value(a.get("value") or {}) for a in (resource.get("resource") or {}).get("attributes", [])}
        for scope in resource.get("scopeSpans") or []:
            for span in scope.get("spans") or []:
                traces.setdefault(span["traceId"], []).append({
                    "spanID": span.get("spanId"), "parentSpanID": span.get("parentSpanId") or None,
                    "name": span.get("name"), "kind": span.get("kind"), "service": attributes.get("service.name"),
                    "attributes": {a["key"]: _otlp_value(a.get("value") or {}) for a in span.get("attributes") or []},
                })
    return [{"traceID": trace_id, "spans": spans} for trace_id, spans in traces.items()]


class ObsStack:
    """Stack observability (OTel Collector, Jaeger, Loki, Prometheus, Alertmanager, Grafana; image `OBS_IMAGES` ghim
    digest) của một `DockerLab`, dựng bằng `lab.compose` nên có mọi bảo đảm của nó: cổng trống trên 127.0.0.1, nhãn
    `devops-ex=1`, cpuset, giới hạn RAM, bind mount chỉ đọc, `close()` của lab chạy `down -v`.

    Không service nào của stack tạo volume: dữ liệu của Prometheus, Loki, Alertmanager, Jaeger nằm trong tmpfs, Grafana
    ghi vào lớp ghi của container. Cấu hình mặc định ở `setup/observability/`.

    `project` (tuỳ chọn) là thư mục của người học. Tệp `compose.yaml` trong đó (nếu có, ví dụ api, worker, postgres,
    redis của Olist Shop) được gộp với stack thành một project compose: app gửi OTLP gRPC tới `otel-collector:4317`,
    Prometheus scrape `api:8000` và `worker:9101`. Tệp trong `project/observability/` thay tệp mặc định cùng đường dẫn,
    ví dụ `observability/prometheus/rules/olist.yml`, `observability/grafana/dashboards/olist.json`,
    `observability/otel-collector/config.yaml`. Service của người học trùng tên service của stack thì fail.

    Mỗi lab một project compose, nên một lab chỉ dựng một `ObsStack` và không gọi `lab.compose` riêng. Các hàm truy vấn
    nhận `timeout` (giây): lớn hơn 0 thì hỏi lại tới khi có kết quả khác rỗng hoặc hết giờ.
    """

    def __init__(self, lab: DockerLab, *, project: Path | None = None, env: dict | None = None,
                 memory: str = OBS_MEMORY, timeout: float = OBS_TIMEOUT) -> None:
        lab._require_entered()
        for image in OBS_IMAGES.values():
            Exercise.require_image(image, f"Tải các image của stack bằng: {OBS_PULL}")
        stage = Path(tempfile.mkdtemp(prefix=f"{lab.network}-obs-"))
        try:
            file = _obs_stage(stage, project)
            start = time.monotonic()
            self.project = lab.compose(file, env=env, memory=memory, timeout=timeout)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
        self.urls = {name: f"http://127.0.0.1:{self.project.port(name, port)}" for name, (port, _) in OBS_READY.items()}
        self._wait_ready(max(timeout - (time.monotonic() - start), 30))
        self.startup_seconds = time.monotonic() - start

    @staticmethod
    def _client():
        import httpx

        return httpx.Client(trust_env=False, timeout=10)

    def _wait_ready(self, timeout: float) -> None:
        import httpx

        pending = dict(OBS_READY)
        deadline = time.monotonic() + timeout
        with self._client() as client:
            while pending:
                for name, (_, path) in list(pending.items()):
                    try:
                        if client.get(self.urls[name] + path).status_code == 200:
                            del pending[name]
                    except httpx.HTTPError:
                        pass
                if not pending:
                    return
                if time.monotonic() > deadline:
                    logs = "\n".join(f"--- {name}\n{self.project.logs(name, tail=DOCKER_LOG_LINES)[-DOCKER_LOG_CHARS:]}"
                                     for name in pending)
                    pytest.fail(f"ObsStack: {', '.join(pending)} chưa sẵn sàng sau {int(timeout)} giây.\n{logs}")
                time.sleep(0.5)

    def url(self, service: str) -> str:
        return self.urls[service]

    def _get(self, service: str, path: str, params: dict | None = None):
        with self._client() as client:
            response = client.get(self.urls[service] + path, params=params)
        if response.status_code >= 400:
            pytest.fail(f"{service} {path} trả {response.status_code}: {response.text[:DOCKER_LOG_CHARS]}")
        return response.json()

    @staticmethod
    def eventually(fetch, timeout: float = 60, interval: float = 1):
        """Gọi `fetch()` tới khi kết quả khác rỗng hoặc hết `timeout` giây, trả kết quả cuối. Dùng khi cần điều kiện
        riêng, ví dụ `stack.eventually(lambda: [t for t in stack.jaeger_traces("api") if ...])`."""
        deadline = time.monotonic() + timeout
        result = fetch()
        while not result and time.monotonic() < deadline:
            time.sleep(interval)
            result = fetch()
        return result

    def _poll(self, fetch, timeout: float):
        return self.eventually(fetch, timeout) if timeout > 0 else fetch()

    def prom_query(self, expr: str, *, timeout: float = 0) -> list:
        """`data.result` của `/api/v1/query` (instant query); query sai cú pháp thì fail kèm lỗi của Prometheus."""
        return self._poll(lambda: self._get("prometheus", "/api/v1/query", {"query": expr})["data"]["result"], timeout)

    def loki_query(self, logql: str, *, since: float = 3600, limit: int = 100, timeout: float = 0) -> list:
        """`data.result` của `/loki/api/v1/query_range` trong `since` giây gần nhất (stream, mỗi stream có `values`)."""
        def fetch():
            end = time.time_ns()
            params = {"query": logql, "start": str(end - int(since * 1e9)), "end": str(end), "limit": str(limit),
                      "direction": "backward"}
            return self._get("loki", "/loki/api/v1/query_range", params)["data"]["result"]
        return self._poll(fetch, timeout)

    def jaeger_traces(self, service: str, *, limit: int = 20, lookback: float = 3600, timeout: float = 0) -> list:
        """Trace của `service` (`service.name` của OTel) qua API v3 của Jaeger, gom theo trace: mỗi mục là
        `{"traceID", "spans": [{"spanID", "parentSpanID", "name", "kind", "service", "attributes"}]}`."""
        def fetch():
            from datetime import datetime, timedelta, timezone

            now = datetime.now(timezone.utc)
            params = {"query.service_name": service, "query.search_depth": str(limit),
                      "query.start_time_min": (now - timedelta(seconds=lookback)).isoformat().replace("+00:00", "Z"),
                      "query.start_time_max": (now + timedelta(seconds=60)).isoformat().replace("+00:00", "Z")}
            with self._client() as client:
                response = client.get(self.urls["jaeger"] + "/api/v3/traces", params=params)
            if response.status_code == 404:
                return []
            if response.status_code >= 400:
                pytest.fail(f"jaeger /api/v3/traces trả {response.status_code}: {response.text[:DOCKER_LOG_CHARS]}")
            return _otlp_traces(response.json().get("result") or {})
        return self._poll(fetch, timeout)

    def grafana_dashboards(self) -> list:
        """Dashboard đã provision (`/api/search?type=dash-db`): mỗi mục có `uid`, `title`, `tags`, `folderTitle`."""
        return self._get("grafana", "/api/search", {"type": "dash-db"})

    def grafana_dashboard(self, uid: str) -> dict:
        return self._get("grafana", f"/api/dashboards/uid/{uid}")["dashboard"]

    def alerts(self, *, timeout: float = 0) -> list:
        """Alert đang active trong Alertmanager (`/api/v2/alerts`): mỗi mục có `labels`, `annotations`, `status`."""
        return self._poll(lambda: self._get("alertmanager", "/api/v2/alerts"), timeout)


def _obs_tool(alias: str, image: str, entrypoint: str, args: tuple[str, ...], cwd: Path,
              timeout: float) -> subprocess.CompletedProcess:
    Exercise.require_image(image)
    cwd = Path(cwd).resolve()
    if not cwd.is_dir():
        pytest.fail(f"{alias}: cwd {cwd} không phải thư mục")
    with DockerLab() as lab:
        return lab.run_once(alias, image, *args, mounts=[(cwd, "/work")], entrypoint=entrypoint, timeout=timeout,
                            user=f"{os.getuid()}:{os.getgid()}", workdir="/work")


def promtool(*args: str, cwd: Path, timeout: float = 120) -> subprocess.CompletedProcess:
    """`promtool <args>` trong image Prometheus ghim (`OBS_IMAGES`), qua `DockerLab.run_once`: `cwd` mount chỉ đọc ở
    `/work` (thư mục làm việc), chạy bằng uid/gid của người chạy test, network riêng của lab. Ví dụ
    `promtool("test", "rules", "tests.yml", cwd=project)`."""
    return _obs_tool("promtool", OBS_IMAGES["prometheus"], "/bin/promtool", args, cwd, timeout)


def amtool(*args: str, cwd: Path, timeout: float = 120) -> subprocess.CompletedProcess:
    """`amtool <args>` trong image Alertmanager ghim, cùng cách cách ly như `promtool`. Ví dụ
    `amtool("check-config", "alertmanager.yml", cwd=project)`."""
    return _obs_tool("amtool", OBS_IMAGES["alertmanager"], "/bin/amtool", args, cwd, timeout)


ANSIBLE_VERSION = "2.21.5"
ANSIBLE_MIN_VERSION = "2.21"
ANSIBLE_TARGET_DIR = ROOT / "setup" / "ansible-target"
ANSIBLE_TARGET_PYTHON = "/usr/local/bin/python3"
ANSIBLE_MEMORY = "512m"
ANSIBLE_TIMEOUT = 600
ANSIBLE_READY_TIMEOUT = 60
_ANSIBLE_STATS = ("ok", "changed", "unreachable", "failures", "skipped", "rescued", "ignored")
_ANSIBLE_ASSETS = ("templates", "files")
_ANSIBLE_DOCS = ("README.md", "SOLUTION.md")
_ANSIBLE_KEYS = (
    r"ansible_(?:connection|host|port|user_known_hosts_file|private_key_file|password|ssh_\w+|sftp_\w+|scp_\w+|"
    r"\w*host_key_checking|ssh_pass|become_exe)|connection|delegate_to|delegate_facts|local_action|add_host|"
    r"host_key_checking|ssh_args|ssh_common_args|ssh_extra_args|ssh_executable|private_key_file|remote_port"
)
_ANSIBLE_FORBIDDEN_KEY = re.compile(rf"(?<![\w.-])(?:ansible\.builtin\.)?({_ANSIBLE_KEYS})\b\s*[\"']?\s*[:=]")
_ANSIBLE_LOCAL_ADDRESS = re.compile(
    r"(?<![\w.-])(localhost|127(?:\.\d+){1,3}|0+(?:\.0+){3}|0x7f[0-9a-f]*|2130706433)(?![\w-])"
    r"|(?<![\w:])(::1|::ffff:127(?:\.\d+){3}|\[::\])(?![\w:])", re.I)
_ANSIBLE_ESCAPE = re.compile(r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})")
_ANSIBLE_LAB_VARS = ("devops_ex_lab_addr", "devops_ex_lab_port")
ANSIBLE_PINNED_VARS = (
    "ansible_connection", "ansible_host", "ansible_ssh_host", "ansible_port", "ansible_ssh_port", "ansible_user",
    "ansible_ssh_user", "ansible_ssh_args", "ansible_ssh_common_args", "ansible_ssh_extra_args", "ansible_scp_extra_args",
    "ansible_sftp_extra_args", "ansible_ssh_executable", "ansible_sftp_executable", "ansible_scp_executable",
    "ansible_ssh_transfer_method", "ansible_host_key_checking", "ansible_ssh_host_key_checking", "ansible_ssh_private_key_file",
    "ansible_private_key_file", "ansible_private_key", "ansible_ssh_private_key", "ansible_ssh_pkcs11_provider",
    "ansible_control_path", "ansible_control_path_dir", "ansible_pipelining", "ansible_ssh_pipelining",
)
_ANSIBLE_UNREPORTED = ("ansible_user", "ansible_ssh_user")
_ANSIBLE_PLUGIN_PATHS = (
    "action_plugins", "become_plugins", "cache_plugins", "cliconf_plugins", "connection_plugins", "filter_plugins",
    "httpapi_plugins", "inventory_plugins", "lookup_plugins", "netconf_plugins", "strategy_plugins", "terminal_plugins",
    "test_plugins", "vars_plugins", "doc_fragment_plugins", "library", "module_utils",
)
_ANSIBLE_CONTROL_DIRS = ("roles", "collections", "callbacks", "ansible-home", "plugins",
                         *(f"plugins/{name}" for name in _ANSIBLE_PLUGIN_PATHS))
_ANSIBLE_WORK_DIRS = ("home", "cp", "events")
_ANSIBLE_CONNECTION = "ansible.builtin.ssh"
_ANSIBLE_CONTROL = ("id_ed25519", "id_ed25519.pub", "ssh_config", "known_hosts", "allowed", "devops_ex_proxy.py",
                    "callbacks/devops_ex_events.py", "ansible.cfg", "lab-conn.yml", "lab.ini")
_ANSIBLE_CONTROLLER_LOOKUP = re.compile(
    r"\b(?:lookup|query|q)\s*\(\s*[\"'](?:ansible\.builtin\.)?(pipe|lines)[\"']")
_ANSIBLE_CODE_REFS = ("roles", "dependencies", "include_role", "import_role", "include_tasks", "import_tasks", "import_playbook")
_ANSIBLE_VARS_REFS = ("vars_files", "include_vars")
_ANSIBLE_REF_FIELDS = ("role", "name", "file", "dir", "tasks_from", "vars_from", "defaults_from", "handlers_from", "_raw_params")
_ANSIBLE_DATA_DIRS = ("group_vars", "host_vars", "vars", "defaults", "files", "templates")
_ANSIBLE_REF_LINE = re.compile(
    r"(?<![\w.-])(?:ansible\.(?:builtin|legacy)\.)?"
    rf"({'|'.join((*_ANSIBLE_CODE_REFS, *_ANSIBLE_VARS_REFS))}|role|tasks_from|vars_from|defaults_from|handlers_from)"
    r"\b\s*[\"']?\s*[:=](.*)$", re.M)
_ANSIBLE_ROLES_PATH = re.compile(r"(?<![\w.-])roles_path\b\s*[\"']?\s*[:=]", re.I)
_ANSIBLE_PARENT = re.compile(r"(?<![^\s\"'\[{(,=:/\\])\.\.(?=[\s\"'\]}),/\\]|$)", re.M)
_ANSIBLE_UNSAFE_REF = re.compile(r"\{\{|\{%|\{#|\$|\\|\.\.|(?:^|[\s\[{,=:\"'])[/~*&!]")
_ANSIBLE_VAULT_HEADER = "$ANSIBLE_VAULT"
_ANSIBLE_CALLBACK = '''
import json
import os

from ansible.playbook.handler import Handler
from ansible.plugins.callback import CallbackBase
from ansible.template import Templar

PINNED = frozenset(json.loads(os.environ.get("DEVOPS_EX_PINNED", "[]")))
DEFAULT_CONNECTIONS = {None, "ssh", "smart", "ansible.builtin.ssh"}


def pinned(names):
    return sorted(name for name in names if isinstance(name, str) and name in PINNED)


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "notification"
    CALLBACK_NAME = "devops_ex_events"
    CALLBACK_NEEDS_ENABLED = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path = os.environ.get("DEVOPS_EX_EVENTS")

    def _write(self, record):
        if self._path:
            with open(self._path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\\n")

    def v2_playbook_on_play_start(self, play):
        self._play = play
        manager = getattr(play, "_variable_manager", None)
        inventory = getattr(manager, "_inventory", None)
        for name in pinned((play.vars or {}).keys()):
            self._write({"type": "pinned", "source": "play vars", "host": None, "name": name})
        if play.connection not in DEFAULT_CONNECTIONS:
            self._write({"type": "pinned", "source": "play connection", "host": None, "name": play.connection})
        for host in (inventory.hosts.values() if inventory else ()):
            for name in pinned(host.vars.keys()):
                self._write({"type": "pinned", "source": "inventory host vars", "host": host.name, "name": name})
            for group in host.groups:
                for name in pinned(group.vars.keys()):
                    self._write({"type": "pinned", "source": f"inventory group {group.name}", "host": host.name, "name": name})

    def _executed(self, result):
        delegated = result._result.get("_ansible_delegated_vars") or {}
        if delegated:
            return (delegated.get("ansible_delegated_host"), delegated.get("ansible_connection"), delegated.get("ansible_host"),
                    delegated.get("ansible_port"))
        play = getattr(self, "_play", None)
        manager = getattr(play, "_variable_manager", None)
        try:
            variables = manager.get_vars(play=play, host=result._host, task=result._task)
            templar = Templar(loader=manager._loader, variables=variables)
            def resolve(*names):
                defined = [name for name in names if variables.get(name) is not None]
                return templar.template(variables[defined[-1]]) if defined else None

            values = [resolve("ansible_connection"), resolve("ansible_host", "ansible_ssh_host"),
                      resolve("ansible_port", "ansible_ssh_port")]
        except Exception as error:
            return result._host.get_name(), f"unknown: {error}", None, None
        return (result._host.get_name(), *values)

    def _task(self, status, result):
        task = result._task
        role = getattr(task, "_role", None)
        host = result._host.get_name()
        target, connection, address, port = self._executed(result)
        sources = [("task vars", task.get_vars().keys()), ("ansible_facts", (result._result.get("ansible_facts") or {}).keys())]
        if role:
            sources += [("role vars", role.get_vars().keys()), ("role defaults", role.get_default_vars().keys())]
        for source, names in sources:
            for name in pinned(names):
                self._write({"type": "pinned", "source": source, "host": host, "name": name})
        if task.connection not in DEFAULT_CONNECTIONS:
            self._write({"type": "pinned", "source": "task connection", "host": host, "name": task.connection})
        self._write({
            "type": "task", "host": host, "task": task.name or task.action, "action": task.action,
            "status": status, "changed": bool(result._result.get("changed", False)), "handler": isinstance(task, Handler),
            "role": role.get_name() if role else None, "tags": sorted(task.tags or []),
            "target": target, "connection": connection, "address": address, "port": str(port) if port is not None else None,
        })

    def v2_runner_on_ok(self, result):
        self._task("ok", result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._task("ignored" if ignore_errors else "failed", result)

    def v2_runner_on_skipped(self, result):
        self._task("skipped", result)

    def v2_runner_on_unreachable(self, result):
        self._task("unreachable", result)

    def v2_playbook_on_stats(self, stats):
        for host in sorted(stats.processed):
            self._write({"type": "stats", "host": host, **stats.summarize(host)})
'''


_ANSIBLE_PROXY = '''
import json
import os
import socket
import sys
import threading

host, port = sys.argv[1], sys.argv[2]
with open(sys.argv[3], encoding="utf-8") as handle:
    allowed = {tuple(line.split()) for line in handle if line.strip()}
ok = (host, port) in allowed
events = os.environ.get("DEVOPS_EX_EVENTS")
if events:
    with open(events, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "connect", "address": host, "port": port, "allowed": ok}) + "\\n")
if not ok:
    sys.stderr.write(f"devops-ex: chặn kết nối SSH tới {host}:{port}, chỉ target của lab được phép\\n")
    sys.exit(1)
sock = socket.create_connection((host, int(port)), timeout=15)
sock.settimeout(None)


def upstream():
    while True:
        data = os.read(0, 65536)
        if not data:
            break
        sock.sendall(data)
    try:
        sock.shutdown(socket.SHUT_WR)
    except OSError:
        pass


threading.Thread(target=upstream, daemon=True).start()
while True:
    data = sock.recv(65536)
    if not data:
        break
    view = memoryview(data)
    while view:
        view = view[os.write(1, view):]
'''

class _AnsibleTagged:
    def __init__(self, tag: str, value: str) -> None:
        self.tag, self.value = tag, value

    def __repr__(self) -> str:
        return f"{self.tag} {self.value[:40]!r}"


def _ansible_yaml_documents(text: str) -> list:
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    def tagged(loader, suffix, node):
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node, deep=True)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node, deep=True)
        return _AnsibleTagged(f"!{suffix}", str(loader.construct_scalar(node)))

    Loader.add_multi_constructor("!", tagged)
    try:
        return list(yaml.load_all(text, Loader=Loader))
    except (yaml.YAMLError, RecursionError, TypeError, ValueError):
        return []


def _ansible_ref_values(value) -> list:
    if isinstance(value, dict):
        return [item for field in _ANSIBLE_REF_FIELDS if field in value for item in _ansible_ref_values(value[field])]
    if isinstance(value, list):
        return [item for entry in value for item in _ansible_ref_values(entry)]
    return [value] if isinstance(value, (str, _AnsibleTagged)) else []


def _ansible_yaml_refs(documents: list) -> list[tuple[str, object]]:
    found, seen, stack = [], set(), list(reversed(documents))
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if isinstance(node, dict):
            for key, value in node.items():
                name = re.sub(r"^ansible\.(?:builtin|legacy)\.", "", key) if isinstance(key, str) else None
                if name in (*_ANSIBLE_CODE_REFS, *_ANSIBLE_VARS_REFS):
                    found += [(name, item) for item in _ansible_ref_values(value)]
                stack.append(value)
        elif isinstance(node, list):
            stack.extend(reversed(node))
    return found


def _ansible_ref_problem(key: str, value) -> str | None:
    if isinstance(value, _AnsibleTagged):
        return f"giá trị có tag `{value.tag}` (Ansible giải mã hay giữ nguyên nó lúc chạy, phép quét không thấy đường dẫn thật)"
    if _ANSIBLE_UNSAFE_REF.search(value):
        return "có `..`, đường dẫn tuyệt đối, `~`, `$`, `\\`, alias YAML hay giá trị template (`{{`, `{%`)"
    if key in _ANSIBLE_CODE_REFS and set(re.split(r"[/\s=]+", value)) & set(_ANSIBLE_DATA_DIRS):
        return f"trỏ vào thư mục dữ liệu ({', '.join(_ANSIBLE_DATA_DIRS)}), nơi tệp mã hoá vault được phép nằm"
    return None


def _ansible_reference_problems(rel: Path, text: str, where) -> list[str]:
    outside = ("chỉ được trỏ tới role, playbook, task hay tệp biến nằm trong bài bằng đường dẫn tương đối viết thẳng (không "
               "`..`, không đường dẫn tuyệt đối, `~`, `$`, alias YAML hay template): Ansible nạp plugin cạnh role và playbook "
               "mà nó tải, nên tham chiếu ra ngoài bài là đường để code lạ chạy trong tiến trình ansible-playbook")
    found = []
    for match in _ANSIBLE_PARENT.finditer(text):
        found.append(f"{where(match)}: `..` bị từ chối: tham chiếu {outside}")
    for match in _ANSIBLE_ROLES_PATH.finditer(text):
        found.append(f"{where(match)}: `roles_path` bị từ chối: lab tự đặt nơi tìm role. Để role trong `roles/` cạnh playbook")
    if set(rel.parts[:-1]) & set(_ANSIBLE_ASSETS):
        return found
    for match in _ANSIBLE_REF_LINE.finditer(text):
        if _ANSIBLE_UNSAFE_REF.search(match.group(2)):
            found.append(f"{where(match)}: `{match.group(1)}:{match.group(2)}` bị từ chối: `{match.group(1)}` {outside}")
    for key, value in _ansible_yaml_refs(_ansible_yaml_documents(text)):
        reason = _ansible_ref_problem(key, value)
        if reason:
            found.append(f"{rel}: `{key}` trỏ tới {value!r} bị từ chối, {reason}: `{key}` {outside}")
    if text.lstrip().startswith(_ANSIBLE_VAULT_HEADER) and not set(rel.parts[:-1]) & set(_ANSIBLE_DATA_DIRS):
        found.append(f"{rel}: tệp mã hoá cả tệp bằng vault ({_ANSIBLE_VAULT_HEADER}) chỉ được nằm trong "
                     f"{', '.join(_ANSIBLE_DATA_DIRS)}: phép quét không đọc được nội dung đã mã hoá, nên playbook hay task "
                     "mã hoá có thể giấu tham chiếu ra ngoài bài. Chỉ mã hoá tệp biến")
    return found


def ansible_problems(root: Path) -> list[str]:
    """Phần lớn là tín hiệu sớm cho người học, không phải ranh giới: tệp dưới `root` đặt cách kết nối (`connection`,
    `ansible_connection`, `ansible_host`, `ansible_port`, `ansible_ssh_*`, khoá `host_key_checking`...), `delegate_to`,
    `local_action`, `add_host`, nhắc `localhost`, địa chỉ trong 127.0.0.0/8 (kể cả dạng rút gọn `127.1`), `0.0.0.0`, `::1`,
    dùng escape `\\xNN`/`\\uNNNN`/`\\UNNNNNNNN` (giải mã ra tên khoá mà phép quét không thấy), lookup `pipe`/`lines`, hay thư
    mục plugin chạy trên máy điều khiển (`*_plugins`, `collections`, `library`, `module_utils`). Quét văn bản thô như
    `tofu_config_problems`, kể cả chú thích và chuỗi. Địa chỉ local và escape được phép trong `templates/` và `files/` (nội
    dung ghi lên target).

    Riêng tham chiếu ra ngoài bài là lớp chặn chính, không chỉ tín hiệu: Ansible nạp plugin cạnh mọi role nó tải, và code của
    bài ghi được vào `HOME` trong sandbox. Từ chối `..` dạng thành phần đường dẫn ở mọi tệp, `roles_path`, và tham chiếu
    (`roles`, `dependencies`, `include_role`/`import_role`, `include_tasks`, `import_tasks`, `import_playbook`, `vars_files`,
    `include_vars`) có đường dẫn tuyệt đối, `~`, `$`, `\\`, alias, anchor, tag hay template, xét cả trên phần còn lại của dòng
    lẫn trên YAML đã giải mã; tham chiếu code vào thư mục dữ liệu; tệp vault cả tệp ngoài thư mục dữ liệu. Ranh giới cho code
    của bài chạy trên máy điều khiển là sandbox bwrap; thứ giữ kết nối trong lab là biến kết nối ghim bằng extra vars, tệp
    điều khiển chỉ đọc, khoá ghim, khoá host ghim và ProxyCommand (`AnsibleLab`)."""
    root = Path(root)
    found = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_dir():
            if path.name.endswith("_plugins") or path.name in ("collections", "library", "module_utils"):
                found.append(f"{rel}/: thư mục `{path.name}` bị từ chối: Ansible tự nạp plugin, module và module_utils trong đó "
                             "(cạnh playbook hay trong role) và chúng có thể thay plugin builtin cùng tên, kể cả plugin kết "
                             "nối. Bài tập chỉ cần `ansible.builtin`, xoá thư mục này")
            continue
        if not path.is_file() or set(_COPY_IGNORE) & set(rel.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")

        def where(match: re.Match) -> str:
            return f"{rel}:{text.count(chr(10), 0, match.start()) + 1}"

        for match in _ANSIBLE_FORBIDDEN_KEY.finditer(text):
            found.append(f"{where(match)}: `{match.group(1)}` bị từ chối: lab tự quyết định cách kết nối tới target (SSH qua "
                         "cổng loopback của container, khoá host đã ghim) và ghim các biến kết nối bằng extra vars, nên dòng "
                         "này không có tác dụng trong lab và dạy một thói quen nguy hiểm. Xoá nó (phép quét đọc cả chú thích "
                         "và chuỗi; nó chỉ là tín hiệu sớm, chặn thật nằm ở lớp kết nối của lab)")
        for match in _ANSIBLE_CONTROLLER_LOOKUP.finditer(text):
            found.append(f"{where(match)}: lookup `{match.group(1)}` bị từ chối: nó chạy lệnh hay đọc tệp trên máy điều khiển. "
                         "Lấy dữ liệu trên target bằng task (`ansible.builtin.command` kèm `register`, `slurp`)")
        found += _ansible_reference_problems(rel, text, where)
        if not set(rel.parts[:-1]) & set(_ANSIBLE_ASSETS):
            for match in _ANSIBLE_ESCAPE.finditer(text):
                found.append(f"{where(match)}: escape `\\{match.group(1)}` bị từ chối ngoài `templates/` và `files/`: YAML "
                             "và JSON giải mã nó trước khi Ansible đọc, nên tên khoá có thể khác với chữ phép quét thấy. Viết "
                             "thẳng ký tự đó (tệp là UTF-8)")
            for match in _ANSIBLE_LOCAL_ADDRESS.finditer(text):
                found.append(f"{where(match)}: `{match.group(0)}` bị từ chối ngoài `templates/` và `files/`: bài Ansible không "
                             "bao giờ chạy vào máy của bạn. Đặt tên host như `redis.internal`; giá trị cần ghi lên target "
                             "để trong template")
    return found


def _ansible_files(control: Path, work: Path, ports: dict[str, int], host_keys: dict[str, str]) -> dict[str, str]:
    """Tệp điều khiển lab sinh trong `control` (sandbox chỉ thấy chỉ đọc): ssh_config (khoá riêng, ghim khoá host, không agent,
    ProxyCommand chỉ cho `127.0.0.1:<cổng của lab>`), `allowed`, known_hosts chỉ có target của lab, `lab.ini` (chỉ tên máy),
    `lab-conn.yml` (extra vars ghim `ANSIBLE_PINNED_VARS`), ansible.cfg (callback ghi sự kiện, roles/collections rỗng). Thứ
    Ansible cần ghi (`HOME`, tmp, control path) nằm trong `work`. ProxyCommand chạy python gốc bằng đường dẫn tuyệt đối với
    `-I`, nên user site và biến `PYTHON*` trong `HOME` ghi được không chạm tới nó."""
    ssh_args = f"-F {control / 'ssh_config'} -o ControlMaster=auto -o ControlPersist=60s"
    proxy = f'"{Path(sys.executable).resolve()}" -I "{control / "devops_ex_proxy.py"}" %h %p "{control / "allowed"}"'
    ssh = "\n".join([
        "Host *",
        f"  ProxyCommand {proxy}",
        "  User root",
        f'  IdentityFile "{control / "id_ed25519"}"',
        "  IdentitiesOnly yes",
        "  IdentityAgent none",
        "  ForwardAgent no",
        f'  UserKnownHostsFile "{control / "known_hosts"}"',
        "  GlobalKnownHostsFile /dev/null",
        "  StrictHostKeyChecking yes",
        "  UpdateHostKeys no",
        "  BatchMode yes",
        "  PasswordAuthentication no",
        "  ConnectTimeout 15",
        "  ServerAliveInterval 15",
        "",
    ])
    known = "".join(f"[127.0.0.1]:{ports[host]} {host_keys[host]}\n" for host in ports)
    inventory = "".join(f"{host}\n" for host in ports)
    config = "\n".join([
        "[defaults]",
        f"roles_path = {control / 'roles'}",
        f"collections_path = {control / 'collections'}",
        "collections_scan_sys_path = False",
        *(f"{name} = {control / 'plugins' / name}" for name in _ANSIBLE_PLUGIN_PATHS),
        f"local_tmp = {work / 'home' / '.ansible' / 'tmp'}",
        f"callback_plugins = {control / 'callbacks'}",
        "callbacks_enabled = devops_ex_events",
        "stdout_callback = ansible.builtin.default",
        f"interpreter_python = {ANSIBLE_TARGET_PYTHON}",
        "host_key_checking = True",
        "retry_files_enabled = False",
        "nocolor = True",
        "forks = 5",
        "timeout = 30",
        "",
        "[ssh_connection]",
        f"ssh_args = {ssh_args}",
        f"control_path_dir = {work / 'cp'}",
        "pipelining = True",
        "",
    ])
    key = str(control / "id_ed25519")
    address = f"{{{{ {_ANSIBLE_LAB_VARS[0]}[inventory_hostname] | default('0.0.0.0') }}}}"
    port = f"{{{{ {_ANSIBLE_LAB_VARS[1]}[inventory_hostname] | default(1) }}}}"
    pinned = {
        _ANSIBLE_LAB_VARS[0]: {host: "127.0.0.1" for host in ports},
        _ANSIBLE_LAB_VARS[1]: dict(ports),
        "ansible_connection": _ANSIBLE_CONNECTION,
        "ansible_host": address,
        "ansible_ssh_host": address,
        "ansible_port": port,
        "ansible_ssh_port": port,
        "ansible_user": "root",
        "ansible_ssh_user": "root",
        "ansible_ssh_args": ssh_args,
        "ansible_ssh_common_args": "",
        "ansible_ssh_extra_args": "",
        "ansible_scp_extra_args": "",
        "ansible_sftp_extra_args": "",
        "ansible_ssh_executable": "ssh",
        "ansible_sftp_executable": "sftp",
        "ansible_scp_executable": "scp",
        "ansible_ssh_transfer_method": "smart",
        "ansible_host_key_checking": True,
        "ansible_ssh_host_key_checking": True,
        "ansible_ssh_private_key_file": key,
        "ansible_private_key_file": key,
        "ansible_private_key": None,
        "ansible_ssh_private_key": None,
        "ansible_ssh_pkcs11_provider": "",
        "ansible_control_path": "%(directory)s/%%C",
        "ansible_control_path_dir": str(work / "cp"),
        "ansible_pipelining": True,
        "ansible_ssh_pipelining": True,
    }
    allowed = "".join(f"127.0.0.1 {port}\n" for port in ports.values())
    return {"ssh_config": ssh, "known_hosts": known, "lab.ini": inventory, "ansible.cfg": config, "allowed": allowed,
            "lab-conn.yml": json.dumps(pinned, indent=2) + "\n", "devops_ex_proxy.py": _ANSIBLE_PROXY,
            "callbacks/devops_ex_events.py": _ANSIBLE_CALLBACK}


def _ansible_env(control: Path, work: Path, events: Path) -> dict[str, str]:
    """Env dựng từ đầu cho lệnh `ansible-*` trong sandbox: `ANSIBLE_CONFIG` là tệp do lab sinh (không đọc `ansible.cfg` ở
    thư mục hiện tại, `~/.ansible.cfg` hay `/etc/ansible`), `HOME` tạm, `PYTHONNOUSERSITE=1`, không mang `ANSIBLE_*` hay
    `SSH_AUTH_SOCK` của bạn."""
    return {
        "HOME": str(work / "home"),
        "ANSIBLE_CONFIG": str(control / "ansible.cfg"),
        "ANSIBLE_HOME": str(control / "ansible-home"),
        "ANSIBLE_NOCOLOR": "1",
        "ANSIBLE_FORCE_COLOR": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "DEVOPS_EX_EVENTS": str(events),
        "DEVOPS_EX_PINNED": json.dumps(sorted({*ANSIBLE_PINNED_VARS, *_ANSIBLE_LAB_VARS} - set(_ANSIBLE_UNREPORTED))),
    }


class AnsibleRun(subprocess.CompletedProcess):
    """Kết quả một lần `ansible-playbook` của `AnsibleLab`: `returncode`, `stdout`, `stderr` cộng `events` (mỗi task trên
    mỗi host: `host`, `task` (đúng `name:` của task, không có tiền tố role), `action`, `status`, `changed`, `handler`, `role`,
    `tags`) do callback của lab ghi."""

    def __init__(self, args, returncode: int, stdout: str, stderr: str, events: list[dict]) -> None:
        super().__init__(args, returncode, stdout, stderr)
        self.events = events

    @property
    def output(self) -> str:
        return f"{self.stdout or ''}\n{self.stderr or ''}"

    @property
    def recap(self) -> dict[str, dict[str, int]]:
        """PLAY RECAP theo host: `ok`, `changed`, `unreachable`, `failures`, `skipped`, `rescued`, `ignored`."""
        return {e["host"]: {key: int(e.get(key, 0)) for key in _ANSIBLE_STATS} for e in self.events if e.get("type") == "stats"}

    @property
    def changed(self) -> dict[str, int]:
        return {host: stats["changed"] for host, stats in self.recap.items()}

    @property
    def hosts(self) -> set[str]:
        return {e["host"] for e in self.events if e.get("type") in ("task", "stats") and e.get("host")}

    @property
    def connections(self) -> list[dict]:
        """Mỗi lần ssh mở kết nối (qua ProxyCommand của lab): `address`, `port`, `allowed`."""
        return [e for e in self.events if e.get("type") == "connect"]

    @property
    def pinned_overrides(self) -> list[dict]:
        """Chỗ bài cố đặt biến kết nối bị ghim (`source`, `host`, `name`), ví dụ `set_fact`, biến inventory, `connection:`."""
        return [e for e in self.events if e.get("type") == "pinned"]

    def tasks(self, name: str | None = None, *, host: str | None = None, changed: bool | None = None,
              handler: bool | None = None) -> list[dict]:
        return [e for e in self.events if e.get("type") == "task" and (name is None or e["task"] == name)
                and (host is None or e["host"] == host) and (changed is None or e["changed"] == changed)
                and (handler is None or e["handler"] == handler)]

    def tail(self, lines: int = 60) -> str:
        return "\n".join(self.output.strip().splitlines()[-lines:])


class AnsibleLab:
    """Target Ansible là container SSH do `DockerLab` dựng; `ansible-*` chạy trong `run_sandboxed`. Chỉ dùng bằng
    `with AnsibleLab(["worker-1", "worker-2"]) as lab:` (không host thì không dựng container, đủ cho `ansible-inventory`,
    `ansible-vault`).

    Image target build bằng `DockerLab.build` từ `setup/ansible-target` (`python:3.12.16-slim-trixie` cộng openssh-server,
    sudo, systemd chỉ để có `systemd-analyze`, wheel của worker Olist Shop ở `/srv/wheels`); lỗi mạng lúc build lần đầu thì
    skip. Mỗi host là một container (`no-new-privileges`, RAM `ANSIBLE_MEMORY`, cổng 22 chỉ trên 127.0.0.1 ở cổng trống),
    sshd chạy bằng root làm PID 1, không có systemd chạy thật.

    Thư mục điều khiển `control` (khoá, ssh_config, known_hosts, `allowed`, script proxy, callback, ansible.cfg, `lab-conn.yml`,
    `lab.ini`, `ANSIBLE_HOME` và thư mục rỗng cho MỌI đường dẫn plugin, library, module_utils, roles, collections) chỉ được
    mount chỉ đọc vào sandbox và được ghi lại từ bộ nhớ trước mỗi lệnh. `root` (bài đã chép, tệp test ghi) cũng chỉ đọc trong
    sandbox; chỉ `work/home` (`HOME`, local tmp), `work/cp` (control path) và `work/events` ghi được, với `work` là thư mục tạm
    riêng, không nằm trong hay cạnh bài. Ranh giới cho code của bài chạy trên máy điều khiển là sandbox (che `~/.ssh`, chỉ ba
    thư mục đó ghi được). Plugin cạnh playbook hay trong role (`*_plugins/`, `library/`, `module_utils/`) không tắt được bằng
    cấu hình và (đã thấy với 2.21.5) che được cả `ansible.builtin.ssh`, nên `stage()` từ chối chúng và bài không tạo được chúng
    trong `root` lúc chạy. Role có plugin mà code của bài ghi vào `HOME` thì không tới được: `stage()` từ chối tham chiếu có thể
    trỏ ra ngoài bài và `../home` từ bài không tồn tại. Kết nối được giữ trong lab bởi biến kết nối ghim bằng extra vars `-e
    @<control>/lab-conn.yml` luôn ở cuối (`ANSIBLE_PINNED_VARS`, kể cả tên cũ `ansible_ssh_host/port/user`), tệp điều khiển
    chỉ đọc, `known_hosts` chỉ có khoá host của các container và ProxyCommand chỉ cho `127.0.0.1:<cổng của lab>`.
    `guard_problems` (callback, sự kiện `connect`) là lớp phát hiện: tệp sự kiện phải ghi được nên không phải ranh giới.
    `stage()` chép tệp của bài vào `root` và từ chối tệp bị `ansible_problems` bắt (tín hiệu sớm). Env dựng từ đầu.
    `close()` xoá container, image, network (qua `DockerLab.close`) và ba thư mục tạm.
    """

    def __init__(self, hosts=(), *, memory: str = ANSIBLE_MEMORY, pids_limit: int = DOCKER_PIDS_LIMIT,
                 timeout: float = ANSIBLE_TIMEOUT) -> None:
        self.hosts = list(hosts)
        for host in self.hosts:
            if not _IMAGE_ALIAS.match(host):
                raise ValueError(f"Tên host {host!r} phải là chữ thường, số, '.', '_', '-'")
        self.memory = memory
        self.pids_limit = pids_limit
        self.timeout = timeout
        self.docker = DockerLab()
        self.root: Path | None = None
        self.work: Path | None = None
        self.control: Path | None = None
        self._control_files: dict[str, bytes] = {}
        self.image: str | None = None
        self.public_key = ""
        self.ports: dict[str, int] = {}
        self._entered = False
        self._runs = 0

    def __enter__(self) -> "AnsibleLab":
        self._entered = True
        self.root = Path(tempfile.mkdtemp(prefix="devops-ex-ansible-"))
        self.work = Path(tempfile.mkdtemp(prefix="devops-ex-ansible-w-"))
        self.control = Path(tempfile.mkdtemp(prefix="devops-ex-ansible-ctl-"))
        try:
            self._open()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _require_entered(self) -> None:
        if not self._entered:
            raise RuntimeError("Dùng AnsibleLab bằng `with AnsibleLab(...) as lab:` để container luôn được dọn")

    def _open(self) -> None:
        Exercise.require_tool("ansible-playbook", ANSIBLE_MIN_VERSION)
        reason = sandbox_ready()
        if reason:
            pytest.skip(SANDBOX_SKIP.format(reason=reason))
        for name in _ANSIBLE_WORK_DIRS:
            (self.work / name).mkdir(parents=True, exist_ok=True)
        host_keys: dict[str, str] = {}
        if self.hosts:
            Exercise.require_tool("docker")
            Exercise.require_tool("ssh-keygen")
            self.docker.__enter__()
            key = self.control / "id_ed25519"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"devops-ex-{self.docker.id}", "-f", str(key)],
                           check=True, capture_output=True, timeout=30)
            self.public_key = key.with_suffix(".pub").read_text(encoding="utf-8").strip()
            try:
                self.image = self.docker.build(ANSIBLE_TARGET_DIR, "ansible-target")
            except pytest.fail.Exception as error:
                if build_failed_on_network(str(error)):
                    pytest.skip("Build image target của Ansible cần mạng lần đầu (apt, pip download) mà không tải được. "
                                "Kiểm tra mạng rồi chạy lại; các lần sau dùng cache của BuildKit")
                raise
            for host in self.hosts:
                self.docker.start(host, self.image, ports=[22], env={"DEVOPS_EX_AUTHORIZED_KEY": self.public_key},
                                  memory=self.memory, pids_limit=self.pids_limit)
            for host in self.hosts:
                host_keys[host] = self._wait_ssh(host)
                self.ports[host] = self.docker.port(host, 22)
        self._control_files = {name: text.encode() for name, text in
                               _ansible_files(self.control, self.work, self.ports, host_keys).items()}
        for name in ("id_ed25519", "id_ed25519.pub"):
            if (self.control / name).exists():
                self._control_files[name] = (self.control / name).read_bytes()
        self._write_control()

    def _write_control(self) -> None:
        """Ghi lại mọi tệp điều khiển từ bản trong bộ nhớ trước mỗi lệnh (ghi tệp tạm rồi `os.replace`), xoá tệp và thư mục
        lạ trong thư mục điều khiển, tạo lại các thư mục plugin rỗng. Sandbox chỉ thấy thư mục này ở chế độ chỉ đọc; bước này
        là lớp thứ hai nếu có gì ngoài sandbox đã sửa nó."""
        files = {self.control / name for name in self._control_files}
        dirs = {self.control / name for name in _ANSIBLE_CONTROL_DIRS} | {p.parent for p in files}
        for path in sorted(self.control.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_symlink() or (path.is_file() and path not in files):
                path.unlink()
            elif path.is_dir() and path not in dirs:
                shutil.rmtree(path, ignore_errors=True)
        for path in sorted(dirs):
            path.mkdir(parents=True, exist_ok=True)
        for name, data in self._control_files.items():
            path = self.control / name
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.chmod(tmp, 0o600 if name == "id_ed25519" else 0o644)
            os.replace(tmp, path)

    def _wait_ssh(self, host: str) -> str:
        self.docker.wait_log(host, "Server listening", timeout=ANSIBLE_READY_TIMEOUT)
        result = self.docker.exec(host, "cat", "/etc/ssh/ssh_host_ed25519_key.pub")
        parts = result.stdout.split()
        if result.returncode != 0 or len(parts) < 2:
            pytest.fail(f"Không đọc được khoá host SSH của {host}: {result.stderr.strip()}")
        port = self.docker.port(host, 22)
        deadline = time.monotonic() + ANSIBLE_READY_TIMEOUT
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
                    sock.settimeout(5)
                    if sock.recv(64).startswith(b"SSH-2.0-"):
                        return f"{parts[0]} {parts[1]}"
            except OSError:
                pass
            time.sleep(0.3)
        pytest.fail(f"sshd của {host} không trả banner SSH trên 127.0.0.1:{port} sau {ANSIBLE_READY_TIMEOUT} giây. "
                    f"{self.docker._log_tail(host)}")

    @property
    def inventory(self) -> Path:
        return self.control / "lab.ini"

    def write(self, rel: str, text: str) -> Path:
        path = (self.root / rel).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"{rel} nằm ngoài thư mục tạm của lab")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def stage(self, source: Path, name: str = "project") -> Path:
        """Chép thư mục bài của người học vào thư mục tạm của lab (bỏ `__pycache__`, `.git` và tài liệu `README.md`,
        `SOLUTION.md`: Ansible không cần chúng, và không chép thì không playbook nào nạp được chúng) rồi kiểm
        `ansible_problems`; trả đường dẫn bản chép để truyền làm `cwd`."""
        self._require_entered()
        target = self.root / name
        shutil.copytree(Path(source).resolve(), target, symlinks=False,
                        ignore=shutil.ignore_patterns(*_COPY_IGNORE, *_ANSIBLE_DOCS))
        problems = ansible_problems(target)
        if problems:
            pytest.fail("Tệp Ansible bị từ chối trước khi chạy:\n- " + "\n- ".join(problems))
        return target

    def run(self, *args: str, cwd: Path | None = None, timeout: float | None = None, input: str | None = "",
            env: dict[str, str] | None = None, events: Path | None = None) -> subprocess.CompletedProcess:
        """Chạy một lệnh `ansible`, `ansible-playbook`, `ansible-inventory`, `ansible-vault`... trong sandbox. `env` thêm biến
        cho chương trình của bài (ví dụ script inventory động), không ghi đè được biến của lab."""
        self._require_entered()
        if not args or not str(args[0]).startswith("ansible"):
            raise ValueError("AnsibleLab.run chỉ chạy lệnh ansible-*")
        base = _ansible_env(self.control, self.work, events or self.work / "events" / "unused.jsonl")
        clash = sorted(set(env or {}) & {*base, "PATH", "LANG", "LC_ALL"} | {k for k in env or {} if k.startswith("ANSIBLE_")})
        if clash:
            raise ValueError(f"env không được đặt {clash}: lab tự quản các biến này")
        try:
            self._write_control()
            return run_sandboxed(list(args), writable=[self.work / name for name in _ANSIBLE_WORK_DIRS],
                                 readonly=[self.control, self.root], cwd=Path(cwd or self.root),
                                 env={**(env or {}), **base},
                                 timeout=timeout or self.timeout, input=input)
        except subprocess.TimeoutExpired:
            pytest.fail(f"{args[0]} chạy quá {timeout or self.timeout} giây")

    def playbook(self, playbook: str, *args: str, inventory=(), cwd: Path | None = None, timeout: float | None = None,
                 env: dict[str, str] | None = None) -> AnsibleRun:
        """`ansible-playbook -i <inventory của bài>... -i lab.ini <playbook> <args>`; trả `AnsibleRun`. Fail khi có task
        chạy trên host không thuộc lab."""
        self._require_entered()
        self._runs += 1
        events = self.work / "events" / f"run-{self._runs}.jsonl"
        sources = [arg for item in inventory for arg in ("-i", str(item))]
        argv = ["ansible-playbook", *sources, "-i", str(self.inventory), playbook, *args, "-e", f"@{self.control / 'lab-conn.yml'}"]
        result = self.run(*argv, cwd=cwd, timeout=timeout, env=env, events=events)
        records = []
        if events.exists():
            records = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines() if line.strip()]
        run = AnsibleRun(argv, result.returncode, result.stdout, result.stderr, records)
        problems = self.guard_problems(run)
        if problems:
            pytest.fail("Lần chạy bị lab đánh dấu lỗi vì cố đi ra ngoài các target của lab (biến kết nối đã bị ghim, kết nối "
                        "khác bị chặn, phần chạy trên máy điều khiển nằm trong sandbox):\n- "
                        + "\n- ".join(problems) + f"\n{run.tail()}")
        return run

    def guard_problems(self, run: AnsibleRun) -> list[str]:
        """Vi phạm trong một lần chạy: task trên host ngoài lab, task không đi bằng ssh tới `127.0.0.1:<cổng của host đó>`,
        kết nối bị ProxyCommand chặn, chỗ cố đặt biến kết nối bị ghim."""
        found = [f"task trên host ngoài lab: {host}" for host in sorted(run.hosts - set(self.hosts))]
        for event in run.tasks():
            target = event.get("target") or event["host"]
            expected = (_ANSIBLE_CONNECTION, "127.0.0.1", str(self.ports.get(target)))
            seen = (event.get("connection"), event.get("address"), event.get("port"))
            if target not in self.ports or seen != expected:
                found.append(f"task '{event['task']}' của {event['host']} chạy qua {seen[0]} tới {seen[1]}:{seen[2]} "
                             f"(chỉ được {_ANSIBLE_CONNECTION} tới 127.0.0.1:<cổng của {target}>)")
        for event in run.connections:
            if not event.get("allowed"):
                found.append(f"ssh tới {event.get('address')}:{event.get('port')} bị chặn: không phải target của lab")
        for event in run.pinned_overrides:
            where = f" trên {event['host']}" if event.get("host") else ""
            found.append(f"{event['source']}{where} đặt `{event['name']}`: biến kết nối do lab ghim, giá trị này bị bỏ qua")
        return sorted(set(found), key=found.index)

    def exec(self, host: str, *command: str, timeout: float = 30) -> subprocess.CompletedProcess:
        self._require_entered()
        return self.docker.exec(host, *command, timeout=timeout)

    def read(self, host: str, path: str) -> str | None:
        """Nội dung tệp trên target, None khi không có."""
        result = self.exec(host, "cat", path)
        return result.stdout if result.returncode == 0 else None

    def stat(self, host: str, path: str) -> tuple[str, str, str] | None:
        """(quyền dạng bát phân, user, group) của tệp trên target, None khi không có."""
        result = self.exec(host, "stat", "-c", "%a %U %G", path)
        if result.returncode != 0:
            return None
        mode, user, group = result.stdout.split()
        return mode, user, group

    def close(self) -> None:
        try:
            self.docker.close()
        finally:
            for path in (self.root, self.work, self.control):
                if path is not None:
                    shutil.rmtree(path, ignore_errors=True)


KIND_CLUSTER = "devops-lab"
KIND_CONFIG = ROOT / "setup" / "kind" / "devops-lab.yaml"
KIND_NODE_IMAGE = "kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a"
KUBECTL_VERSION = "1.34.13"
KUBECTL_MIN_VERSION = "1.33"
KIND_MIN_VERSION = "0.30"
HELM_VERSION = "3.22.1"
HELM_MIN_VERSION = "3.18"
KUBE_READY_TIMEOUT = 5
KUBE_TIMEOUT = 180
KUBE_CLEANUP_TIMEOUT = 120
KUBE_TOKEN_SECONDS = 7200
KUBE_KUBECONFIG_HINT = "~/.kube/devops-lab.yaml"
KUBE_CREATE = f"kind create cluster --config setup/kind/devops-lab.yaml --kubeconfig {KUBE_KUBECONFIG_HINT}"
KUBE_SKIP_DOCKER = (
    "Docker chưa chạy hoặc user chưa có quyền dùng docker, nên chưa kiểm được cluster kind {name} (mỗi node của cluster là "
    "một container Docker). Bật Docker rồi chạy lại. Xem setup/DEVOPS-TOOLS.md"
)
KUBE_SKIP_MISSING = "Chưa có cluster kind {name}. Tạo bằng: {create} rồi ghim CPU theo setup/DEVOPS-TOOLS.md"
KUBE_SKIP_STOPPED = (
    "Cluster kind {name} có nhưng node đang dừng ({states}), thường do máy vừa khởi động lại. Bật lại bằng: docker start "
    "{names} rồi chờ khoảng 30 giây. Xem setup/DEVOPS-TOOLS.md"
)
KUBE_SKIP_NOT_READY = (
    "API server của cluster kind {name} chưa sẵn sàng (kubectl get --raw /readyz qua kubeconfig tạm, chờ {seconds} giây: "
    "{detail}). Chờ thêm rồi chạy lại; vẫn lỗi thì xem docker logs {name}-control-plane"
)
KUBE_IMAGES = {
    "olist": "devops-track/olist-shop:1.0",
    "postgres": "postgres:16.15-alpine",
    "redis": "redis:7.4.12-alpine",
    "nginx": "nginx:1.30.6-alpine",
}
KUBE_OLIST_DOCKERFILE = ROOT / "setup" / "kind" / "olist-shop.Dockerfile"
KUBE_OLIST_BUILD = ("docker build --pull=false -f setup/kind/olist-shop.Dockerfile -t devops-track/olist-shop:1.0 "
                    "tracks/devops/sample-app")
KUBE_WORKERS = "devops-lab-worker,devops-lab-worker2"
KUBE_GATEWAY_DIR = ROOT / "setup" / "kind" / "gateway"
KUBE_GATEWAY_NAMESPACE = "devops-gateway"
KUBE_GATEWAY_NAME = "public"
KUBE_INGRESS_CLASS = "devops-traefik"
KUBE_GATEWAY_SERVICE = "traefik.devops-gateway.svc.cluster.local"
KUBE_LAB_DOMAIN = "olist.test"
KUBE_GATEWAY_IMAGE = "traefik:v3.7.17"
KUBE_GATEWAY_IMAGE_DIGEST = "sha256:30ff62491aacdb862ceb8c9edcf2627da638d7deafdd4b6dab32fe34f8aa3e90"
KUBE_GATEWAY_SETUP = (
    "kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side -f setup/kind/gateway/00-gateway-api-v1.6.3-standard-install.yaml "
    "&& kubectl --kubeconfig ~/.kube/devops-lab.yaml wait --for condition=Established crd --all --timeout=60s "
    "&& kubectl --kubeconfig ~/.kube/devops-lab.yaml apply -f setup/kind/gateway/10-traefik.yaml"
)
KUBE_SKIP_GATEWAY = (
    "Cluster kind {name} chưa có Gateway dùng chung ({detail}). Cài một lần (nạp image traefik:v3.7.17 trước, xem module 10 mục 0 "
    "và setup/DEVOPS-TOOLS.md): {setup}"
)
KUBE_METRICS_DIR = ROOT / "setup" / "kind" / "metrics-server"
KUBE_METRICS_VERSION = "0.9.1"
KUBE_METRICS_IMAGE = "registry.k8s.io/metrics-server/metrics-server:v0.9.1"
KUBE_METRICS_IMAGE_DIGEST = "sha256:9b0ba1926e1d3089673f45461c3c1416109dea33b3ba3434048defd380df329b"
KUBE_METRICS_SETUP = "kubectl --kubeconfig ~/.kube/devops-lab.yaml apply -k setup/kind/metrics-server"
KUBE_SKIP_METRICS = (
    "Cluster kind {name} chưa có metrics-server chạy được ({detail}). Cài một lần (kéo image theo digest rồi nạp bằng docker save và "
    "kind load image-archive, kiểm SHA256SUMS, xem module 11 mục 0 và setup/DEVOPS-TOOLS.md): {setup}; vừa cài thì chờ khoảng "
    "30 giây cho lần lấy số liệu đầu tiên"
)
KUBE_ARGOCD_DIR = ROOT / "setup" / "kind" / "argocd"
KUBE_ARGOCD_VERSION = "3.5.6"
KUBE_ARGOCD_NAMESPACE = "argocd"
KUBE_ARGOCD_IMAGE = "quay.io/argoproj/argocd:v3.5.6"
KUBE_ARGOCD_IMAGE_DIGEST = "sha256:8e5cc5bb008df8a09dba439462e58c94c55b7735888d3ebde0c25fc05e4e5335"
KUBE_ARGOCD_REDIS_IMAGE = "public.ecr.aws/docker/library/redis:8.2.3-alpine"
KUBE_ARGOCD_REDIS_IMAGE_DIGEST = "sha256:08ad0b1d280850169a790dba1393ff7a90aef951fc19632cf4d3ce4f78e679ba"
KUBE_ARGOCD_SOPS_IMAGE = "ghcr.io/getsops/sops:v3.13.3-alpine"
KUBE_ARGOCD_SOPS_IMAGE_DIGEST = "sha256:ae501277bf742f1662e0f881f43dd8fd6798b489a8058e921dbf6cda597140ea"
KUBE_ARGOCD_CMP = "sops-kustomize"
KUBE_ARGOCD_AGE_SECRET = "devops-sops-age"
KUBE_ARGOCD_AGE_PUBLIC = "devops-sops-age-public"
KUBE_IN_CLUSTER = "https://kubernetes.default.svc"
KUBE_GIT_NAMESPACE = "devops-git"
KUBE_GIT_SERVICE = "git.devops-git.svc.cluster.local"
KUBE_GIT_ROOT = "/srv/git"
KUBE_ARGOCD_SETUP = (
    "kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side -k setup/kind/argocd "
    "&& sleep 3 && kubectl --kubeconfig ~/.kube/devops-lab.yaml wait --for condition=Established crd/appprojects.argoproj.io --timeout=60s "
    "&& kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side --force-conflicts -f setup/kind/argocd/20-default-project.yaml"
)
KUBE_ARGOCD_KEY_SETUP = (
    'keydir=$(mktemp -d) && age-keygen -o "$keydir/keys.txt" && kubectl --kubeconfig ~/.kube/devops-lab.yaml -n argocd create secret '
    'generic devops-sops-age --from-file=keys.txt="$keydir/keys.txt" && kubectl --kubeconfig ~/.kube/devops-lab.yaml -n argocd '
    'create configmap devops-sops-age-public --from-literal=recipient="$(age-keygen -y "$keydir/keys.txt")" && rm -rf "$keydir"'
)
KUBE_SKIP_ARGOCD = (
    "Cluster kind {name} chưa có ArgoCD dùng chung ({detail}). Admin cài một lần (kéo ba image theo digest rồi nạp bằng docker save "
    "và kind load image-archive, kiểm SHA256SUMS, xem module 12 mục 0 và setup/DEVOPS-TOOLS.md): {setup}; rồi tạo khoá age dùng "
    "chung (khoá riêng chỉ vào Secret argocd/devops-sops-age, không để lại trên máy): {key}"
)
_KUBE_AGE_RECIPIENT = re.compile(r"age1[0-9a-z]{58}")
KUBE_GITOPS_MAX_BYTES = 20 * 1024 * 1024
KUBE_GITOPS_MAX_FILES = 2000
KUBE_GITOPS_MAX_REPO_BYTES = 40 * 1024 * 1024
_KUBE_OPERATION_SOURCES = ("source", "sources", "manifests")
_KUBE_ARGO_APP = re.compile(r"[a-z0-9]([-a-z0-9]{0,51}[a-z0-9])?")
KUBE_NODE_LOCK_TIMEOUT = 900
KUBE_SHARED_NAMESPACES = ("kube-system", "local-path-storage", "devops-gateway", "argocd", "devops-git")
KUBE_SHARED_READY_TIMEOUT = 180
KUBE_LOAD = "kind load docker-image {images} --name {name} --nodes " + KUBE_WORKERS
KUBE_SKIP_IMAGES = (
    "Image chưa nạp vào worker của cluster kind {name} ({detail}); test không bao giờ kéo image từ Internet. Nạp bằng: {load}{build}. "
    "Docker dùng containerd image store mà lệnh trên báo 'content digest ... not found' thì nạp qua docker save --platform "
    "linux/amd64 rồi kind load image-archive, xem setup/DEVOPS-TOOLS.md"
)
_KIND_LABEL = "io.x-k8s.kind.cluster"
_KIND_NODE = re.compile(r"devops-lab-(?:control-plane|worker\d*)")
_KIND_NODE_SHELLS = {"sh", "bash", "dash", "zsh", "ash", "ksh", "busybox", "env"}
_KUBE_SA = "devops-ex-learner"
_KUBE_LABEL_KEY = "devops-ex"
_KUBECTL_FORBIDDEN = {
    "kubeconfig", "context", "cluster", "user", "server", "token", "as", "as-group", "as-uid", "username", "password",
    "client-certificate", "client-key", "certificate-authority", "insecure-skip-tls-verify", "tls-server-name", "group",
    "serviceaccount",
}
_KUBECTL_SUBJECT_FLAGS = {"user", "group", "serviceaccount"}
_KUBECTL_BINDING_COMMANDS = (("create", "rolebinding"), ("create", "clusterrolebinding"))
_KUBECTL_BOOL_SHORT = set("AwRith")
_HELM_INSTALL_FORBIDDEN = {"post-renderer", "post-renderer-args", "namespace", "create-namespace"}
_KUBE_ENV_OWNED = ("KUBE", "HELM_")
_KUBE_CLUSTER_KINDS = frozenset({
    "Namespace", "Node", "PersistentVolume", "ComponentStatus", "ClusterRole", "ClusterRoleBinding", "StorageClass", "CSIDriver",
    "CSINode", "VolumeAttachment", "VolumeAttributesClass", "IngressClass", "PriorityClass", "RuntimeClass",
    "CustomResourceDefinition", "APIService", "MutatingWebhookConfiguration", "ValidatingWebhookConfiguration",
    "ValidatingAdmissionPolicy", "ValidatingAdmissionPolicyBinding", "MutatingAdmissionPolicy", "MutatingAdmissionPolicyBinding",
    "CertificateSigningRequest", "ClusterTrustBundle", "FlowSchema", "PriorityLevelConfiguration", "DeviceClass", "ResourceSlice",
    "IPAddress", "ServiceCIDR",
})
_KUBE_TENANT_WIDE = "chặn hay sửa request của mọi namespace"
_KUBE_REFUSED = {
    "Namespace": "lab tự tạo namespace riêng; bài không tạo hay sửa namespace, kể cả nhãn Pod Security của namespace khác",
    "Node": "node là của cả cluster",
    "MutatingWebhookConfiguration": _KUBE_TENANT_WIDE,
    "ValidatingWebhookConfiguration": _KUBE_TENANT_WIDE,
    "ValidatingAdmissionPolicy": _KUBE_TENANT_WIDE,
    "ValidatingAdmissionPolicyBinding": _KUBE_TENANT_WIDE,
    "MutatingAdmissionPolicy": _KUBE_TENANT_WIDE,
    "MutatingAdmissionPolicyBinding": _KUBE_TENANT_WIDE,
    "APIService": "chuyển cả một nhóm API sang server khác",
    "CertificateSigningRequest": "xin chứng chỉ client đăng nhập cluster",
    "RuntimeClass": "đổi runtime chạy container của cả cluster",
    "FlowSchema": "đổi thứ tự ưu tiên request của cả cluster",
    "PriorityLevelConfiguration": "đổi thứ tự ưu tiên request của cả cluster",
    "PersistentVolume": "PV do bài tạo trỏ được ra ngoài cluster (nfs tới máy host) hay giữ sẵn PVC của lab khác; PV tĩnh dùng "
                        "KubeLab.admin_local_pv, PV động dùng StorageClass standard",
    "Gateway": "bài gắn route vào Gateway dùng chung devops-gateway/public; Gateway chiếm listener của controller dùng chung",
    "AppProject": "AppProject quyết định repo và namespace mà ArgoCD được sync tới; testkit tạo sẵn project riêng của lab "
                  "(KubeLab.argocd_project)",
    "ApplicationSet": "ApplicationSet sinh Application hàng loạt và không chạy trong namespace của lab; viết từng Application "
                      "trong project của lab",
    "GatewayClass": "GatewayClass chọn controller cho cả cluster; dùng GatewayClass devops-traefik có sẵn",
    "ReferenceGrant": "ReferenceGrant mở quyền tham chiếu chéo namespace; route của bài chỉ trỏ Service trong namespace của lab",
    "StorageClass": "provisioner chạy bằng quyền của node; tham số như pathPattern của local-path tạo được volume trỏ ra ngoài thư "
                    "mục dữ liệu, tới socket containerd của node; dùng StorageClass standard có sẵn hoặc KubeLab.admin_local_pv",
}
KUBE_ALLOWABLE = {
    "ClusterRole": ("rbac.authorization.k8s.io", "clusterroles"),
    "ClusterRoleBinding": ("rbac.authorization.k8s.io", "clusterrolebindings"),
    "IngressClass": ("networking.k8s.io", "ingressclasses"),
    "PriorityClass": ("scheduling.k8s.io", "priorityclasses"),
    "CustomResourceDefinition": ("apiextensions.k8s.io", "customresourcedefinitions"),
}
_KUBE_RW = ["get", "list", "watch", "create", "update", "patch", "delete", "deletecollection"]
_KUBE_READ = ["get", "list", "watch"]
_KUBE_LEARNER_RULES = [
    {"apiGroups": [""], "resources": ["pods", "services", "configmaps", "secrets", "persistentvolumeclaims", "serviceaccounts",
                                      "replicationcontrollers", "replicationcontrollers/scale", "resourcequotas", "limitranges"],
     "verbs": _KUBE_RW},
    {"apiGroups": [""], "resources": ["pods/exec", "pods/attach", "pods/portforward", "pods/ephemeralcontainers", "pods/eviction",
                                      "services/proxy"], "verbs": ["get", "create", "update", "patch"]},
    {"apiGroups": [""], "resources": ["pods/log", "pods/status", "endpoints", "events", "persistentvolumeclaims/status",
                                      "services/status", "resourcequotas/status"], "verbs": _KUBE_READ},
    {"apiGroups": ["apps"], "resources": ["deployments", "statefulsets", "daemonsets", "replicasets", "deployments/scale",
                                          "statefulsets/scale", "replicasets/scale", "deployments/rollback", "controllerrevisions"],
     "verbs": _KUBE_RW},
    {"apiGroups": ["batch"], "resources": ["jobs", "cronjobs"], "verbs": _KUBE_RW},
    {"apiGroups": ["autoscaling"], "resources": ["horizontalpodautoscalers"], "verbs": _KUBE_RW},
    {"apiGroups": ["policy"], "resources": ["poddisruptionbudgets"], "verbs": _KUBE_RW},
    {"apiGroups": ["networking.k8s.io"], "resources": ["networkpolicies", "ingresses"], "verbs": _KUBE_RW},
    {"apiGroups": ["gateway.networking.k8s.io"], "resources": ["httproutes"], "verbs": _KUBE_RW},
    {"apiGroups": ["discovery.k8s.io"], "resources": ["endpointslices"], "verbs": _KUBE_READ},
    {"apiGroups": ["coordination.k8s.io"], "resources": ["leases"], "verbs": _KUBE_RW},
    {"apiGroups": ["rbac.authorization.k8s.io"], "resources": ["roles", "rolebindings"], "verbs": _KUBE_RW},
    {"apiGroups": ["metrics.k8s.io"], "resources": ["pods"], "verbs": ["get", "list"]},
    {"apiGroups": ["argoproj.io"], "resources": ["applications"], "verbs": _KUBE_RW},
]
KUBE_ARGOCD_HOOK_FINALIZER = "argocd.argoproj.io/hook-finalizer"
_KUBE_HOOK_KINDS = ",".join(
    f"{resource}.{group}" if group else resource
    for rule in _KUBE_LEARNER_RULES if "create" in rule["verbs"]
    for group in rule["apiGroups"] for resource in rule["resources"]
    if "/" not in resource and group not in ("argoproj.io", "gateway.networking.k8s.io"))
_KUBE_SYSTEM_USER = (
    "((request.userInfo.username.startsWith('system:') && !request.userInfo.username.startsWith('system:serviceaccount:')) || "
    "request.userInfo.username.startsWith('system:serviceaccount:kube-system:') || "
    "request.userInfo.username.startsWith('system:serviceaccount:local-path-storage:'))"
)
KUBE_LOCAL_PV_ROOT = "/srv/devops-lab-pv"
_KUBE_AGGREGATE = "rbac.authorization.k8s.io/aggregate-to-"
_KUBE_ADMIN_GROUPS = ("kubeadm:cluster-admins", "system:masters")
_KUBE_NAME = re.compile(r"[a-z0-9]([-a-z0-9]{0,40}[a-z0-9])?")
_KUBE_QUANTITY = re.compile(r"[1-9]\d{0,3}(Mi|Gi)")
_KUBE_WORKER = re.compile(r"devops-lab-worker\d*")
_KUBE_TAINT_KEY = re.compile(r"(?:[a-z0-9]([-a-z0-9.]{0,60}[a-z0-9])?/)?[a-zA-Z0-9]([-a-zA-Z0-9_.]{0,61}[a-zA-Z0-9])?")
_KUBE_TAINT_VALUE = re.compile(r"(?:[a-zA-Z0-9]([-a-zA-Z0-9_.]{0,61}[a-zA-Z0-9])?)?")
_KUBE_TAINT_EFFECTS = ("NoSchedule", "PreferNoSchedule", "NoExecute")
_KUBE_READ_CLUSTER = [
    {"apiGroups": [""], "resources": ["nodes", "namespaces", "persistentvolumes"], "verbs": ["get", "list", "watch"]},
    {"apiGroups": ["storage.k8s.io"], "resources": ["storageclasses", "csidrivers", "csinodes"], "verbs": ["get", "list", "watch"]},
    {"apiGroups": ["networking.k8s.io"], "resources": ["ingressclasses"], "verbs": ["get", "list", "watch"]},
    {"apiGroups": ["gateway.networking.k8s.io"], "resources": ["gatewayclasses", "gateways"], "verbs": ["get", "list", "watch"]},
    {"apiGroups": ["scheduling.k8s.io"], "resources": ["priorityclasses"], "verbs": ["get", "list", "watch"]},
    {"apiGroups": ["node.k8s.io"], "resources": ["runtimeclasses"], "verbs": ["get", "list", "watch"]},
    {"apiGroups": ["apiextensions.k8s.io"], "resources": ["customresourcedefinitions"], "verbs": ["get", "list", "watch"]},
    {"apiGroups": ["rbac.authorization.k8s.io"], "resources": ["clusterroles", "clusterrolebindings"], "verbs": ["get", "list", "watch"]},
    {"apiGroups": ["metrics.k8s.io"], "resources": ["nodes", "pods"], "verbs": ["get", "list"]},
]
_KUBE_BASELINE_CAPS = {"AUDIT_WRITE", "CHOWN", "DAC_OVERRIDE", "FOWNER", "FSETID", "KILL", "MKNOD", "NET_BIND_SERVICE", "SETFCAP",
                       "SETGID", "SETPCAP", "SETUID", "SYS_CHROOT"}
_KUBE_HOST = "cho container chạm tới node, mà node kind là container privileged nên từ đó chạm được máy host"


def _kind_docker(*args: str, input: str | None = None, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout, input=input, env=_docker_env())


def kind_nodes(name: str = KIND_CLUSTER) -> dict[str, str]:
    """Tên container node của cluster kind `name` (theo nhãn `io.x-k8s.kind.cluster`) và trạng thái Docker của nó."""
    result = _run_tool(["docker", "ps", "-a", "--filter", f"label={_KIND_LABEL}={name}", "--format", "{{.Names}}\t{{.State}}"],
                       env=_docker_env())
    if result is None or result.returncode != 0:
        return {}
    return dict(line.split("\t", 1) for line in result.stdout.splitlines() if "\t" in line)


def kind_kubeconfig(name: str = KIND_CLUSTER) -> str:
    """Kubeconfig admin của cluster lấy bằng `kind get kubeconfig` (in ra stdout, không ghi tệp nào), env không có
    `KUBECONFIG`."""
    result = subprocess.run(["kind", "get", "kubeconfig", "--name", name], capture_output=True, text=True, timeout=30,
                            env=_docker_env())
    if result.returncode != 0 or "clusters:" not in result.stdout:
        pytest.fail(f"kind get kubeconfig --name {name} lỗi (mã {result.returncode}): {result.stderr.strip()}")
    return result.stdout


def _kube_env(kubeconfig: Path, home: Path) -> dict[str, str]:
    return {
        "KUBECONFIG": str(kubeconfig),
        "HOME": str(home),
        "KUBERC": "off",
        "HELM_CACHE_HOME": str(home / ".cache" / "helm"),
        "HELM_CONFIG_HOME": str(home / ".config" / "helm"),
        "HELM_DATA_HOME": str(home / ".local" / "share" / "helm"),
    }


def _write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


class _KubeAdmin:
    """kubectl bằng kubeconfig admin lấy từ `kind get kubeconfig`, chỉ cho mã cố định của testkit. Tệp nằm trong thư mục riêng,
    chỉ mount (chỉ đọc) vào sandbox của chính lệnh admin, HOME riêng (cache discovery không dùng chung với người học)."""

    def __init__(self, root: Path, name: str) -> None:
        self.dir = root / "admin"
        self.home = root / "admin-home"
        self.kubeconfig = self.dir / "kubeconfig"
        self.home.mkdir(parents=True, exist_ok=True)
        self.text = kind_kubeconfig(name)
        _write_private(self.kubeconfig, self.text)

    def run(self, *args: str, input: str | None = None, timeout: float = 60) -> subprocess.CompletedProcess:
        _write_private(self.kubeconfig, self.text)
        try:
            return run_sandboxed(["kubectl", *args], writable=[self.home], readonly=[self.dir], cwd=self.home,
                                 env=_kube_env(self.kubeconfig, self.home), timeout=timeout, input=input)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(["kubectl", *args], 124, "", f"kubectl {' '.join(args)} chạy quá {timeout:.0f}s")

    def cluster_resources(self) -> list[str]:
        """Loại tài nguyên cluster-scoped list và xoá được, trừ `nodes`: chỉ dùng để dọn theo nhãn."""
        result = self.run("api-resources", "--namespaced=false", "--verbs=list,delete", "-o", "name")
        names = [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
        return [n for n in names if n.split(".")[0] != "nodes"]

    def has_argocd(self) -> bool:
        """Cluster có CRD Application của ArgoCD (nhóm `argoproj.io`)."""
        result = self.run("api-resources", "--api-group=argoproj.io", "-o", "name")
        return result.returncode == 0 and "applications.argoproj.io" in result.stdout.split()

    def cluster_kinds(self) -> set[str]:
        result = self.run("api-resources", "--namespaced=false", "--no-headers")
        kinds = set()
        for line in result.stdout.splitlines():
            words = line.split()
            if "false" in words[:-1]:
                kinds.add(words[words.index("false") + 1])
        return kinds


def _kube_ready(admin: _KubeAdmin, name: str) -> None:
    result = admin.run("get", "--raw", "/readyz", f"--request-timeout={KUBE_READY_TIMEOUT}s", timeout=KUBE_READY_TIMEOUT + 10)
    if result.returncode != 0 or result.stdout.strip() != "ok":
        detail = (result.stderr or result.stdout).strip().splitlines()
        pytest.skip(KUBE_SKIP_NOT_READY.format(name=name, seconds=KUBE_READY_TIMEOUT, detail=detail[-1] if detail else "không rõ"))


def _kube_node_paths() -> tuple[Path, Path]:
    root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "devops-track"
    return root / "kube-nodes.lock", root / "kube-nodes.state.json"


def _kube_node_entry_ok(entry) -> bool:
    if not isinstance(entry, dict) or not isinstance(entry.get("node"), str) or not _KUBE_WORKER.fullmatch(entry["node"]):
        return False
    if entry.get("cordon") is True and set(entry) == {"node", "cordon"}:
        return True
    taint = entry.get("taint")
    return (set(entry) == {"node", "taint"} and isinstance(taint, list) and len(taint) == 2 and isinstance(taint[0], str)
            and bool(_KUBE_TAINT_KEY.fullmatch(taint[0])) and taint[1] in _KUBE_TAINT_EFFECTS)


def _kube_node_state_read() -> list[dict]:
    path = _kube_node_paths()[1]
    try:
        actions = json.loads(path.read_text(encoding="utf-8")).get("actions", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [entry for entry in actions if _kube_node_entry_ok(entry)] if isinstance(actions, list) else []


def _kube_node_state_write(actions: list[dict]) -> None:
    path = _kube_node_paths()[1]
    if not actions:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"actions": actions}), encoding="utf-8")
    os.replace(tmp, path)


def _kube_node_undo(entry: dict) -> list[str]:
    if entry.get("cordon"):
        return ["uncordon", entry["node"]]
    return ["taint", "nodes", entry["node"], f"{entry['taint'][0]}:{entry['taint'][1]}-"]


def _kube_node_leftovers(admin: "_KubeAdmin", actions: list[dict]) -> list[dict]:
    result = admin.run("get", "nodes", "-o", "json")
    try:
        nodes = {n["metadata"]["name"]: n.get("spec") or {} for n in json.loads(result.stdout).get("items", [])}
    except (ValueError, KeyError, AttributeError):
        return list(actions)
    present = []
    for entry in actions:
        spec = nodes.get(entry["node"])
        if spec is None:
            continue
        if entry.get("cordon") and spec.get("unschedulable"):
            present.append(entry)
        elif entry.get("taint") and any(t.get("key") == entry["taint"][0] and t.get("effect") == entry["taint"][1]
                                        for t in spec.get("taints") or []):
            present.append(entry)
    return present


def _kube_node_undo_present(admin: "_KubeAdmin") -> list[dict]:
    """Chỉ gọi khi đang giữ khoá node. Đọc lại tệp trạng thái, so với trạng thái thật của node, hoàn tác đúng những thao tác testkit
    đã ghi mà còn trên cluster, rồi ghi lại tệp. Trả các thao tác hoàn tác không được (tệp vẫn giữ chúng). Một cordon hay taint ghi
    trong tệp mà vẫn còn trên node thì coi là của lab bị ngắt: testkit không phân biệt được với cùng cordon hay taint người dùng tự đặt
    lại sau đó trên đúng node đó."""
    actions = _kube_node_state_read()
    if not actions:
        _kube_node_state_write([])
        return []
    present = _kube_node_leftovers(admin, actions)
    failed = []
    for entry in present:
        result = admin.run(*_kube_node_undo(entry))
        if result.returncode != 0 and "not found" not in result.stderr:
            failed.append(entry)
    _kube_node_state_write(failed)
    return failed


def _kube_check_node_leftovers(admin: "_KubeAdmin") -> None:
    """Một lab bị giết (SIGKILL) giữa bài thao tác node để lại cordon, taint mà `close()` chưa kịp hoàn tác. Có tệp trạng thái và
    khoá node đang rảnh thì giữ khoá, đọc lại tệp, hoàn tác những thao tác còn trên cluster rồi chạy tiếp; chỉ skip kèm đúng lệnh hoàn
    tác khi chính việc hoàn tác lỗi. Khoá đang bị giữ (một bài thao tác node đang chạy, hay một tiến trình khác đang hoàn tác) thì
    không đụng gì và không chờ: `require_cluster` của tiến trình này chạy tiếp trong khi worker có thể còn cordon vài giây."""
    import fcntl

    lock, state = _kube_node_paths()
    if not state.exists():
        return
    with open(lock, "a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        failed = _kube_node_undo_present(admin)
    if failed:
        commands = " && ".join(f"kubectl --kubeconfig {KUBE_KUBECONFIG_HINT} {' '.join(_kube_node_undo(e))}" for e in failed)
        pytest.skip(f"Một bài thao tác node trước đó bị ngắt nên worker còn cordon hay taint của lab, và testkit không tự hoàn tác "
                    f"được ({state}). Hoàn tác bằng: {commands}")


def _require_cluster_up(name: str) -> None:
    Exercise.require_tool("kind", KIND_MIN_VERSION)
    Exercise.require_tool("kubectl", KUBECTL_MIN_VERSION)
    if not docker_ready():
        pytest.skip(KUBE_SKIP_DOCKER.format(name=name))
    listed = _run_tool(["kind", "get", "clusters"], env=_docker_env())
    nodes = kind_nodes(name)
    if listed is None or name not in listed.stdout.split() or not nodes:
        pytest.skip(KUBE_SKIP_MISSING.format(name=name, create=KUBE_CREATE))
    stopped = sorted(node for node, state in nodes.items() if state != "running")
    if stopped:
        states = ", ".join(f"{node}: {nodes[node]}" for node in stopped)
        pytest.skip(KUBE_SKIP_STOPPED.format(name=name, states=states, names=" ".join(stopped)))
    reason = sandbox_ready()
    if reason:
        pytest.skip(SANDBOX_SKIP.format(reason=reason))


def _kind_node(node) -> str:
    if not isinstance(node, str) or not _KIND_NODE.fullmatch(node):
        raise ValueError(f"Chỉ dùng được node của cluster devops-lab (devops-lab-control-plane, devops-lab-worker, "
                         f"devops-lab-worker<số>), không nhận {node!r}")
    result = _kind_docker("inspect", "--format", '{{index .Config.Labels "' + _KIND_LABEL + '"}}', node, timeout=30)
    if result.returncode != 0 or result.stdout.strip() != KIND_CLUSTER:
        raise ValueError(f"Container {node} không phải node của cluster kind {KIND_CLUSTER} (thiếu nhãn {_KIND_LABEL}={KIND_CLUSTER})")
    return node


def kind_node_exec(node: str, *cmd, timeout: float = 60, input: str | None = None) -> subprocess.CompletedProcess:
    """`docker exec` một argv cố định của testkit trong node kind (ví dụ `etcdctl snapshot save` ở module 10). Chỉ nhận
    `devops-lab-control-plane`, `devops-lab-worker`, `devops-lab-worker<số>` có nhãn kind của `devops-lab`. Lệnh là argv, không
    bao giờ qua shell (`sh`, `bash`, `env`... ở đầu bị từ chối): giá trị từ bài của người học chỉ được là một phần tử argv."""
    if not cmd or not all(isinstance(part, (str, Path)) for part in cmd):
        raise ValueError("kind_node_exec cần argv không rỗng gồm chuỗi")
    if Path(str(cmd[0])).name in _KIND_NODE_SHELLS:
        raise ValueError(f"kind_node_exec không chạy {cmd[0]}: truyền argv, không qua shell")
    _kind_node(node)
    flags = ["-i"] if input is not None else []
    return _kind_docker("exec", *flags, node, *map(str, cmd), input=input, timeout=timeout)


def kind_node_cp(node: str, source, dest, *, to_node: bool = False, timeout: float = 120) -> subprocess.CompletedProcess:
    """`docker cp` giữa node kind và máy: mặc định chép `node:source` về `dest` trên máy, `to_node=True` chép `source` trên
    máy vào `node:dest`. Đường dẫn trong node phải tuyệt đối; không nhận `-` (luồng tar)."""
    _kind_node(node)
    inside, local = (str(dest), str(source)) if to_node else (str(source), str(dest))
    if not inside.startswith("/"):
        raise ValueError(f"Đường dẫn trong node phải tuyệt đối, không nhận {inside!r}")
    if not local or local.startswith("-"):
        raise ValueError(f"Đường dẫn trên máy không được là {local!r}")
    args = [local, f"{node}:{inside}"] if to_node else [f"{node}:{inside}", local]
    result = _kind_docker("cp", *args, timeout=timeout)
    if result.returncode != 0:
        pytest.fail(f"docker cp {' '.join(args)} lỗi: {result.stderr.strip()}")
    return result


def _kind_image_ref(image: str) -> str:
    path, tag = image.rsplit(":", 1) if ":" in image.rsplit("/", 1)[-1] else (image, "latest")
    first = path.split("/", 1)[0]
    if "/" not in path:
        path = f"docker.io/library/{path}"
    elif "." not in first and ":" not in first and first != "localhost":
        path = f"docker.io/{path}"
    return f"{path}:{tag}"


def kind_images_missing(images, name: str = KIND_CLUSTER) -> dict[str, list[str]]:
    """Image trong `images` chưa có trong containerd của từng worker (`crictl images`), theo tên đầy đủ (`postgres:16` là
    `docker.io/library/postgres:16`). Control plane có taint nên pod của bài không chạy ở đó, không xét."""
    missing = {}
    for node in sorted(n for n in kind_nodes(name) if _KUBE_WORKER.fullmatch(n)):
        result = kind_node_exec(node, "crictl", "images", "-o", "json")
        try:
            listed = json.loads(result.stdout).get("images", []) if result.returncode == 0 else []
        except ValueError:
            listed = []
        tags = {tag for item in listed if isinstance(item, dict) for tag in item.get("repoTags") or []}
        lost = [image for image in images if _kind_image_ref(image) not in tags]
        if lost:
            missing[node] = lost
    return missing


def _kube_flatten(documents) -> list:
    flat = []
    for doc in documents:
        if isinstance(doc, dict) and str(doc.get("kind", "")).endswith("List") and isinstance(doc.get("items"), list):
            flat += _kube_flatten(doc["items"])
        elif doc is not None:
            flat.append(doc)
    return flat


def _kube_pod_specs(value):
    if isinstance(value, dict):
        if isinstance(value.get("containers"), list):
            yield value
        for item in value.values():
            yield from _kube_pod_specs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _kube_pod_specs(item)


def _kube_security_problems(where: str, context, owner: str) -> list[str]:
    if not isinstance(context, dict):
        return []
    found = []
    if context.get("privileged") is True:
        found.append(f"{where}: {owner} privileged {_KUBE_HOST}")
    added = ((context.get("capabilities") or {}).get("add") or []) if isinstance(context.get("capabilities"), dict) else []
    extra = sorted({str(cap).upper().removeprefix("CAP_") for cap in added} - _KUBE_BASELINE_CAPS)
    if extra:
        found.append(f"{where}: {owner} thêm capability {', '.join(extra)} ngoài mức Pod Security baseline")
    if context.get("procMount") not in (None, "Default"):
        found.append(f"{where}: {owner} đặt procMount {context.get('procMount')}, lộ /proc của node")
    for key in ("seccompProfile", "appArmorProfile"):
        if isinstance(context.get(key), dict) and context[key].get("type") == "Unconfined":
            found.append(f"{where}: {owner} đặt {key} Unconfined, bỏ lớp chặn syscall")
    if isinstance(context.get("windowsOptions"), dict) and context["windowsOptions"].get("hostProcess"):
        found.append(f"{where}: {owner} hostProcess {_KUBE_HOST}")
    return found


def _kube_pod_problems(where: str, spec: dict) -> list[str]:
    found = [f"{where}: {key}: true {_KUBE_HOST}" for key in ("hostNetwork", "hostPID", "hostIPC") if spec.get(key) is True]
    for volume in spec.get("volumes") or []:
        if isinstance(volume, dict) and "hostPath" in volume:
            found.append(f"{where}: volume {volume.get('name')} dùng hostPath {_KUBE_HOST}")
    found += _kube_security_problems(where, spec.get("securityContext"), "pod")
    for field in ("initContainers", "containers", "ephemeralContainers"):
        for container in spec.get(field) or []:
            if not isinstance(container, dict):
                continue
            owner = f"container {container.get('name')}"
            found += _kube_security_problems(where, container.get("securityContext"), owner)
            for port in container.get("ports") or []:
                if isinstance(port, dict) and port.get("hostPort"):
                    found.append(f"{where}: {owner} mở hostPort {port['hostPort']} trên node")
    return found


def _kube_rbac_problems(where: str, kind: str, doc: dict, namespace: str) -> list[str]:
    found = []
    if kind in ("RoleBinding", "ClusterRoleBinding"):
        role = str((doc.get("roleRef") or {}).get("name", ""))
        if role == "cluster-admin" or role.startswith("system:") or (kind == "ClusterRoleBinding" and role in ("admin", "edit")):
            found.append(f"{where}: gắn vào {role}, quyền quản trị rộng hơn namespace của lab")
        for subject in doc.get("subjects") or []:
            if not isinstance(subject, dict):
                continue
            name, subject_ns = str(subject.get("name", "")), subject.get("namespace")
            if subject.get("kind") in ("Group", "User") and name.startswith("system:"):
                found.append(f"{where}: cấp quyền cho {name}, tức mọi user hay mọi thành phần hệ thống")
            if subject.get("kind") == "ServiceAccount" and subject_ns not in (None, "", namespace):
                found.append(f"{where}: cấp quyền cho ServiceAccount ở namespace {subject_ns}, ngoài namespace của lab")
    if kind in ("Role", "ClusterRole"):
        if doc.get("aggregationRule"):
            found.append(f"{where}: aggregationRule gom quyền của role khác vào role này")
        labels = (doc.get("metadata") or {}).get("labels") or {}
        for key in sorted(k for k in labels if isinstance(k, str) and k.startswith(_KUBE_AGGREGATE)):
            found.append(f"{where}: nhãn {key} gộp role này vào view/edit/admin dùng chung của mọi namespace")
        for rule in doc.get("rules") or []:
            if not isinstance(rule, dict):
                continue
            verbs = {str(v) for v in rule.get("verbs") or []}
            risky = sorted(verbs & {"escalate", "bind", "impersonate"})
            if risky:
                found.append(f"{where}: verb {', '.join(risky)} cho phép tự nâng quyền")
            if "*" in verbs and "*" in {str(r) for r in rule.get("resources") or []}:
                found.append(f"{where}: rule '*' trên mọi resource là quyền quản trị")
    return found


def _kube_host_ok(host, domain: str) -> bool:
    return isinstance(host, str) and (host == domain or host.endswith(f".{domain}"))


def _kube_route_problems(where: str, kind: str, doc: dict, namespace: str) -> list[str]:
    spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
    domain = f"{namespace}.{KUBE_LAB_DOMAIN}"
    found = []
    if kind == "Ingress":
        if spec.get("ingressClassName") != KUBE_INGRESS_CLASS:
            found.append(f"{where}: ingressClassName phải là {KUBE_INGRESS_CLASS} (controller dùng chung của cluster)")
        if "defaultBackend" in spec:
            found.append(f"{where}: defaultBackend bắt mọi host của controller dùng chung, kể cả host của lab khác")
        rules = spec.get("rules") if isinstance(spec.get("rules"), list) else []
        hosts = [r.get("host") if isinstance(r, dict) else None for r in rules]
        hosts += [h for t in spec.get("tls") or [] if isinstance(t, dict) for h in t.get("hosts") or []]
        if not rules or not all(_kube_host_ok(h, domain) for h in hosts):
            found.append(f"{where}: mọi rule cần host là {domain} hay tên con của nó")
    if kind == "HTTPRoute" and str(doc.get("apiVersion", "")).startswith("gateway.networking.k8s.io/"):
        parents = spec.get("parentRefs") if isinstance(spec.get("parentRefs"), list) else []
        good = [p for p in parents if isinstance(p, dict) and p.get("name") == KUBE_GATEWAY_NAME
                and p.get("namespace") == KUBE_GATEWAY_NAMESPACE and p.get("kind", "Gateway") == "Gateway"
                and p.get("group", "gateway.networking.k8s.io") == "gateway.networking.k8s.io"]
        if not parents or len(good) != len(parents):
            found.append(f"{where}: parentRefs chỉ được trỏ Gateway {KUBE_GATEWAY_NAMESPACE}/{KUBE_GATEWAY_NAME}")
        hostnames = spec.get("hostnames") if isinstance(spec.get("hostnames"), list) else []
        if not hostnames or not all(_kube_host_ok(h, domain) for h in hostnames):
            found.append(f"{where}: hostnames cần có và chỉ gồm {domain} hay tên con của nó")
    return found


def kube_git_url(namespace: str) -> str:
    """URL nội bộ của repo git riêng của lab trên git server dùng chung (`git daemon` chỉ đọc trong namespace `devops-git`)."""
    return f"git://{KUBE_GIT_SERVICE}/{namespace}.git"


def _kube_argocd_problems(where: str, kind: str, doc: dict, namespace: str) -> list[str]:
    if kind != "Application" or not str(doc.get("apiVersion", "")).startswith("argoproj.io/"):
        return []
    spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
    url = kube_git_url(namespace)
    found = []
    if spec.get("project") != namespace:
        found.append(f"{where}: spec.project phải là project riêng của lab ({namespace}), không phải {spec.get('project')!r}")
    destination = spec.get("destination") if isinstance(spec.get("destination"), dict) else {}
    server, name = destination.get("server"), destination.get("name")
    if (destination.get("namespace") != namespace or server not in (None, KUBE_IN_CLUSTER) or name not in (None, "in-cluster")
            or (server is None and name is None)):
        found.append(f"{where}: destination chỉ được là namespace {namespace} trên cluster hiện tại ({KUBE_IN_CLUSTER})")
    sources = ([spec["source"]] if isinstance(spec.get("source"), dict) else []) + [
        s for s in spec.get("sources") or [] if isinstance(s, dict)]
    if not sources or any(s.get("repoURL") != url for s in sources):
        found.append(f"{where}: repoURL chỉ được là repo git của lab ({url})")
    if "sourceHydrator" in spec:
        found.append(f"{where}: sourceHydrator ghi ngược vào git, lab không dùng")
    operation = doc.get("operation") if isinstance(doc.get("operation"), dict) else {}
    sync = operation.get("sync") if isinstance(operation.get("sync"), dict) else {}
    for key in _KUBE_OPERATION_SOURCES:
        if key in sync:
            found.append(f"{where}: operation.sync.{key} cho ArgoCD render nguồn khác spec (repo của lab khác); chỉ sync theo spec")
    if "status" in doc:
        found.append(f"{where}: status của Application do ArgoCD ghi, bài không được tự đặt")
    return found


def kube_manifest_problems(documents, *, lab_id: str, namespace: str, allow=(), cluster_kinds=(), api_group: str | None = None) -> list[str]:
    """Kiểm tĩnh object Kubernetes của bài trước khi apply (tín hiệu sớm, ranh giới thật là quyền RBAC, policy và Pod Security
    trong cluster, xem `KubeLab`). Object namespaced chỉ ở namespace của lab (không ghi namespace thì lab đặt). Object
    cluster-scoped (danh sách dựng sẵn cộng `cluster_kinds` đọc từ cluster) phải có kind trong `allow` và nhãn
    `devops-ex=<lab_id>`. Luôn từ chối Namespace, Node, StorageClass, webhook, admission policy, APIService, CSR, RuntimeClass, FlowSchema;
    binding vào cluster-admin hay `system:*`, subject là nhóm hệ thống hay ServiceAccount ở namespace khác; role có
    escalate/bind/impersonate, `*` trên `*` hay aggregationRule; pod (ở bất kỳ độ sâu nào: Deployment, CronJob...) privileged,
    hostPath, hostNetwork/hostPID/hostIPC, hostPort, capability ngoài baseline, procMount, seccomp/AppArmor Unconfined;
    PersistentVolume hostPath hay local; StorageClass; PriorityClass globalDefault; Service có externalIPs; CustomResourceDefinition
    ngoài nhóm API `api_group` của lab; AppProject, ApplicationSet; Application của ArgoCD có project khác project của lab,
    destination ngoài namespace của lab hay ngoài cluster hiện tại, repoURL khác repo git của lab (`kube_git_url`)."""
    found = []
    cluster = _KUBE_CLUSTER_KINDS | set(cluster_kinds)
    for index, doc in enumerate(_kube_flatten(documents), 1):
        if not isinstance(doc, dict):
            found.append(f"tài liệu {index}: không phải object Kubernetes (mapping có apiVersion, kind, metadata)")
            continue
        kind, meta = doc.get("kind"), doc.get("metadata")
        if not isinstance(kind, str) or not kind or not isinstance(doc.get("apiVersion"), str) or not isinstance(meta, dict):
            found.append(f"tài liệu {index}: thiếu apiVersion, kind hay metadata")
            continue
        where = f"{kind} {meta.get('name') or meta.get('generateName') or index}"
        if kind in _KUBE_REFUSED:
            found.append(f"{where}: {kind} bị từ chối ({_KUBE_REFUSED[kind]})")
            continue
        if kind in cluster:
            if kind not in allow:
                found.append(f"{where}: {kind} là object cluster-scoped mà bài này không cho phép (KubeLab(allow=...))")
            labels = meta.get("labels") if isinstance(meta.get("labels"), dict) else {}
            if labels.get(_KUBE_LABEL_KEY) != lab_id:
                found.append(f"{where}: object cluster-scoped phải có nhãn {_KUBE_LABEL_KEY}={lab_id} để lab dọn được")
        elif meta.get("namespace") not in (None, "", namespace):
            found.append(f"{where}: namespace {meta.get('namespace')} nằm ngoài namespace của lab ({namespace})")
        found += _kube_rbac_problems(where, kind, doc, namespace)
        found += _kube_route_problems(where, kind, doc, namespace)
        found += _kube_argocd_problems(where, kind, doc, namespace)
        for spec in _kube_pod_specs(doc):
            found += _kube_pod_problems(where, spec)
        if kind == "PriorityClass" and doc.get("globalDefault") is True:
            found.append(f"{where}: globalDefault đổi độ ưu tiên mặc định của mọi pod trong cluster")
        if kind == "CustomResourceDefinition":
            crd_spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
            if api_group and crd_spec.get("group") != api_group:
                found.append(f"{where}: CRD phải thuộc nhóm API riêng của lab ({api_group}), không phải {crd_spec.get('group')}")
            conversion = crd_spec.get("conversion")
            if conversion is not None and (not isinstance(conversion, dict) or conversion.get("strategy", "None") != "None"):
                found.append(f"{where}: conversion webhook bị từ chối: API server gọi địa chỉ đó từ mạng của control plane")
            names = crd_spec.get("names") if isinstance(crd_spec.get("names"), dict) else {}
            for field in ("categories", "shortNames"):
                if field in names:
                    found.append(f"{where}: names.{field} bị từ chối: tên ngắn và nhóm (như `all`) dùng chung cho mọi lab trên cluster")
        if kind == "Service" and isinstance(doc.get("spec"), dict) and doc["spec"].get("externalIPs"):
            found.append(f"{where}: externalIPs chặn được traffic tới địa chỉ đó của mọi pod trong cluster")
        if kind == "PersistentVolume" and isinstance(doc.get("spec"), dict):
            for key in ("hostPath", "local"):
                if key in doc["spec"]:
                    found.append(f"{where}: PersistentVolume {key} trỏ vào hệ thống tệp của node, {_KUBE_HOST}")
    return found


def _kube_refuse_flags(tool: str, args) -> None:
    """Từ chối cờ đổi cluster, context, user hay danh tính. Riêng `--user`, `--group`, `--serviceaccount` của `kubectl create
    rolebinding|clusterrolebinding` là subject của binding, chỉ nhận khi lệnh con đứng đầu argv (cờ đặt trước lệnh con là cờ
    toàn cục `--user` của kubeconfig)."""
    args = [str(arg) for arg in args]
    binding = tool == "kubectl" and tuple(args[:2]) in _KUBECTL_BINDING_COMMANDS
    for arg in args:
        if arg == "--":
            return
        bad = False
        if arg.startswith("--"):
            name = arg[2:].split("=", 1)[0]
            bad = name in _KUBECTL_FORBIDDEN if tool == "kubectl" else name.startswith("kube")
            if bad and binding and name in _KUBECTL_SUBJECT_FLAGS:
                bad = False
        elif tool == "kubectl" and arg.startswith("-") and len(arg) > 1:
            for letter in arg[1:]:
                if letter == "s":
                    bad = True
                if letter == "s" or letter not in _KUBECTL_BOOL_SHORT:
                    break
        if bad:
            raise ValueError(f"{tool} không được nhận {arg}: lab chỉ chạy với kubeconfig của lab (một cluster, một context, "
                             "user riêng của lab), không đổi cluster, context, user hay danh tính")


def _kube_owned(lab_id: str, subject: str) -> str:
    return (f"has({subject}.metadata.labels) && '{_KUBE_LABEL_KEY}' in {subject}.metadata.labels && "
            f"{subject}.metadata.labels['{_KUBE_LABEL_KEY}'] == '{lab_id}'")


def _kube_hostpath_pv(name: str, path: str) -> str:
    return json.dumps({"apiVersion": "v1", "kind": "PersistentVolume", "metadata": {"name": name},
                       "spec": {"capacity": {"storage": "1Mi"}, "accessModes": ["ReadWriteOnce"], "hostPath": {"path": path}}})


def kube_leftovers(lab_id: str, name: str = KIND_CLUSTER) -> list[str]:
    """Namespace `devops-ex-<id>`, object cluster-scoped có nhãn `devops-ex=<id>`, AppProject của lab trong `argocd` và repo git
    của lab trên git server còn trên cluster; rỗng là đã dọn sạch."""
    with tempfile.TemporaryDirectory(prefix=f"{DOCKER_PREFIX}{lab_id}-check-") as tmp:
        admin = _KubeAdmin(Path(tmp), name)
        namespace = f"{DOCKER_PREFIX}{lab_id}"
        found = admin.run("get", "namespace", namespace, "--ignore-not-found", "-o", "name").stdout.split()
        kinds = ",".join(admin.cluster_resources())
        found += admin.run("get", kinds, "-l", f"{_KUBE_LABEL_KEY}={lab_id}", "-o", "name").stdout.split()
        if admin.has_argocd():
            projects = admin.run("-n", KUBE_ARGOCD_NAMESPACE, "get", "appprojects.argoproj.io", "-l", f"{_KUBE_LABEL_KEY}={lab_id}",
                                 "-o", "name")
            found += projects.stdout.split() if projects.returncode == 0 else []
            listed = admin.run("-n", KUBE_GIT_NAMESPACE, "exec", "deploy/git", "-c", "git", "--", "ls", "-1A", KUBE_GIT_ROOT)
            found += [f"git:{KUBE_GIT_ROOT}/{line}" for line in listed.stdout.split() if line == f"{namespace}.git"]
        return found


class KubeLab:
    """Namespace riêng của một test trên cluster kind `devops-lab`. Chỉ dùng bằng `with KubeLab() as lab:`.

    Mở lab: `require_cluster` (Docker, cluster, node chạy, `/readyz`), lấy kubeconfig admin bằng `kind get kubeconfig` (mã cố
    định của testkit, không bao giờ đọc `KUBECONFIG` hay `~/.kube` của người học), rồi bằng quyền admin tạo namespace
    `devops-ex-<id>` có nhãn `devops-ex=<id>` và Pod Security `enforce=<pod_security>` (baseline, hoặc restricted), ServiceAccount
    `devops-ex-learner` với Role riêng `_KUBE_LEARNER_RULES` trong namespace đó (không `impersonate`, không
    `serviceaccounts/token`, không escalate/bind; ghi được ResourceQuota, LimitRange của chính namespace đó), ClusterRoleBinding
    vào `view` (đọc mọi namespace, không có Secret) và quyền đọc object cluster-scoped, quyền ghi đúng các kind trong `allow`
    (`KUBE_ALLOWABLE`, không có StorageClass; có CustomResourceDefinition thì Role thêm quyền ghi mọi resource của nhóm API riêng
    `api_group` trong namespace của lab, và CRD phải thuộc nhóm đó; ghi `applications.argoproj.io` trong namespace của lab,
    không ghi `appprojects`), và năm
    ValidatingAdmissionPolicy: policy `devops-ex-<id>` áp cho mọi ServiceAccount của namespace (nhóm
    `system:serviceaccounts:<ns>`, kể cả ServiceAccount bài tự tạo rồi lấy token trong pod): object cluster-scoped tạo, sửa,
    xoá phải mang nhãn `devops-ex=<id>`, PV không hostPath hay local, PriorityClass không globalDefault, CRD chỉ thuộc `api_group`,
    ClusterRoleBinding không cấp cho `system:*`; policy `devops-ex-<id>-pv` từ chối PV hostPath của mọi user không phải thành phần hệ thống và PV local
    ngoài `KUBE_LOCAL_PV_ROOT` hay không do admin tạo; policy `devops-ex-<id>-rbac` (cũng cho mọi ServiceAccount của namespace,
    cả Role/RoleBinding trong namespace): không nhãn `rbac.authorization.k8s.io/aggregate-to-*`, không aggregationRule, binding
    không cấp cho `system:*` hay ServiceAccount của namespace khác (RoleBinding bỏ trống namespace của subject ServiceAccount là
    namespace của chính nó); policy `devops-ex-<id>-routes` (cũng cho mọi ServiceAccount
    của namespace): Ingress phải `ingressClassName: devops-traefik`, không `defaultBackend`, HTTPRoute chỉ gắn Gateway
    `devops-gateway/public`, mọi host là `hostname` của lab (`<namespace>.olist.test`) hay tên con; policy `devops-ex-<id>-argocd`
    (cũng cho mọi ServiceAccount của namespace): Application phải có `spec.project` là project của lab (`devops-ex-<id>`),
    destination là namespace của lab trên `https://kubernetes.default.svc`, repoURL là `repo_url` của lab, không
    `sourceHydrator`. Lab chỉ trao kubeconfig khi cả năm policy đã chặn được lần tạo thử (policy ArgoCD chỉ thử khi cluster có
    CRD của ArgoCD). GitOps: `argocd_project`, `gitops_repo`, `argocd_wait`, `age_public_key`/`sops_age_recipient`.

    `kubectl`, `helm`, `run` (script của bài), `apply_learner`, `helm_install` chạy qua `run_sandboxed` với `KUBECONFIG` là
    kubeconfig của lab (một cluster, một context có namespace của lab, token của `devops-ex-learner`) trong thư mục `control`
    chỉ đọc, `HOME` và thư mục cache, config, data của helm trong `work` (ghi được), `KUBERC=off`. Kubeconfig admin ở thư mục
    khác, không bao giờ mount vào sandbox của người học. `kubectl`/`helm` từ chối cờ đổi cluster, context, user hay danh tính
    (`--kubeconfig`, `--context`, `--server`/`-s`, `--token`, `--as`..., với helm mọi `--kube*`); script tự gọi kubectl không bị
    kiểm cờ nhưng chỉ có token của lab, `~/.kube` thật bị sandbox che. Việc cần quyền admin chỉ qua `admin_local_pv` và
    `node_action`, từ spec đã kiểm từng trường; `can_i` hỏi `kubectl auth can-i --as=...` hộ người học bằng quyền admin, chỉ đọc.
    `kubectl` nhận `--user`, `--group`, `--serviceaccount` duy nhất khi argv bắt đầu bằng `create rolebinding` hay `create
    clusterrolebinding` (subject của binding); đặt trước lệnh con hay ở lệnh khác là cờ danh tính, bị từ chối.

    Ranh giới: quyền RBAC của token, năm policy ở trên, và Pod Security của namespace (baseline chặn privileged, hostPath,
    hostNetwork, hostPID, hostIPC, hostPort, capability lạ). Node kind là container privileged: pod privileged thấy ổ đĩa của máy
    host, hostPath vào node chạm `/var` và `/run/containerd` của node. Vì thế chặn các trường đó là yêu cầu an toàn cho máy host
    chứ không chỉ cho cluster. `kube_manifest_problems` trong `apply_learner` và `helm_install` (sau `helm template`) là tín hiệu
    sớm; object được apply là đúng bản đã kiểm (JSON dựng lại từ YAML đã parse).

    `close()` gỡ cordon và taint lab đã đặt, xoá namespace (chờ tối đa `KUBE_CLEANUP_TIMEOUT`), xoá PV có `claimRef` trỏ namespace
    của lab, object cluster-scoped có nhãn `devops-ex=<id>` (không bao giờ đụng object khác, không xoá node), thư mục PV local
    trong worker, rồi thư mục tạm. Dọn lỗi thì có `UserWarning`, và test đang đạt sẽ fail.
    """

    def __init__(self, name: str = KIND_CLUSTER, *, allow=(), pod_security: str = "baseline", timeout: float = KUBE_TIMEOUT) -> None:
        if pod_security not in ("baseline", "restricted"):
            raise ValueError(f"pod_security chỉ nhận baseline hoặc restricted, không nhận {pod_security!r}")
        for kind in allow:
            if kind not in KUBE_ALLOWABLE:
                raise ValueError(f"{kind} không cho phép qua allow; chỉ nhận {', '.join(sorted(KUBE_ALLOWABLE))}")
        self.name = name
        self.allow = tuple(allow)
        self.pod_security = pod_security
        self.timeout = timeout
        self.id = uuid.uuid4().hex[:8]
        self.namespace = f"{DOCKER_PREFIX}{self.id}"
        self.label = f"{_KUBE_LABEL_KEY}={self.id}"
        self.root: Path | None = None
        self.cleanup_error: str | None = None
        self._admin: _KubeAdmin | None = None
        self._kubeconfig_text = ""
        self._cluster_kinds: set[str] = set()
        self._created = False
        self._entered = False
        self._cordoned: set[str] = set()
        self._taints: set[tuple[str, str, str]] = set()
        self._local_nodes: set[str] = set()
        self._node_lock = None
        self._argocd = False
        self._project = False
        self._git_pushed = False
        self._git_repo: GitRepo | None = None
        self._age_public: str | None = None
        self.gitops_revision = ""

    @property
    def control(self) -> Path:
        return self.root / "control"

    @property
    def kubeconfig(self) -> Path:
        return self.control / "kubeconfig"

    @property
    def admin_kubeconfig(self) -> Path:
        return self.root / "admin" / "kubeconfig"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def home(self) -> Path:
        return self.work / "home"

    def __enter__(self) -> "KubeLab":
        self._entered = True
        self.root = Path(tempfile.mkdtemp(prefix=f"{self.namespace}-kube-"))
        try:
            self._open()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, *exc) -> None:
        self.close()
        if exc_type is None and self.cleanup_error:
            pytest.fail(self.cleanup_error)

    def _require_entered(self) -> None:
        if not self._entered or self.root is None or not self._kubeconfig_text:
            raise RuntimeError("Dùng KubeLab bằng `with KubeLab(...) as lab:` để namespace luôn được dọn")

    def _open(self) -> None:
        import yaml

        _require_cluster_up(self.name)
        self.home.mkdir(parents=True)
        self.control.mkdir()
        self._admin = _KubeAdmin(self.root, self.name)
        _kube_ready(self._admin, self.name)
        self._cluster_kinds = self._admin.cluster_kinds()
        self._argocd = self._admin.has_argocd()
        if self._argocd:
            self._sweep_gitops()
        self._created = True
        result = self._admin.run("apply", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "List",
                                                                       "items": self._bootstrap()}))
        if result.returncode != 0:
            pytest.fail(f"Không dựng được namespace {self.namespace} của lab: {_output_tail(result)}")
        token = self._admin.run("create", "token", _KUBE_SA, "-n", self.namespace, f"--duration={KUBE_TOKEN_SECONDS}s")
        if token.returncode != 0 or not token.stdout.strip():
            pytest.fail(f"Không tạo được token cho {_KUBE_SA}: {_output_tail(token)}")
        admin = yaml.safe_load(self._admin.text)
        cluster = admin["clusters"][0]["cluster"]
        self._kubeconfig_text = yaml.safe_dump({
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [{"name": self.name, "cluster": {"server": cluster["server"],
                                                         "certificate-authority-data": cluster["certificate-authority-data"]}}],
            "users": [{"name": _KUBE_SA, "user": {"token": token.stdout.strip()}}],
            "contexts": [{"name": self.name, "context": {"cluster": self.name, "user": _KUBE_SA, "namespace": self.namespace}}],
            "current-context": self.name,
        }, sort_keys=False)
        self._write_control()
        self._wait_ready()

    def _bootstrap(self) -> list[dict]:
        labels = {_KUBE_LABEL_KEY: self.id}
        user = f"system:serviceaccount:{self.namespace}:{_KUBE_SA}"
        subject = [{"kind": "ServiceAccount", "name": _KUBE_SA, "namespace": self.namespace}]
        psa = {"enforce": self.pod_security, "warn": "restricted", "audit": "restricted"}
        ns_labels = {**labels, **{f"pod-security.kubernetes.io/{mode}": level for mode, level in psa.items()},
                     **{f"pod-security.kubernetes.io/{mode}-version": "latest" for mode in psa}}

        def meta(name: str, namespaced: bool = False) -> dict:
            return {"name": name, "labels": dict(labels), **({"namespace": self.namespace} if namespaced else {})}

        def cluster_binding(name: str, role: str) -> dict:
            return {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding", "metadata": meta(name),
                    "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": role}, "subjects": subject}

        def policy(name: str, rules: list, condition: str, validations: list) -> list[dict]:
            return [{"apiVersion": "admissionregistration.k8s.io/v1", "kind": "ValidatingAdmissionPolicy", "metadata": meta(name),
                     "spec": {"failurePolicy": "Fail", "matchConstraints": {"resourceRules": rules},
                              "matchConditions": [{"name": "who", "expression": condition}], "validations": validations}},
                    {"apiVersion": "admissionregistration.k8s.io/v1", "kind": "ValidatingAdmissionPolicyBinding",
                     "metadata": meta(name), "spec": {"policyName": name, "validationActions": ["Deny"]}}]

        owned_new, owned_old = _kube_owned(self.id, "object"), _kube_owned(self.id, "oldObject")
        lab_identity = (f"(request.userInfo.username == '{user}' || "
                        f"'system:serviceaccounts:{self.namespace}' in request.userInfo.groups)")
        admin = " || ".join(f"'{group}' in request.userInfo.groups" for group in _KUBE_ADMIN_GROUPS)
        no_host_pv = [
            {"expression": "request.operation == 'DELETE' || !has(object.spec.hostPath)",
             "message": "PersistentVolume hostPath trỏ vào node (từ đó tới máy host); cluster devops-lab không nhận PV hostPath"},
            {"expression": f"request.operation == 'DELETE' || !has(object.spec.local) || (({admin}) && "
                           f"object.spec.local.path.startsWith('{KUBE_LOCAL_PV_ROOT}/') && !object.spec.local.path.contains('..'))",
             "message": f"PersistentVolume local chỉ do testkit tạo, dưới {KUBE_LOCAL_PV_ROOT}/"},
        ]
        lab_rules = [
            {"expression": f"request.operation == 'DELETE' || ({owned_new})",
             "message": f"Object cluster-scoped của bài phải có nhãn {self.label}"},
            {"expression": f"request.operation == 'CREATE' || ({owned_old})",
             "message": f"Chỉ sửa, xoá được object cluster-scoped có nhãn {self.label}"},
            {"expression": "request.operation == 'DELETE' || request.resource.resource != 'persistentvolumes' || "
                           "(!has(object.spec.hostPath) && !has(object.spec.local))",
             "message": "PersistentVolume của bài không được dùng hostPath hay local (trỏ vào node, từ đó tới máy host)"},
            {"expression": "request.operation == 'DELETE' || request.resource.resource != 'priorityclasses' || "
                           "!has(object.globalDefault) || object.globalDefault == false",
             "message": "PriorityClass của bài không được globalDefault"},
            {"expression": "request.operation == 'DELETE' || request.resource.resource != 'customresourcedefinitions' || "
                           f"object.spec.group == '{self.api_group}'",
             "message": f"CustomResourceDefinition của bài phải thuộc nhóm API riêng của lab: {self.api_group}"},
            {"expression": "request.operation == 'DELETE' || request.resource.resource != 'customresourcedefinitions' || "
                           "((!has(object.spec.conversion) || object.spec.conversion.strategy == 'None') && "
                           "!has(object.spec.names.categories) && !has(object.spec.names.shortNames))",
             "message": "CustomResourceDefinition của bài không được có conversion webhook, names.categories hay names.shortNames"},
            {"expression": "request.operation == 'DELETE' || request.resource.resource != 'clusterrolebindings' || "
                           "!has(object.subjects) || !object.subjects.exists(s, s.kind != 'ServiceAccount' && "
                           "s.name.startsWith('system:'))",
             "message": "ClusterRoleBinding của bài không cấp quyền cho nhóm hay user hệ thống"},
        ]
        everything = [{"apiGroups": ["*"], "apiVersions": ["*"], "resources": ["*"], "operations": ["CREATE", "UPDATE", "DELETE"],
                       "scope": "Cluster"}]
        rbac = [{"apiGroups": ["rbac.authorization.k8s.io"], "apiVersions": ["*"],
                 "resources": ["roles", "rolebindings", "clusterroles", "clusterrolebindings"], "operations": ["CREATE", "UPDATE"],
                 "scope": "*"}]
        rbac_rules = [
            {"expression": f"!has(object.metadata.labels) || !object.metadata.labels.exists(k, k.startsWith('{_KUBE_AGGREGATE}'))",
             "message": f"Role của bài không được mang nhãn {_KUBE_AGGREGATE}* (gộp quyền vào view/edit/admin của mọi namespace)"},
            {"expression": "request.resource.resource != 'clusterroles' || !has(object.aggregationRule)",
             "message": "ClusterRole của bài không được có aggregationRule"},
            {"expression": "!(request.resource.resource in ['rolebindings', 'clusterrolebindings']) || !has(object.subjects) || "
                           "object.subjects.all(s, !s.name.startsWith('system:') && (s.kind != 'ServiceAccount' || "
                           "(request.resource.resource == 'rolebindings' && (!has(s.namespace) || s.namespace == '')) || "
                           f"(has(s.namespace) && s.namespace == '{self.namespace}')))",
             "message": f"Binding của bài chỉ cấp quyền cho user, nhóm không phải system:* hay ServiceAccount của {self.namespace}"},
        ]
        volumes = [{"apiGroups": [""], "apiVersions": ["v1"], "resources": ["persistentvolumes"], "operations": ["CREATE", "UPDATE"]}]
        domain = self.hostname
        host_ok = f"(h == '{domain}' || h.endsWith('.{domain}'))"
        routes = [{"apiGroups": ["networking.k8s.io"], "apiVersions": ["*"], "resources": ["ingresses"], "operations": ["CREATE", "UPDATE"]},
                  {"apiGroups": ["gateway.networking.k8s.io"], "apiVersions": ["*"], "resources": ["httproutes"],
                   "operations": ["CREATE", "UPDATE"]}]
        route_rules = [
            {"expression": "request.resource.resource != 'ingresses' || (has(object.spec.ingressClassName) && "
                           f"object.spec.ingressClassName == '{KUBE_INGRESS_CLASS}' && !has(object.spec.defaultBackend) && "
                           "has(object.spec.rules) && size(object.spec.rules) > 0 && "
                           f"object.spec.rules.all(r, has(r.host) && [r.host].all(h, {host_ok})) && "
                           f"(!has(object.spec.tls) || object.spec.tls.all(t, !has(t.hosts) || t.hosts.all(h, {host_ok}))))",
             "message": f"Ingress của bài: ingressClassName {KUBE_INGRESS_CLASS}, không defaultBackend, host là {domain} hay tên con"},
            {"expression": "request.resource.resource != 'httproutes' || (has(object.spec.parentRefs) && size(object.spec.parentRefs) > 0 && "
                           f"object.spec.parentRefs.all(p, p.name == '{KUBE_GATEWAY_NAME}' && has(p.namespace) && "
                           f"p.namespace == '{KUBE_GATEWAY_NAMESPACE}' && (!has(p.kind) || p.kind == 'Gateway') && "
                           "(!has(p.group) || p.group == 'gateway.networking.k8s.io')) && has(object.spec.hostnames) && "
                           f"size(object.spec.hostnames) > 0 && object.spec.hostnames.all(h, {host_ok}))",
             "message": f"HTTPRoute của bài chỉ gắn vào {KUBE_GATEWAY_NAMESPACE}/{KUBE_GATEWAY_NAME}, hostnames là {domain} hay tên con"},
        ]
        url = kube_git_url(self.namespace)
        applications = [{"apiGroups": ["argoproj.io"], "apiVersions": ["*"], "resources": ["applications"],
                         "operations": ["CREATE", "UPDATE"]}]
        argocd_rules = [
            {"expression": f"has(object.spec.project) && object.spec.project == '{self.namespace}'",
             "message": f"Application của bài phải dùng project riêng của lab: spec.project {self.namespace}"},
            {"expression": f"has(object.spec.destination) && has(object.spec.destination.namespace) && "
                           f"object.spec.destination.namespace == '{self.namespace}' && "
                           f"(has(object.spec.destination.server) || has(object.spec.destination.name)) && "
                           f"(!has(object.spec.destination.server) || object.spec.destination.server == '{KUBE_IN_CLUSTER}') && "
                           "(!has(object.spec.destination.name) || object.spec.destination.name == 'in-cluster')",
             "message": f"Application của bài chỉ sync vào namespace {self.namespace} trên cluster hiện tại ({KUBE_IN_CLUSTER})"},
            {"expression": f"(has(object.spec.source) || has(object.spec.sources)) && "
                           f"(!has(object.spec.source) || object.spec.source.repoURL == '{url}') && "
                           f"(!has(object.spec.sources) || object.spec.sources.all(s, s.repoURL == '{url}')) && "
                           "!has(object.spec.sourceHydrator)",
             "message": f"Application của bài chỉ lấy nguồn từ repo git của lab: {url}"},
            {"expression": "!has(object.operation) || !has(object.operation.sync) || "
                           "(request.operation == 'UPDATE' && has(oldObject.operation) && object.operation == oldObject.operation) || "
                           + " && ".join(f"!has(object.operation.sync.{key})" for key in _KUBE_OPERATION_SOURCES),
             "message": "Application của bài không được đặt operation.sync.source, sources hay manifests (nguồn ngoài spec)"},
            {"expression": "request.operation == 'CREATE' ? !has(object.status) : ((!has(object.status) && !has(oldObject.status)) || "
                           "(has(object.status) && has(oldObject.status) && object.status == oldObject.status))",
             "message": "status của Application do ArgoCD ghi; bài không được tạo hay sửa status"},
        ]
        items = [
            *policy(self.namespace, everything,
                    f"{lab_identity} || (request.operation == 'CREATE' && request.dryRun == true && "
                    f"request.resource.resource == 'clusterroles' && object.metadata.name == '{self._probe}')", lab_rules),
            *policy(f"{self.namespace}-rbac", rbac,
                    f"{lab_identity} || (request.operation == 'CREATE' && request.dryRun == true && "
                    f"object.metadata.name == '{self._probe}-rbac')", rbac_rules),
            *policy(f"{self.namespace}-routes", routes,
                    f"{lab_identity} || (request.dryRun == true && object.metadata.name == '{self._probe}-routes')", route_rules),
            *policy(f"{self.namespace}-argocd", applications,
                    f"{lab_identity} || (request.dryRun == true && object.metadata.name == '{self._probe}-argocd')", argocd_rules),
            *policy(f"{self.namespace}-pv", volumes,
                    f"!{_KUBE_SYSTEM_USER} && !(request.dryRun == true && object.metadata.name.endsWith('-probe-pv') && "
                    f"object.metadata.name != '{self._probe}-pv')", no_host_pv),
            {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": self.namespace, "labels": ns_labels}},
            {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": meta(_KUBE_SA, True), "automountServiceAccountToken": False},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role", "metadata": meta(_KUBE_SA, True),
             "rules": _KUBE_LEARNER_RULES},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": meta(_KUBE_SA, True),
             "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": _KUBE_SA}, "subjects": subject},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole", "metadata": meta(f"{self.namespace}-read"),
             "rules": _KUBE_READ_CLUSTER},
            cluster_binding(f"{self.namespace}-read", f"{self.namespace}-read"),
            cluster_binding(f"{self.namespace}-view", "view"),
        ]
        if "CustomResourceDefinition" in self.allow:
            items[items.index(next(i for i in items if i["kind"] == "Role"))]["rules"] = [
                *_KUBE_LEARNER_RULES, {"apiGroups": [self.api_group], "resources": ["*"], "verbs": _KUBE_RW}]
        if self.allow:
            rules = [{"apiGroups": [KUBE_ALLOWABLE[kind][0]], "resources": [KUBE_ALLOWABLE[kind][1]],
                      "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]} for kind in self.allow]
            items += [{"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole",
                       "metadata": meta(f"{self.namespace}-write"), "rules": rules},
                      cluster_binding(f"{self.namespace}-write", f"{self.namespace}-write")]
        return items

    @property
    def hostname(self) -> str:
        """Tên miền riêng của lab cho Ingress và HTTPRoute: `<namespace>.olist.test` (cộng tên con)."""
        return f"{self.namespace}.{KUBE_LAB_DOMAIN}"

    @property
    def api_group(self) -> str:
        """Nhóm API riêng của lab cho CustomResourceDefinition (`allow` có CustomResourceDefinition): `<namespace>.olist.test`.
        CRD của bài phải thuộc nhóm này (kiểm tĩnh và policy của lab); Role của lab ghi được mọi resource của nhóm này trong
        namespace của lab, không nhóm nào khác. Tên CRD là cluster-wide, nhóm riêng giúp hai lab chạy song song không giẫm nhau."""
        return f"{self.namespace}.{KUBE_LAB_DOMAIN}"

    @property
    def _probe(self) -> str:
        return f"{self.namespace}-probe"

    def _wait_ready(self) -> None:
        """Policy và RBAC mới tạo chỉ có hiệu lực sau khi API server đồng bộ (vài giây). Chờ tới khi mỗi lần tạo thử bằng admin
        (dry-run, tên probe riêng của lab) bị đúng policy tương ứng của lab chặn: ClusterRole không nhãn, ClusterRole nhãn
        aggregate-to, PV hostPath, Ingress không class, và (cluster có ArgoCD) Application dùng project `default`. Rồi chờ token
        của lab được tạo pod, mới trao kubeconfig."""
        probes = {
            self.namespace: {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole",
                             "metadata": {"name": self._probe}, "rules": []},
            f"{self.namespace}-pv": json.loads(_kube_hostpath_pv(f"{self._probe}-pv", "/")),
            f"{self.namespace}-routes": {"apiVersion": "networking.k8s.io/v1", "kind": "Ingress",
                                         "metadata": {"name": f"{self._probe}-routes", "namespace": self.namespace},
                                         "spec": {"rules": [{"host": "probe.invalid", "http": {"paths": [
                                             {"path": "/", "pathType": "Prefix",
                                              "backend": {"service": {"name": "probe", "port": {"number": 80}}}}]}}]}},
            f"{self.namespace}-rbac": {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole",
                                       "metadata": {"name": f"{self._probe}-rbac", "labels": {f"{_KUBE_AGGREGATE}view": "true"}},
                                       "rules": []},
        }
        if self._argocd:
            probes[f"{self.namespace}-argocd"] = {
                "apiVersion": "argoproj.io/v1alpha1", "kind": "Application",
                "metadata": {"name": f"{self._probe}-argocd", "namespace": self.namespace},
                "spec": {"project": "default", "destination": {"server": KUBE_IN_CLUSTER, "namespace": self.namespace},
                         "source": {"repoURL": kube_git_url(self.namespace), "path": ".", "targetRevision": "main"}}}
        deadline = time.monotonic() + 30
        for name, probe in probes.items():
            while True:
                result = self._admin.run("create", "--dry-run=server", "-f", "-", input=json.dumps(probe))
                if result.returncode != 0 and f"'{name}'" in result.stderr and "denied" in result.stderr:
                    break
                if time.monotonic() > deadline:
                    pytest.fail(f"ValidatingAdmissionPolicy {name} chưa có hiệu lực sau 30 giây: {_output_tail(result)}")
                time.sleep(0.5)
        while time.monotonic() < deadline:
            if self.kubectl("auth", "can-i", "create", "pods", check=False).stdout.strip() == "yes":
                return
            time.sleep(0.5)
        pytest.fail(f"Quyền của {_KUBE_SA} trong {self.namespace} chưa có hiệu lực sau 30 giây")

    def _write_control(self) -> None:
        for path in self.control.iterdir():
            if path != self.kubeconfig:
                shutil.rmtree(path) if path.is_dir() and not path.is_symlink() else path.unlink()
        _write_private(self.kubeconfig, self._kubeconfig_text)

    def _env(self) -> dict[str, str]:
        return _kube_env(self.kubeconfig, self.home)

    def _execute(self, cmd: list, *, cwd: Path | None = None, readonly=(), env: dict[str, str] | None = None,
                 input: str | None = None, timeout: float | None = None) -> subprocess.CompletedProcess:
        self._require_entered()
        self._write_control()
        limit = timeout or self.timeout
        try:
            return run_sandboxed(list(cmd), writable=[self.work], readonly=[self.control, *readonly], cwd=Path(cwd or self.home),
                                 env={**(env or {}), **self._env()}, timeout=limit, input=input)
        except subprocess.TimeoutExpired:
            pytest.fail(f"{cmd[0]} chạy quá {limit:.0f}s")

    @staticmethod
    def _checked(tool: str, args, result: subprocess.CompletedProcess, check: bool) -> subprocess.CompletedProcess:
        if check and result.returncode != 0:
            pytest.fail(f"{tool} {' '.join(map(str, args))} lỗi (mã {result.returncode}):\n{_output_tail(result)}")
        return result

    def kubectl(self, *args: str, check: bool = True, input: str | None = None, timeout: float | None = None) -> subprocess.CompletedProcess:
        """`kubectl <args>` bằng kubeconfig của lab, namespace mặc định là của lab. `check` thì lỗi là fail kèm output."""
        self._require_entered()
        _kube_refuse_flags("kubectl", args)
        return self._checked("kubectl", args, self._execute(["kubectl", *args], input=input, timeout=timeout), check)

    def helm(self, *args: str, check: bool = True, timeout: float | None = None, readonly=()) -> subprocess.CompletedProcess:
        self._require_entered()
        _kube_refuse_flags("helm", args)
        return self._checked("helm", args, self._execute(["helm", *args], readonly=readonly, timeout=timeout), check)

    def run(self, cmd: list, *, cwd: Path | None = None, env: dict[str, str] | None = None, readonly=(),
            input: str | None = None, timeout: float | None = None) -> subprocess.CompletedProcess:
        """Chạy script hay chương trình của bài (tự gọi kubectl, helm) trong sandbox với cùng env của lab; `env` chỉ thêm
        biến cho bài, không đặt được `PATH`, `HOME`, `LANG`, `KUBE*`, `HELM_*`. Thư mục bài truyền qua `readonly`."""
        self._require_entered()
        owned = set(self._env()) | {"PATH", "HOME", "LANG", "LC_ALL"}
        clash = sorted(k for k in env or {} if k in owned or k.startswith(_KUBE_ENV_OWNED))
        if clash:
            raise ValueError(f"env không được đặt {clash}: lab tự quản các biến này")
        return self._execute(cmd, cwd=cwd, readonly=readonly, env=env, input=input, timeout=timeout)

    @staticmethod
    def _parse(text: str, where: str) -> list:
        """YAML nhiều tài liệu bằng SafeLoader không nhận alias (`*x`): alias làm JSON dựng lại phình theo cấp số nhân."""
        import yaml

        class NoAlias(yaml.SafeLoader):
            def compose_node(self, parent, index):
                if self.check_event(yaml.AliasEvent):
                    raise yaml.YAMLError(f"alias YAML ({self.peek_event().anchor}) không được dùng trong manifest của bài")
                return super().compose_node(parent, index)

        try:
            return [doc for doc in yaml.load_all(text, Loader=NoAlias) if doc is not None]
        except yaml.YAMLError as error:
            pytest.fail(f"{where}: YAML không hợp lệ: {error}")
        except RecursionError:
            pytest.fail(f"{where}: manifest lồng quá sâu")

    def _apply_checked(self, documents: list, *, check: bool) -> subprocess.CompletedProcess:
        try:
            documents = _kube_flatten(documents)
            problems = kube_manifest_problems(documents, lab_id=self.id, namespace=self.namespace, allow=self.allow,
                                              cluster_kinds=self._cluster_kinds, api_group=self.api_group)
            payload = json.dumps({"apiVersion": "v1", "kind": "List", "items": documents}, default=str)
        except RecursionError:
            pytest.fail("Manifest bị từ chối trước khi apply: lồng quá sâu")
        if problems:
            pytest.fail("Manifest bị từ chối trước khi apply:\n- " + "\n- ".join(problems))
        return self.kubectl("apply", "-n", self.namespace, "-f", "-", input=payload, check=check)

    def manifests(self, path: Path) -> list:
        """Object trong `path`: một tệp YAML/JSON (nhiều tài liệu), thư mục (các tệp `.yaml`, `.yml`, `.json` ở cấp đầu, theo tên),
        hay thư mục Kustomize (render bằng `kubectl kustomize` trong sandbox, thư mục bài chỉ đọc)."""
        self._require_entered()
        path = Path(path).resolve()
        if path.is_dir() and any((path / n).exists() for n in ("kustomization.yaml", "kustomization.yml", "Kustomization")):
            result = self._checked("kubectl", ["kustomize", path], self._execute(["kubectl", "kustomize", str(path)],
                                                                                   readonly=[path]), True)
            return self._parse(result.stdout, f"kustomize {path.name}")
        if path.is_dir():
            files = sorted(p for p in path.iterdir() if p.suffix in (".yaml", ".yml", ".json"))
        elif path.is_file():
            files = [path]
        else:
            pytest.fail(f"Không thấy manifest {path}")
        base = path if path.is_dir() else path.parent
        for file in files:
            if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(base):
                pytest.fail(f"Manifest {file.name} phải là tệp thường trong thư mục bài, không phải symlink")
        return [doc for file in files for doc in self._parse(file.read_text(encoding="utf-8"), file.name)]

    def apply_learner(self, path: Path, *, check: bool = True) -> subprocess.CompletedProcess:
        """Đọc manifest của bài (`manifests`), kiểm bằng `kube_manifest_problems` rồi `kubectl apply -n <namespace> -f -` đúng
        các object đã kiểm bằng kubeconfig của lab."""
        return self._apply_checked(self.manifests(path), check=check)

    def helm_install(self, release: str, chart: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """`helm template` chart cục bộ của bài (thư mục hay `.tgz`), kiểm mọi object đã render (kể cả hook), rồi `helm upgrade
        --install` vào namespace của lab với cùng `args`. Không nhận `--namespace`, `--create-namespace`, `--post-renderer`.
        Hàm `lookup` hay giá trị ngẫu nhiên có thể làm bản cài khác bản đã render; ranh giới vẫn là quyền và Pod Security trong
        cluster."""
        self._require_entered()
        _kube_refuse_flags("helm", args)
        for arg in map(str, args):
            if arg.startswith("--") and arg[2:].split("=", 1)[0] in _HELM_INSTALL_FORBIDDEN or arg == "-n":
                raise ValueError(f"helm_install không nhận {arg}: lab tự đặt namespace, không dùng post-renderer")
        chart = Path(chart).resolve()
        if not chart.exists():
            raise ValueError(f"helm_install chỉ nhận chart cục bộ (thư mục hay .tgz), không thấy {chart}")
        rendered = self.helm("template", release, str(chart), "--namespace", self.namespace, *args, readonly=[chart])
        documents = _kube_flatten(self._parse(rendered.stdout, f"helm template {release}"))
        problems = kube_manifest_problems(documents, lab_id=self.id, namespace=self.namespace, allow=self.allow,
                                          cluster_kinds=self._cluster_kinds, api_group=self.api_group)
        if problems:
            pytest.fail(f"Chart {chart.name} bị từ chối trước khi cài:\n- " + "\n- ".join(problems))
        return self.helm("upgrade", "--install", release, str(chart), "--namespace", self.namespace, *args, readonly=[chart],
                         check=check)

    def _require_argocd(self, detail: str) -> None:
        if not self._argocd:
            pytest.skip(KUBE_SKIP_ARGOCD.format(name=self.name, detail=detail, setup=KUBE_ARGOCD_SETUP, key=KUBE_ARGOCD_KEY_SETUP))

    @property
    def repo_url(self) -> str:
        """URL nội bộ của repo git riêng của lab (`git://git.devops-git.svc.cluster.local/<namespace>.git`), dùng trong
        `spec.source.repoURL` của Application. Chỉ repo-server của ArgoCD đọc được (NetworkPolicy của `devops-git`)."""
        return kube_git_url(self.namespace)

    def argocd_project(self) -> str:
        """Bằng quyền admin tạo AppProject `devops-ex-<id>` trong namespace `argocd` (nhãn của lab, xoá trong `close()`):
        `sourceRepos` chỉ `repo_url`, `destinations` chỉ namespace của lab trên `https://kubernetes.default.svc`,
        `sourceNamespaces` chỉ namespace của lab, không có `clusterResourceWhitelist` (không object cluster-scoped nào), và
        `destinationServiceAccounts` buộc ArgoCD sync bằng chính ServiceAccount `devops-ex-learner` của lab (impersonation):
        object trong repo chỉ được tạo khi token của lab tạo được, qua đúng RBAC, policy và Pod Security của lab. Trả tên
        project để ghi vào `spec.project`."""
        self._require_entered()
        self._require_argocd("chưa có CRD applications.argoproj.io")
        project = {
            "apiVersion": "argoproj.io/v1alpha1", "kind": "AppProject",
            "metadata": {"name": self.namespace, "namespace": KUBE_ARGOCD_NAMESPACE, "labels": {_KUBE_LABEL_KEY: self.id}},
            "spec": {
                "description": f"Project riêng của lab {self.namespace}",
                "sourceRepos": [self.repo_url],
                "sourceNamespaces": [self.namespace],
                "destinations": [{"server": KUBE_IN_CLUSTER, "namespace": self.namespace}],
                "clusterResourceWhitelist": [],
                "destinationServiceAccounts": [{"server": KUBE_IN_CLUSTER, "namespace": self.namespace,
                                                "defaultServiceAccount": _KUBE_SA}],
            },
        }
        self._project = True
        result = self._admin.run("apply", "-f", "-", input=json.dumps(project))
        if result.returncode != 0:
            pytest.fail(f"Không tạo được AppProject {self.namespace}: {_output_tail(result)}")
        return self.namespace

    def _git_pods(self, running: bool = False) -> list[str]:
        argv = ["-n", KUBE_GIT_NAMESPACE, "get", "pods", "-l", "app.kubernetes.io/name=git", "-o", "jsonpath={.items[*].metadata.name}"]
        result = self._admin.run(*argv, *(["--field-selector=status.phase=Running"] if running else []))
        return [p for p in result.stdout.split() if re.fullmatch(r"[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?", p)] if result.returncode == 0 else []

    def _git_exec(self, pod: str, *argv: str) -> subprocess.CompletedProcess:
        return self._admin.run("-n", KUBE_GIT_NAMESPACE, "exec", pod, "-c", "git", "--", *argv, timeout=120)

    def gitops_repo(self, path: Path) -> str:
        """Chép tệp thường trong thư mục `path` (bỏ `.git`, không nhận symlink, không nhận tệp có khoá riêng age) vào một repo git
        mới của lab (`GitRepo`, `SAFE_GIT_CONFIG`, tác giả và ngày cố định), commit, rồi bằng quyền admin đẩy lên repo riêng
        `<namespace>.git` của git server (mỗi lần tối đa `KUBE_GITOPS_MAX_FILES` tệp và `KUBE_GITOPS_MAX_BYTES` byte, đếm theo byte
        thật đọc được lúc chép chứ không theo kích thước khai báo; bundle của cả lịch sử tối đa `KUBE_GITOPS_MAX_REPO_BYTES`;
        `kubectl cp` bundle vào pod rồi `git fetch` vào repo bare; git server chỉ cho đọc, không
        ai push được qua mạng). Gọi lại với nội dung mới là thêm một commit lên `main` (lịch sử giữ nguyên) và yêu cầu mọi
        Application của lab refresh ngay. `gitops_revision` là SHA của commit vừa đẩy. Trả `repo_url`; `close()` xoá repo."""
        self._require_entered()
        self._require_argocd("chưa có CRD applications.argoproj.io")
        source = Path(path).resolve()
        if not source.is_dir():
            raise ValueError(f"gitops_repo cần thư mục, không thấy {source}")
        files = []
        for item in sorted(source.rglob("*")):
            rel = item.relative_to(source)
            if ".git" in rel.parts:
                continue
            if item.is_symlink():
                pytest.fail(f"gitops_repo: {rel} là symlink; repo GitOps của bài chỉ nhận tệp thường")
            if item.is_file():
                files.append(rel)
        limit = (f"repo GitOps của bài tối đa {KUBE_GITOPS_MAX_FILES} tệp và {KUBE_GITOPS_MAX_BYTES // (1024 * 1024)} MiB mỗi lần "
                 "(git server dùng chung, lưu trong emptyDir)")
        if len(files) > KUBE_GITOPS_MAX_FILES:
            pytest.fail(f"gitops_repo: {len(files)} tệp; {limit}")
        contents: dict[Path, bytes] = {}
        remaining = KUBE_GITOPS_MAX_BYTES
        for rel in files:
            try:
                fd = os.open(source / rel, os.O_RDONLY | os.O_NOFOLLOW)
            except OSError as error:
                pytest.fail(f"gitops_repo: không đọc được {rel} như tệp thường ({error.strerror})")
            with os.fdopen(fd, "rb") as handle:
                data = handle.read(remaining + 1)
            if len(data) > remaining:
                pytest.fail(f"gitops_repo: vượt {KUBE_GITOPS_MAX_BYTES} byte khi chép tới {rel}; {limit}")
            remaining -= len(data)
            contents[rel] = data
        leaked = [str(rel) for rel, data in contents.items() if b"AGE-SECRET-KEY-" in data]
        if leaked:
            pytest.fail(f"gitops_repo: {', '.join(leaked)} chứa khoá riêng age (AGE-SECRET-KEY-...); khoá riêng không bao giờ được "
                        "commit vào repo, chỉ public key (age1...) nằm trong .sops.yaml")
        pods = self._git_pods(running=True)
        if not pods:
            pytest.skip(KUBE_SKIP_ARGOCD.format(name=self.name, detail=f"git server trong {KUBE_GIT_NAMESPACE} chưa chạy",
                                                setup=KUBE_ARGOCD_SETUP, key=KUBE_ARGOCD_KEY_SETUP))
        work, home = self.root / "gitops" / "repo", self.root / "gitops" / "home"
        if self._git_repo is None:
            work.mkdir(parents=True)
            home.mkdir(parents=True)
            self._git_repo = GitRepo(work, home)
            self._git_repo.out("init", "--quiet")
        else:
            for child in work.iterdir():
                if child.name != ".git":
                    shutil.rmtree(child) if child.is_dir() and not child.is_symlink() else child.unlink()
        for rel, data in contents.items():
            (work / rel).parent.mkdir(parents=True, exist_ok=True)
            (work / rel).write_bytes(data)
        repo = self._git_repo
        repo.out("add", "--all")
        repo.out("commit", "--quiet", "--allow-empty", "-m", f"{self.namespace}: {source.name}")
        bundle = self._admin.home / f"{self.namespace}.bundle"
        repo.out("bundle", "create", str(bundle), "main")
        if bundle.stat().st_size > KUBE_GITOPS_MAX_REPO_BYTES:
            size = bundle.stat().st_size
            bundle.unlink()
            if self.gitops_revision:
                repo.out("reset", "--quiet", "--soft", self.gitops_revision)
            pytest.fail(f"gitops_repo: lịch sử repo của lab đã {size} byte, vượt {KUBE_GITOPS_MAX_REPO_BYTES // (1024 * 1024)} MiB "
                        "cho cả lab (mỗi lần gọi là thêm một commit); gom thay đổi lại hay dùng lab mới")
        pod, remote, incoming = pods[0], f"{KUBE_GIT_ROOT}/{self.namespace}.git", f"/tmp/{self.namespace}.bundle"
        self._git_pushed = True
        try:
            result = self._admin.run("cp", str(bundle), f"{KUBE_GIT_NAMESPACE}/{pod}:{incoming}", "-c", "git", timeout=120)
            for argv in (("git", *SAFE_GIT_CONFIG, "init", "--quiet", "--bare", remote),
                         ("git", *SAFE_GIT_CONFIG, "-C", remote, "fetch", "--quiet", "--force", incoming, "+main:main")):
                if result.returncode == 0:
                    result = self._git_exec(pod, *argv)
            if result.returncode != 0:
                pytest.fail(f"Không đẩy được repo {self.namespace}.git lên git server: {_output_tail(result)}")
        finally:
            bundle.unlink(missing_ok=True)
            self._git_exec(pod, "rm", "-f", incoming)
        self.gitops_revision = repo.out("rev-parse", "HEAD")
        apps = [a for a in self.kubectl("get", "applications.argoproj.io", "-o", "name", check=False).stdout.split()
                if a.startswith("application.argoproj.io/")]
        if apps:
            self.kubectl("annotate", *apps, "argocd.argoproj.io/refresh=hard", "--overwrite", check=False)
        return self.repo_url

    def argocd_wait(self, app: str, *, health: str | None = "Healthy", sync: str | None = "Synced", timeout: float = 180,
                    latest: bool = True) -> dict:
        """Chờ Application `app` trong namespace của lab có `status.health.status == health` và `status.sync.status == sync`
        (`None` là bỏ qua điều kiện đó), không còn thao tác sync đang chạy, và (`latest`, sau `gitops_repo`) trạng thái tính trên
        đúng commit cuối cùng đã đẩy. Đọc bằng token của lab. Trả `status` của Application; quá `timeout` giây thì fail kèm
        health, sync, revision, thông điệp của thao tác sync và condition (không bao giờ in object hay giá trị Secret)."""
        self._require_entered()
        if not isinstance(app, str) or not _KUBE_ARGO_APP.fullmatch(app):
            raise ValueError(f"Tên Application {app!r} không hợp lệ")
        if not 1 <= timeout <= 900:
            raise ValueError(f"timeout {timeout!r} phải từ 1 tới 900 giây")
        deadline = time.monotonic() + timeout
        status: dict = {}
        while True:
            result = self.kubectl("get", "applications.argoproj.io", app, "-o", "json", check=False)
            try:
                status = (json.loads(result.stdout).get("status") or {}) if result.returncode == 0 else {}
            except ValueError:
                status = {}
            got_sync = status.get("sync") or {}
            revisions = [got_sync.get("revision"), *(got_sync.get("revisions") or [])]
            running = (status.get("operationState") or {}).get("phase") in ("Running", "Terminating")
            if (status and (health is None or (status.get("health") or {}).get("status") == health)
                    and (sync is None or got_sync.get("status") == sync) and not running
                    and (not latest or not self.gitops_revision or self.gitops_revision in revisions)):
                return status
            if time.monotonic() > deadline:
                break
            time.sleep(2)
        operation = status.get("operationState") or {}
        conditions = "; ".join(f"{c.get('type')}: {c.get('message')}" for c in status.get("conditions") or [] if isinstance(c, dict))
        detail = (f"health={(status.get('health') or {}).get('status')}, sync={(status.get('sync') or {}).get('status')}, "
                  f"revision={(status.get('sync') or {}).get('revision')}, commit cuối của gitops_repo={self.gitops_revision or '-'}, "
                  f"thao tác sync={operation.get('phase')}: {operation.get('message')}; condition: {conditions or '-'}")
        pytest.fail(f"Application {app} chưa đạt health={health}, sync={sync} sau {timeout:.0f}s ({detail[:DOCKER_LOG_CHARS]})")

    @property
    def age_public_key(self) -> str:
        """Public key (`age1...`) của khoá age dùng chung mà admin tạo cho ArgoCD, đọc từ ConfigMap
        `argocd/devops-sops-age-public`. Khoá riêng chỉ nằm trong Secret `argocd/devops-sops-age`, chỉ mount vào sidecar CMP
        `sops-kustomize` của repo-server; testkit không bao giờ đọc Secret đó, và không có gì của nó vào sandbox của người học."""
        self._require_entered()
        if self._age_public is None:
            result = self._admin.run("-n", KUBE_ARGOCD_NAMESPACE, "get", "configmap", KUBE_ARGOCD_AGE_PUBLIC, "-o",
                                     "jsonpath={.data.recipient}")
            value = result.stdout.strip()
            if result.returncode != 0 or not _KUBE_AGE_RECIPIENT.fullmatch(value):
                pytest.skip(KUBE_SKIP_ARGOCD.format(name=self.name, detail=f"thiếu ConfigMap {KUBE_ARGOCD_NAMESPACE}/"
                                                    f"{KUBE_ARGOCD_AGE_PUBLIC} có recipient age1...", setup=KUBE_ARGOCD_SETUP,
                                                    key=KUBE_ARGOCD_KEY_SETUP))
            self._age_public = value
        return self._age_public

    @property
    def sops_age_recipient(self) -> str:
        """Recipient cho `sops encrypt --age <recipient>` và `creation_rules[].age` của `.sops.yaml`: chính `age_public_key`."""
        return self.age_public_key

    def _sweep_gitops(self) -> None:
        """Dọn phần GitOps của lab bị giết trước khi kịp `close()` (SIGKILL): repo `devops-ex-<id>.git`, bundle trong pod git và
        AppProject `devops-ex-<id>` mà namespace `devops-ex-<id>` không còn. Lab đang chạy luôn có namespace nên không bị đụng."""
        listed = self._admin.run("get", "namespaces", "-o", "name")
        if listed.returncode != 0:
            return
        alive = {n.removeprefix("namespace/") for n in listed.stdout.split()}
        stale = lambda name: re.fullmatch(rf"{DOCKER_PREFIX}[0-9a-f]{{8}}", name) and name not in alive
        projects = self._admin.run("-n", KUBE_ARGOCD_NAMESPACE, "get", "appprojects.argoproj.io", "-l", _KUBE_LABEL_KEY, "-o", "name")
        for name in projects.stdout.split() if projects.returncode == 0 else []:
            project = name.split("/", 1)[-1]
            if stale(project):
                self._admin.run("-n", KUBE_ARGOCD_NAMESPACE, "delete", "appprojects.argoproj.io", project, "--ignore-not-found")
        for pod in self._git_pods(running=True):
            entries = self._git_exec(pod, "ls", "-1A", KUBE_GIT_ROOT, "/tmp")
            names = {line.removesuffix(".git").removesuffix(".bundle").rstrip(":").rsplit("/", 1)[-1]
                     for line in entries.stdout.split()}
            old = sorted(n for n in names if stale(n))
            if old:
                self._git_exec(pod, "rm", "-rf", *(f"{KUBE_GIT_ROOT}/{n}.git" for n in old), *(f"/tmp/{n}.bundle" for n in old))

    def _delete_applications(self, errors: list[str]) -> None:
        listed = self._admin.run("-n", self.namespace, "get", "applications.argoproj.io", "-o", "name", "--ignore-not-found")
        names = [n for n in listed.stdout.split() if n.startswith("application.argoproj.io/")]
        if not names:
            return
        result = self._admin.run("-n", self.namespace, "delete", *names, "--ignore-not-found", "--wait=true", "--timeout=60s",
                                 timeout=90)
        if result.returncode == 0:
            return
        for name in names:
            self._admin.run("-n", self.namespace, "patch", name, "--type=merge", "-p", '{"metadata":{"finalizers":null}}')
        result = self._admin.run("-n", self.namespace, "delete", *names, "--ignore-not-found", "--wait=true", "--timeout=30s",
                                 timeout=60)
        if result.returncode != 0:
            errors.append(f"xoá Application trong {self.namespace}: {_output_tail(result)}")

    def _release_argocd_hooks(self, errors: list[str]) -> None:
        """ArgoCD gắn finalizer `hook-finalizer` cho object hook (Job PreSync...) và chỉ gỡ khi hook kết thúc. Application bị xoá
        lúc hook còn chạy thì finalizer ở lại, namespace kẹt Terminating. Gỡ đúng finalizer đó trên object trong namespace của lab
        (hook được apply bằng token của lab nên chỉ thuộc các kind trong Role của lab)."""
        listed = self._admin.run("-n", self.namespace, "get", _KUBE_HOOK_KINDS, "-o", "json", "--ignore-not-found")
        if listed.returncode != 0:
            errors.append(f"liệt kê hook ArgoCD trong {self.namespace}: {_output_tail(listed)}")
            return
        try:
            items = json.loads(listed.stdout or "{}").get("items") or []
        except ValueError:
            items = []
        for item in items:
            metadata = item.get("metadata") or {}
            finalizers = metadata.get("finalizers") or []
            if KUBE_ARGOCD_HOOK_FINALIZER not in finalizers:
                continue
            group = item.get("apiVersion", "").rpartition("/")[0]
            ref = f"{item.get('kind', '').lower()}{'.' + group if group else ''}/{metadata.get('name')}"
            rest = [f for f in finalizers if f != KUBE_ARGOCD_HOOK_FINALIZER]
            result = self._admin.run("-n", self.namespace, "patch", ref, "--type=merge", "-p",
                                     json.dumps({"metadata": {"finalizers": rest or None}}))
            if result.returncode != 0:
                errors.append(f"gỡ {KUBE_ARGOCD_HOOK_FINALIZER} khỏi {ref}: {_output_tail(result)}")

    def _remove_gitops(self, errors: list[str]) -> None:
        if self._project:
            result = self._admin.run("-n", KUBE_ARGOCD_NAMESPACE, "delete", "appprojects.argoproj.io", "-l", self.label,
                                     "--ignore-not-found", "--wait=true", "--timeout=60s", timeout=90)
            if result.returncode != 0:
                errors.append(f"xoá AppProject {self.namespace}: {_output_tail(result)}")
        if self._git_pushed:
            for pod in self._git_pods():
                result = self._git_exec(pod, "rm", "-rf", f"{KUBE_GIT_ROOT}/{self.namespace}.git", f"/tmp/{self.namespace}.bundle")
                if result.returncode != 0:
                    errors.append(f"xoá repo {self.namespace}.git trong {KUBE_GIT_NAMESPACE}/{pod}: {_output_tail(result)}")

    def _worker(self, node) -> str:
        if not isinstance(node, str) or not _KUBE_WORKER.fullmatch(node) or node not in kind_nodes(self.name):
            raise ValueError(f"Chỉ nhận worker của cluster {self.name} (devops-lab-worker, devops-lab-worker<số>), không bao giờ "
                             f"control plane; không nhận {node!r}")
        return node

    @staticmethod
    def _spec(spec, required: set[str], optional: set[str], what: str) -> dict:
        if not isinstance(spec, dict) or not all(isinstance(k, str) for k in spec):
            raise ValueError(f"{what} cần dict")
        unknown, missing = sorted(set(spec) - required - optional), sorted(required - set(spec))
        if unknown or missing:
            raise ValueError(f"{what}: thiếu {missing}, không nhận {unknown}; chỉ có {sorted(required | optional)}")
        return spec

    def admin_local_pv(self, spec: dict) -> str:
        """Tạo bằng quyền admin một PersistentVolume `local` cho bài (thay cho PV hostPath mà bài không được tạo), từ spec đã
        kiểm từng trường: `name`, `capacity` (`1Gi`, `500Mi`), `node` (chỉ worker), tuỳ chọn `accessModes` (ReadWriteOnce,
        ReadWriteOncePod, ReadOnlyMany), `storageClassName` (không phải `standard`), `claim` (tên PVC trong namespace của lab,
        mặc định bằng `name`). Thư mục `/srv/devops-lab-pv/<id>/<name>` do testkit tạo trong node (không mount từ máy host),
        PV `devops-ex-<id>-<name>` có nhãn của lab, nodeAffinity vào đúng worker đó, reclaim Retain và `claimRef` giữ sẵn cho
        PVC `claim` của lab, nên namespace khác không bind được. `close()` xoá PV và thư mục. Trả tên PV."""
        self._require_entered()
        spec = self._spec(spec, {"name", "capacity", "node"}, {"accessModes", "storageClassName", "claim"}, "admin_local_pv")
        name, capacity = spec["name"], spec["capacity"]
        if not isinstance(name, str) or not _KUBE_NAME.fullmatch(name):
            raise ValueError(f"name {name!r} phải là chữ thường, số, '-' (tối đa 42 ký tự)")
        if not isinstance(capacity, str) or not _KUBE_QUANTITY.fullmatch(capacity):
            raise ValueError(f"capacity {capacity!r} phải dạng 1Gi hay 500Mi")
        modes = spec.get("accessModes", ["ReadWriteOnce"])
        if not isinstance(modes, list) or not modes or not set(modes) <= {"ReadWriteOnce", "ReadWriteOncePod", "ReadOnlyMany"}:
            raise ValueError(f"accessModes {modes!r} chỉ nhận ReadWriteOnce, ReadWriteOncePod, ReadOnlyMany")
        storage_class = spec.get("storageClassName", "")
        if not isinstance(storage_class, str) or storage_class == "standard" or (storage_class and not _KUBE_NAME.fullmatch(storage_class)):
            raise ValueError(f"storageClassName {storage_class!r} không hợp lệ (không dùng standard của local-path)")
        claim = spec.get("claim", name)
        if not isinstance(claim, str) or not _KUBE_NAME.fullmatch(claim):
            raise ValueError(f"claim {claim!r} phải là tên PVC hợp lệ")
        node = self._worker(spec["node"])
        path = f"{KUBE_LOCAL_PV_ROOT}/{self.id}/{name}"
        self._local_nodes.add(node)
        for argv in (("mkdir", "-p", path), ("chmod", "0777", path)):
            made = kind_node_exec(node, *argv)
            if made.returncode != 0:
                pytest.fail(f"Không tạo được {path} trong {node}: {made.stderr.strip()}")
        volume = {"apiVersion": "v1", "kind": "PersistentVolume",
                  "metadata": {"name": f"{self.namespace}-{name}", "labels": {_KUBE_LABEL_KEY: self.id}},
                  "spec": {"capacity": {"storage": capacity}, "accessModes": list(modes), "volumeMode": "Filesystem",
                           "persistentVolumeReclaimPolicy": "Retain", "storageClassName": storage_class, "local": {"path": path},
                           "claimRef": {"apiVersion": "v1", "kind": "PersistentVolumeClaim", "namespace": self.namespace,
                                        "name": claim},
                           "nodeAffinity": {"required": {"nodeSelectorTerms": [{"matchExpressions": [
                               {"key": "kubernetes.io/hostname", "operator": "In", "values": [node]}]}]}}}}
        result = self._admin.run("apply", "-f", "-", input=json.dumps(volume))
        if result.returncode != 0:
            pytest.fail(f"Không tạo được PV {volume['metadata']['name']}: {_output_tail(result)}")
        return volume["metadata"]["name"]

    def can_i(self, verb: str, resource: str, *, serviceaccount: str | None = None, user: str | None = None, groups=(),
              subresource: str | None = None, all_namespaces: bool = False) -> bool:
        """`kubectl auth can-i` bằng quyền admin, chỉ đọc (hỏi SubjectAccessReview, không đổi gì), cho một ServiceAccount của lab
        (`serviceaccount`, thành `system:serviceaccount:<namespace của lab>:<tên>`) hoặc một user (`user`, cộng `groups`). Token của
        lab không có `impersonate` nên `--as` bị từ chối với người học; testkit hỏi hộ. Mặc định trong namespace của lab;
        `all_namespaces` hỏi quyền trên mọi namespace (`--all-namespaces`)."""
        self._require_entered()
        if (serviceaccount is None) == (user is None):
            raise ValueError("can_i cần đúng một trong serviceaccount hoặc user")
        if not isinstance(verb, str) or not re.fullmatch(r"[a-z*]{1,30}", verb):
            raise ValueError(f"verb {verb!r} không hợp lệ")
        if not isinstance(resource, str) or not re.fullmatch(r"[a-z0-9*][-a-z0-9.*/]{0,100}", resource):
            raise ValueError(f"resource {resource!r} không hợp lệ")
        if subresource is not None and (not isinstance(subresource, str) or not re.fullmatch(r"[a-z][a-z0-9]{0,40}", subresource)):
            raise ValueError(f"subresource {subresource!r} không hợp lệ")
        identity = re.compile(r"[A-Za-z0-9][-A-Za-z0-9@._:]{0,100}")
        if serviceaccount is not None and (not isinstance(serviceaccount, str) or not _KUBE_NAME.fullmatch(serviceaccount)):
            raise ValueError(f"serviceaccount {serviceaccount!r} phải là tên ServiceAccount trong namespace của lab")
        if user is not None and (not isinstance(user, str) or not identity.fullmatch(user)):
            raise ValueError(f"user {user!r} không hợp lệ")
        for group in groups:
            if not isinstance(group, str) or not identity.fullmatch(group):
                raise ValueError(f"group {group!r} không hợp lệ")
        argv = ["auth", "can-i", verb, resource, "--all-namespaces" if all_namespaces else "-n", *([] if all_namespaces else
                                                                                                    [self.namespace])]
        if subresource:
            argv.append(f"--subresource={subresource}")
        who = f"system:serviceaccount:{self.namespace}:{serviceaccount}" if serviceaccount else user
        argv += [f"--as={who}", *(f"--as-group={group}" for group in groups)]
        result = self._admin.run(*argv)
        answer = result.stdout.strip().splitlines()[-1:] if result.stdout.strip() else []
        if answer not in (["yes"], ["no"]):
            pytest.fail(f"kubectl {' '.join(argv)} không trả yes/no: {_output_tail(result)}")
        return answer == ["yes"]

    def _lock_nodes(self) -> None:
        if self._node_lock is not None:
            return
        import fcntl

        path = _kube_node_paths()[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(path, "a+")
        deadline = time.monotonic() + KUBE_NODE_LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    handle.close()
                    pytest.fail(f"node_action chờ quá {KUBE_NODE_LOCK_TIMEOUT}s: một lab khác đang cordon, drain hay taint worker "
                                f"({path}); bài dùng node_action không chạy song song")
                time.sleep(min(2, KUBE_NODE_LOCK_TIMEOUT / 4))
        self._node_lock = handle
        failed = _kube_node_undo_present(self._admin)
        if failed:
            pytest.fail("Không hoàn tác được thao tác node còn sót của lần chạy trước: "
                        + "; ".join(" ".join(_kube_node_undo(e)) for e in failed))

    def _record_node(self, entry: dict, keep: bool) -> None:
        actions = [e for e in _kube_node_state_read() if e != entry]
        _kube_node_state_write(actions + [entry] if keep else actions)

    def _wait_shared_ready(self, errors: list[str]) -> None:
        deadline = time.monotonic() + KUBE_SHARED_READY_TIMEOUT
        waiting: list[str] = []
        while True:
            waiting = []
            for namespace in KUBE_SHARED_NAMESPACES:
                result = self._admin.run("-n", namespace, "get", "deployments", "-o", "json")
                try:
                    items = json.loads(result.stdout).get("items", []) if result.returncode == 0 and result.stdout.strip() else []
                except ValueError:
                    items = []
                waiting += [f"{namespace}/{item['metadata']['name']}" for item in items
                            if ((item.get("status") or {}).get("availableReplicas") or 0) < ((item.get("spec") or {}).get("replicas", 1) or 0)]
            if not waiting or time.monotonic() > deadline:
                break
            time.sleep(2)
        if waiting:
            errors.append(f"sau khi hoàn tác node, thành phần dùng chung chưa available lại sau {KUBE_SHARED_READY_TIMEOUT}s: "
                          f"{', '.join(waiting)}")

    def node_action(self, spec: dict, *, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
        """Thao tác node bằng quyền admin từ spec đã kiểm, chỉ trên worker, không bao giờ control plane: `{"action": "cordon" |
        "uncordon" | "drain", "node": ...}` (drain luôn `--ignore-daemonsets --delete-emptydir-data`, có eviction, không bao giờ
        `--disable-eviction`), `{"action": "taint" | "untaint", "node": ..., "taint": {"key", "value", "effect"}}` (key không
        thuộc `kubernetes.io`, `k8s.io`). `close()` uncordon mọi node lab đã cordon hay drain và gỡ mọi taint lab đã thêm.
        Trạng thái cordon và taint là của node, không đếm theo lab, nên lần `node_action` đầu tiên giữ khoá
        `~/.cache/devops-track/kube-nodes.lock` (flock, chờ tối đa `KUBE_NODE_LOCK_TIMEOUT`) tới khi `close()` hoàn tác xong: hai
        lab dùng `node_action` không bao giờ chạy chồng nhau, kể cả ở hai tiến trình pytest. Test dùng `node_action` mang marker
        `kube_nodes`. Sau khi hoàn tác, `close()` chờ Deployment trong `KUBE_SHARED_NAMESPACES` (CoreDNS, local-path, Gateway,
        metrics-server, ArgoCD, git server) available lại, để bài chạy sau không skip vì thành phần dùng chung đang dời node. `timeout` là
        `--timeout` của drain (10 tới 120 giây).

        Mỗi thao tác được ghi vào `kube-nodes.state.json` cạnh khoá (chỉ đọc, ghi, xoá khi đang giữ khoá) trước khi chạy và xoá khi
        đã hoàn tác; lab bị SIGKILL thì `require_cluster` của bài sau (khi khoá rảnh) hay lần `node_action` sau giữ khoá, so tệp với
        trạng thái thật của node và hoàn tác phần còn trên cluster rồi chạy tiếp; chỉ skip kèm lệnh khi hoàn tác lỗi. Giới hạn: đường
        dẫn khoá và tệp trạng thái theo `XDG_CACHE_HOME` (hai tiến trình đặt `XDG_CACHE_HOME` khác nhau không thấy khoá của nhau);
        hai lab lồng nhau trong cùng một tiến trình cùng gọi `node_action` thì lab trong chờ khoá của lab ngoài tới hết
        `KUBE_NODE_LOCK_TIMEOUT` rồi fail; cordon hay taint ghi trong tệp mà vẫn còn trên node bị coi là của lab bị ngắt, kể cả khi
        người dùng tự đặt lại đúng cordon, taint đó sau khi lab chết."""
        self._require_entered()
        spec = self._spec(spec, {"action", "node"}, {"taint"}, "node_action")
        action = spec["action"]
        if action not in ("cordon", "uncordon", "drain", "taint", "untaint"):
            raise ValueError(f"action {action!r} chỉ nhận cordon, uncordon, drain, taint, untaint")
        node = self._worker(spec["node"])
        if (action in ("taint", "untaint")) != ("taint" in spec):
            raise ValueError("taint chỉ đi kèm action taint hay untaint, và hai action đó cần taint")
        if not isinstance(timeout, int) or not 10 <= timeout <= 120:
            raise ValueError(f"timeout của drain {timeout!r} phải là số giây từ 10 tới 120")
        taint_spec = None
        if action in ("taint", "untaint"):
            taint = self._spec(spec["taint"], {"key", "effect"}, {"value"}, "taint")
            key, value, effect = taint["key"], taint.get("value", ""), taint["effect"]
            if (not isinstance(key, str) or not _KUBE_TAINT_KEY.fullmatch(key) or "kubernetes.io" in key or "k8s.io" in key
                    or not isinstance(value, str) or not _KUBE_TAINT_VALUE.fullmatch(value) or effect not in _KUBE_TAINT_EFFECTS):
                raise ValueError(f"taint {taint!r} không hợp lệ (key riêng của bài, effect {', '.join(_KUBE_TAINT_EFFECTS)})")
            taint_spec = (key, effect)
        self._lock_nodes()
        if taint_spec:
            argv = ["taint", "nodes", node, f"{key}={value}:{effect}" if value else f"{key}:{effect}"]
            if action == "untaint":
                argv[-1] = f"{key}:{effect}-"
            else:
                self._taints.add((node, key, effect))
                self._record_node({"node": node, "taint": [key, effect]}, True)
        elif action == "drain":
            self._cordoned.add(node)
            self._record_node({"node": node, "cordon": True}, True)
            argv = ["drain", node, "--ignore-daemonsets", "--delete-emptydir-data", f"--timeout={timeout}s"]
        else:
            if action == "cordon":
                self._cordoned.add(node)
                self._record_node({"node": node, "cordon": True}, True)
            argv = [action, node]
        result = self._admin.run(*argv, timeout=timeout + 60)
        if result.returncode == 0 and action == "untaint":
            self._taints.discard((node, key, effect))
            self._record_node({"node": node, "taint": [key, effect]}, False)
        if result.returncode == 0 and action == "uncordon":
            self._cordoned.discard(node)
            self._record_node({"node": node, "cordon": True}, False)
        return self._checked("kubectl", argv, result, check)

    def _released_volumes(self) -> list[str]:
        result = self._admin.run("get", "pv", "-o", "json")
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return [item["metadata"]["name"] for item in json.loads(result.stdout).get("items", [])
                if ((item.get("spec") or {}).get("claimRef") or {}).get("namespace") == self.namespace
                and ((item.get("metadata") or {}).get("labels") or {}).get(_KUBE_LABEL_KEY) != self.id]

    def _restore_nodes(self, errors: list[str]) -> None:
        for node, key, effect in sorted(self._taints):
            result = self._admin.run("taint", "nodes", node, f"{key}:{effect}-")
            if result.returncode != 0 and "not found" not in result.stderr:
                errors.append(f"gỡ taint {key}:{effect} khỏi {node}: {_output_tail(result)}")
            else:
                self._record_node({"node": node, "taint": [key, effect]}, False)
        for node in sorted(self._cordoned):
            result = self._admin.run("uncordon", node)
            if result.returncode != 0:
                errors.append(f"uncordon {node}: {_output_tail(result)}")
            else:
                self._record_node({"node": node, "cordon": True}, False)
        if self._node_lock is not None:
            self._wait_shared_ready(errors)

    def close(self) -> None:
        """Gỡ thao tác node của lab, xoá Application của ArgoCD trong namespace của lab (gỡ finalizer nếu ArgoCD không xử lý kịp)
        và gỡ `hook-finalizer` khỏi hook còn dở,
        xoá namespace, chờ rồi xoá PV có `claimRef` trỏ namespace của lab (PV do local-path tạo cho PVC của bài không mang nhãn),
        xoá object cluster-scoped có nhãn của lab, AppProject của lab và repo git của lab trên git server, xoá thư mục PV local
        trong worker."""
        import warnings

        errors = []
        try:
            if self._admin is not None and self._created:
                self._restore_nodes(errors)
                if self._argocd:
                    self._delete_applications(errors)
                    self._release_argocd_hooks(errors)
                result = self._admin.run("delete", "namespace", self.namespace, "--ignore-not-found", "--wait=true",
                                         f"--timeout={KUBE_CLEANUP_TIMEOUT}s", timeout=KUBE_CLEANUP_TIMEOUT + 30)
                if result.returncode != 0:
                    errors.append(f"xoá namespace {self.namespace}: {_output_tail(result)}")
                deadline = time.monotonic() + 60
                while self._released_volumes() and time.monotonic() < deadline:
                    time.sleep(1)
                left = self._released_volumes()
                if left:
                    result = self._admin.run("delete", "pv", *left, "--ignore-not-found", "--wait=true",
                                             f"--timeout={KUBE_CLEANUP_TIMEOUT}s", timeout=KUBE_CLEANUP_TIMEOUT + 30)
                    if result.returncode != 0:
                        errors.append(f"xoá PV của namespace {self.namespace}: {_output_tail(result)}")
                kinds = ",".join(self._admin.cluster_resources())
                result = self._admin.run("delete", kinds, "-l", self.label, "--ignore-not-found", "--wait=true",
                                         f"--timeout={KUBE_CLEANUP_TIMEOUT}s", timeout=KUBE_CLEANUP_TIMEOUT + 30)
                if result.returncode != 0:
                    errors.append(f"xoá object cluster-scoped nhãn {self.label}: {_output_tail(result)}")
                self._remove_gitops(errors)
                for node in sorted(self._local_nodes):
                    removed = kind_node_exec(node, "rm", "-rf", f"{KUBE_LOCAL_PV_ROOT}/{self.id}")
                    if removed.returncode != 0:
                        errors.append(f"xoá {KUBE_LOCAL_PV_ROOT}/{self.id} trong {node}: {removed.stderr.strip()}")
        except (Exception, pytest.fail.Exception, pytest.skip.Exception) as error:
            errors.append(str(error))
        finally:
            self._kubeconfig_text = ""
            if self._node_lock is not None:
                self._node_lock.close()
                self._node_lock = None
            if self.root is not None:
                shutil.rmtree(self.root, ignore_errors=True)
        if errors:
            self.cleanup_error = (f"KubeLab {self.namespace} dọn chưa hết; xoá tay bằng kubectl delete namespace {self.namespace} "
                                  f"và kubectl delete <loại> -l {self.label}:\n" + "\n".join(errors))
            warnings.warn(self.cleanup_error, UserWarning)



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
    def require_vault_devops() -> str:
        """Skip khi `vault-devops` (profile `devops`) chưa chạy hoặc cổng của nó là server khác; trả địa chỉ. Test dùng qua
        `vault_env`."""
        if not service_up("vault-devops"):
            pytest.skip(f"Vault dev của track DevOps chưa chạy. Bật bằng: {VAULT_DEVOPS_START}")
        health = _vault_health(vault_devops_address())
        if not isinstance(health, dict) or health.get("initialized") is not True or health.get("sealed") is not False:
            pytest.skip(
                f"Cổng {_port('vault-devops')} đang mở nhưng không phải vault-devops (GET /v1/sys/health không trả Vault đã "
                f"unseal). Đổi DEVOPS_VAULT_PORT trong setup/.env rồi chạy: {VAULT_DEVOPS_START}")
        return vault_devops_address()

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
    def require_cluster(name: str = KIND_CLUSTER) -> None:
        """Skip, mỗi trường hợp một thông báo, khi Docker tắt, chưa có cluster kind `name`, node container đang dừng, hay API
        server không trả `ok` cho `kubectl get --raw /readyz` trong `KUBE_READY_TIMEOUT` giây. Lệnh kubectl chạy trong
        sandbox với kubeconfig tạm lấy bằng `kind get kubeconfig`, không đọc `KUBECONFIG` hay `~/.kube` của người học."""
        _require_cluster_up(name)
        with tempfile.TemporaryDirectory(prefix=f"{DOCKER_PREFIX}ready-") as tmp:
            admin = _KubeAdmin(Path(tmp), name)
            _kube_ready(admin, name)
            _kube_check_node_leftovers(admin)

    @staticmethod
    def require_gateway(name: str = KIND_CLUSTER) -> None:
        """Skip kèm lệnh cài khi cluster chưa có Gateway dùng chung: CRD của Gateway API, IngressClass `devops-traefik`,
        Deployment traefik có pod available trong `devops-gateway`, Gateway `devops-gateway/public` Programmed. Admin cài một lần
        từ `setup/kind/gateway/`; test không bao giờ cài."""
        _require_cluster_up(name)
        with tempfile.TemporaryDirectory(prefix=f"{DOCKER_PREFIX}gateway-") as tmp:
            admin = _KubeAdmin(Path(tmp), name)
            checks = (
                ("CRD httproutes.gateway.networking.k8s.io", ("get", "crd", "httproutes.gateway.networking.k8s.io", "-o", "name"),
                 lambda out: "httproutes" in out),
                (f"IngressClass {KUBE_INGRESS_CLASS}", ("get", "ingressclass", KUBE_INGRESS_CLASS, "-o", "name"),
                 lambda out: KUBE_INGRESS_CLASS in out),
                ("Deployment traefik chưa có pod available", ("-n", KUBE_GATEWAY_NAMESPACE, "get", "deployment", "traefik", "-o",
                                                              "jsonpath={.status.availableReplicas}"),
                 lambda out: out.strip() not in ("", "0")),
                (f"Gateway {KUBE_GATEWAY_NAMESPACE}/{KUBE_GATEWAY_NAME} chưa Programmed",
                 ("-n", KUBE_GATEWAY_NAMESPACE, "get", "gateway", KUBE_GATEWAY_NAME, "-o",
                  "jsonpath={.status.conditions[?(@.type=='Programmed')].status}"), lambda out: out.strip() == "True"),
            )
            for what, args, ok in checks:
                result = admin.run(*args)
                if result.returncode != 0 or not ok(result.stdout):
                    pytest.skip(KUBE_SKIP_GATEWAY.format(name=name, detail=f"thiếu {what}", setup=KUBE_GATEWAY_SETUP))

    @staticmethod
    def require_metrics(name: str = KIND_CLUSTER) -> None:
        """Skip kèm lệnh cài khi cluster chưa có metrics-server dùng được: Deployment `kube-system/metrics-server` có pod
        available, APIService `v1beta1.metrics.k8s.io` Available, và `/apis/metrics.k8s.io/v1beta1/nodes` đã có số liệu. Admin cài
        một lần từ `setup/kind/metrics-server/` (manifest ghim của release, cờ `--kubelet-insecure-tls`, image nạp sẵn); test không
        bao giờ cài."""
        _require_cluster_up(name)
        with tempfile.TemporaryDirectory(prefix=f"{DOCKER_PREFIX}metrics-") as tmp:
            admin = _KubeAdmin(Path(tmp), name)

            def has_nodes(out: str) -> bool:
                try:
                    return bool(json.loads(out).get("items"))
                except ValueError:
                    return False

            checks = (
                ("Deployment metrics-server chưa có pod available", ("-n", "kube-system", "get", "deployment", "metrics-server", "-o",
                                                                     "jsonpath={.status.availableReplicas}"),
                 lambda out: out.strip() not in ("", "0")),
                ("APIService v1beta1.metrics.k8s.io chưa Available", ("get", "apiservice", "v1beta1.metrics.k8s.io", "-o",
                                                                      "jsonpath={.status.conditions[?(@.type=='Available')].status}"),
                 lambda out: out.strip() == "True"),
                ("metrics.k8s.io chưa có số liệu của node", ("get", "--raw", "/apis/metrics.k8s.io/v1beta1/nodes"), has_nodes),
            )
            for what, args, ok in checks:
                result = admin.run(*args)
                if result.returncode != 0 or not ok(result.stdout):
                    pytest.skip(KUBE_SKIP_METRICS.format(name=name, detail=what, setup=KUBE_METRICS_SETUP))

    @staticmethod
    def require_argocd(name: str = KIND_CLUSTER) -> None:
        """Skip kèm lệnh cài khi cluster chưa có ArgoCD dùng chung đúng cấu hình của track: CRD `applications.argoproj.io`,
        `application.namespaces: devops-ex-*` (Application trong namespace của lab), sync bằng impersonation, AppProject
        `default` đã khoá, application-controller sẵn sàng, repo-server (kèm sidecar CMP `sops-kustomize`, cần Secret
        `argocd/devops-sops-age`) available, ConfigMap `argocd/devops-sops-age-public` có recipient `age1...`, git server
        `devops-git/git` available. Không đọc Secret chứa khoá riêng. Admin cài một lần từ `setup/kind/argocd/`; test không bao
        giờ cài."""
        _require_cluster_up(name)
        with tempfile.TemporaryDirectory(prefix=f"{DOCKER_PREFIX}argocd-") as tmp:
            admin = _KubeAdmin(Path(tmp), name)
            ns = ("-n", KUBE_ARGOCD_NAMESPACE)
            checks = (
                ("CRD applications.argoproj.io", ("get", "crd", "applications.argoproj.io", "-o", "name"),
                 lambda out: "applications.argoproj.io" in out),
                ("argocd-cmd-params-cm chưa có application.namespaces: devops-ex-*",
                 (*ns, "get", "configmap", "argocd-cmd-params-cm", "-o", r"jsonpath={.data.application\.namespaces}"),
                 lambda out: "devops-ex-*" in [part.strip() for part in out.split(",")]),
                ("argocd-cm chưa bật application.sync.impersonation.enabled",
                 (*ns, "get", "configmap", "argocd-cm", "-o", r"jsonpath={.data.application\.sync\.impersonation\.enabled}"),
                 lambda out: out.strip() == "true"),
                ("AppProject default chưa khoá (20-default-project.yaml)",
                 (*ns, "get", "appprojects.argoproj.io", "default", "-o", "jsonpath={.spec.sourceRepos}{.spec.destinations}"),
                 lambda out: out.strip() in ("", "[]", "[][]")),
                ("application-controller chưa sẵn sàng", (*ns, "get", "statefulset", "argocd-application-controller", "-o",
                                                          "jsonpath={.status.readyReplicas}"),
                 lambda out: out.strip() not in ("", "0")),
                (f"repo-server chưa có pod available (thiếu Secret {KUBE_ARGOCD_NAMESPACE}/{KUBE_ARGOCD_AGE_SECRET} thì pod kẹt ở "
                 "ContainerCreating)", (*ns, "get", "deployment", "argocd-repo-server", "-o", "jsonpath={.status.availableReplicas}"),
                 lambda out: out.strip() not in ("", "0")),
                (f"thiếu ConfigMap {KUBE_ARGOCD_NAMESPACE}/{KUBE_ARGOCD_AGE_PUBLIC} có recipient age1...",
                 (*ns, "get", "configmap", KUBE_ARGOCD_AGE_PUBLIC, "-o", "jsonpath={.data.recipient}"),
                 lambda out: bool(_KUBE_AGE_RECIPIENT.fullmatch(out.strip()))),
                (f"git server {KUBE_GIT_NAMESPACE}/git chưa có pod available",
                 ("-n", KUBE_GIT_NAMESPACE, "get", "deployment", "git", "-o", "jsonpath={.status.availableReplicas}"),
                 lambda out: out.strip() not in ("", "0")),
            )
            for what, args, ok in checks:
                result = admin.run(*args)
                if result.returncode != 0 or not ok(result.stdout):
                    pytest.skip(KUBE_SKIP_ARGOCD.format(name=name, detail=what, setup=KUBE_ARGOCD_SETUP, key=KUBE_ARGOCD_KEY_SETUP))

    @staticmethod
    def require_kind_images(*images: str, name: str = KIND_CLUSTER) -> None:
        """Skip khi một image trong `images` chưa nạp vào mọi worker của cluster (`kind load`), để pod không bao giờ phải kéo
        image từ Internet lúc chấm. Kiểm cluster trước (`require_cluster` cho các thông báo về Docker, cluster, node). Thông
        báo skip có đúng lệnh `kind load docker-image` cho image còn thiếu, cộng lệnh build khi thiếu image Olist Shop."""
        _require_cluster_up(name)
        missing = kind_images_missing(images, name)
        if missing:
            wanted = [image for image in images if any(image in lost for lost in missing.values())]
            detail = "; ".join(f"{node} thiếu {', '.join(lost)}" for node, lost in missing.items())
            build = f" (build trước: {KUBE_OLIST_BUILD})" if KUBE_IMAGES["olist"] in wanted else ""
            pytest.skip(KUBE_SKIP_IMAGES.format(name=name, detail=detail, load=KUBE_LOAD.format(images=" ".join(wanted), name=name),
                                                build=build))
