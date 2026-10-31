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
    with DockerLab() as lab: lab.start("web", "nginx:1.30.6-alpine", ports=[80])  # container riêng, tự dọn
    run_sandboxed(cmd, writable=[tmp_path], cwd=tmp_path, env={...})  # bài DevOps: chạy script trong bwrap
"""

from __future__ import annotations

import importlib.util
import linecache
import os
import pwd
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
_PORT_TAKEN = ("port is already allocated", "address already in use")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _docker(*args: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


class DockerLab:
    """Network và container riêng của một test, luôn được dọn trong `close()` (gọi ở `finally` hoặc `with`).

    Mọi container: tên `devops-ex-<uuid8>-<alias>`, nhãn `devops-ex=1`, `--rm`, ghim CPU theo `docker_cpu_args()`,
    cổng chỉ mở trên 127.0.0.1 ở cổng trống do test chọn, mount chỉ đọc. Không đụng container hay network nào khác.
    """

    def __init__(self) -> None:
        self.id = uuid.uuid4().hex[:8]
        self.network = f"{DOCKER_PREFIX}{self.id}"
        self.names: list[str] = []
        self.ports: dict[str, dict[int, int]] = {}
        self._network_created = False

    def __enter__(self) -> "DockerLab":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def open(self) -> None:
        self._network_created = True
        result = _docker("network", "create", "--label", DOCKER_LABEL, self.network)
        if result.returncode != 0:
            pytest.fail(f"Không tạo được docker network {self.network}: {result.stderr.strip()}")

    def name(self, alias: str) -> str:
        return f"{self.network}-{alias}"

    def run_args(self, alias: str, image: str, *command: str, detach: bool = True, mounts=(), publish=(),
                 env: dict[str, str] | None = None, entrypoint: str | None = None) -> list[str]:
        args = ["docker", "run", "--rm", *(["-d"] if detach else [])]
        args += ["--name", self.name(alias), "--label", DOCKER_LABEL, "--network", self.network, "--network-alias", alias]
        args += docker_cpu_args()
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

    def start(self, alias: str, image: str, *command: str, ports=(), mounts=(), env=None, entrypoint=None) -> str:
        """Chạy container nền; `ports` là cổng trong container, cổng host lấy bằng `lab.port(alias, cổng)`."""
        name = self._track(alias)
        result = None
        for _ in range(3):
            publish = [(port, free_port()) for port in ports]
            args = self.run_args(alias, image, *command, mounts=mounts, publish=publish, env=env, entrypoint=entrypoint)
            result = subprocess.run(args, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                self.ports[alias] = dict(publish)
                return name
            _docker("rm", "-f", name)
            if not any(text in result.stderr for text in _PORT_TAKEN):
                break
        pytest.fail(f"docker run {alias} ({image}) lỗi: {result.stderr.strip()}")

    def run_once(self, alias: str, image: str, *command: str, mounts=(), entrypoint=None,
                 timeout: float = 60) -> subprocess.CompletedProcess:
        """Chạy container tới khi xong (vd. `nginx -t`) và trả kết quả; container vẫn được dọn nếu quá giờ."""
        self._track(alias)
        args = self.run_args(alias, image, *command, detach=False, mounts=mounts, entrypoint=entrypoint)
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"Container {alias} chạy quá {timeout} giây")

    def port(self, alias: str, container_port: int) -> int:
        return self.ports[alias][container_port]

    def logs(self, alias: str) -> str:
        result = _docker("logs", self.name(alias))
        return result.stdout + result.stderr

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
                pytest.fail(f"Container {alias} đã dừng trước khi in '{text}'")
            time.sleep(0.2)
        pytest.fail(f"Container {alias} không in '{text}' sau {timeout} giây. Log:\n{self.logs(alias)[-2000:]}")

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
                pytest.fail(f"Container {alias} đã dừng ngay sau khi khởi động")
            time.sleep(0.2)
        pytest.fail(f"{url} không trả lời sau {timeout} giây. Log của {alias}:\n{self.logs(alias)[-2000:]}")

    def close(self) -> None:
        for name in self.names:
            try:
                _docker("rm", "-f", name)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if self._network_created:
            try:
                _docker("network", "rm", self.network)
            except (OSError, subprocess.TimeoutExpired):
                pass


_BWRAP_ISOLATION = ["--unshare-user", "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--die-with-parent", "--new-session"]
_UNSAFE_ENV = re.compile(r"^(?:BASH_ENV|ENV|BASH_FUNC_.*|LD_PRELOAD|LD_LIBRARY_PATH|SHELLOPTS|BASHOPTS|PROMPT_COMMAND|PS4)$")
SANDBOX_SKIP = (
    "Bài này chạy script của bạn trong sandbox bubblewrap (bwrap) để một script viết sai không xoá hay sửa được tệp "
    "nào ngoài thư mục tạm của test; test từ chối chạy khi không có sandbox. {reason} Cài: sudo apt install bubblewrap "
    "(Fedora: sudo dnf install bubblewrap). Xem setup/DEVOPS-TOOLS.md"
)


def _real_homes() -> list[Path]:
    homes = {Path(pwd.getpwuid(os.getuid()).pw_dir), Path(os.path.expanduser("~"))}
    return sorted(h.resolve() for h in homes if h.is_dir())


def _base_flags(bwrap: str) -> list[str]:
    """Cờ chung cho lần thử và lần chạy thật: / chỉ đọc, /tmp và /run là tmpfs rỗng (che socket docker, D-Bus)."""
    args = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", "/run"]
    for home in _real_homes():
        docker_dir = home / ".docker"
        if docker_dir.is_dir() and not docker_dir.is_relative_to("/tmp"):
            args += ["--tmpfs", str(docker_dir)]
    return args


def sandbox_ready() -> str | None:
    """Trả None khi bwrap tạo được sandbox với đúng bộ cờ của lần chạy thật, ngược lại trả lý do."""
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return "Chưa cài bwrap."
    probe = _run_tool([*_base_flags(bwrap), *_BWRAP_ISOLATION, "--clearenv", "--", "true"])
    if probe is None or probe.returncode != 0:
        detail = (probe.stderr.strip() if probe is not None else "") or "không rõ lỗi"
        return f"bwrap có nhưng không tạo được sandbox ({detail}); có thể kernel chặn user namespace không đặc quyền."
    return None


def _clean_env(env: dict[str, str], home: Path) -> dict[str, str]:
    base = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": str(home), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    base.update({k: v for k, v in env.items() if not _UNSAFE_ENV.match(k)})
    return base


def _hidden_by_tmpfs() -> list[Path]:
    hidden = (Path("/tmp"), Path("/run"))
    candidates = {ROOT, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), Path(sys.executable).resolve().parent}
    return sorted(p for p in candidates if any(p.is_relative_to(h) and p != h for h in hidden))


def sandbox_command(cmd: list, *, writable: list[Path], cwd: Path, env: dict[str, str]) -> list[str]:
    """argv chạy `cmd` trong bwrap: / chỉ đọc, /tmp và /run là tmpfs rỗng, ~/.docker bị che, chỉ `writable` ghi được,
    môi trường dựng lại từ đầu.

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
    def require_tool(name: str, min_version: str | None = None) -> None:
        if not shutil.which(name):
            pytest.skip(f"Chưa cài {name}. Xem setup/DEVOPS-TOOLS.md")
        if min_version:
            have = tool_version(name)
            need = parse_version(min_version)
            if have is None or (need is not None and have < need):
                shown = ".".join(map(str, have)) if have else "không rõ phiên bản"
                pytest.skip(f"{name} {shown} cũ hơn {min_version} cần cho bài này. Xem setup/DEVOPS-TOOLS.md")
        if name == "docker" and not docker_ready():
            pytest.skip("Docker daemon chưa chạy hoặc user chưa có quyền dùng docker")

    @staticmethod
    def require_image(image: str) -> None:
        Exercise.require_tool("docker")
        if _docker("image", "inspect", image).returncode != 0:
            pytest.skip(f"Chưa có image {image}. Tải bằng: docker pull {image}")

    @staticmethod
    def require_cluster(name: str = "devops-lab") -> None:
        Exercise.require_tool("kind")
        result = _run_tool(["kind", "get", "clusters"])
        if result is None or name not in result.stdout.split():
            pytest.skip(f"Chưa có cluster kind {name}. Xem setup/DEVOPS-TOOLS.md")
