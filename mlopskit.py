"""Công cụ dùng chung cho các bài tập của track MLOps: stack `setup/mlops`, MLflow cục bộ, build image và compose tạm."""
from __future__ import annotations

import hashlib
import os
import shutil
import socket
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

import testkit

ROOT = testkit.ROOT
LABEL = "mlops-ex=1"
PREFIX = "mlops-ex-"
BUILD_TIMEOUT_DEFAULT = 1800
STACK_HINT = "docker compose -f setup/mlops/compose.yaml up -d --wait"
FEAST_IMAGE = "mlops-feast:0.67.0"
EVIDENTLY_IMAGE = "mlops-evidently:0.7.23"
ACT_RUNNER = "mlops-act-runner:1"
PROMETHEUS_IMAGE = "prom/prometheus:v3.5.0"
ALERTMANAGER_IMAGE = "prom/alertmanager:v0.34.1"
K6_IMAGE = "grafana/k6:1.8.1"
ACT_INSTALL_HINT = "Chưa cài act. Xem module 08-cicd-for-ml, mục 0"

STACK_SERVICES: dict[str, tuple[str, int]] = {
    "postgres": ("MLOPS_PG_PORT", 25433),
    "minio": ("MLOPS_MINIO_PORT", 29000),
    "mlflow": ("MLOPS_MLFLOW_PORT", 25000),
    "prometheus": ("MLOPS_PROMETHEUS_PORT", 29090),
    "alertmanager": ("MLOPS_ALERTMANAGER_PORT", 29093),
    "grafana": ("MLOPS_GRAFANA_PORT", 23000),
    "redis": ("MLOPS_REDIS_PORT", 26390),
}
STACK_PROFILES: dict[str, str] = {
    "prometheus": "monitoring",
    "alertmanager": "monitoring",
    "grafana": "monitoring",
    "redis": "feast",
}

testkit._load_env_file(ROOT / "setup" / ".env")


def stack_port(service: str) -> int:
    env_name, default = STACK_SERVICES[service]
    return int(os.environ.get(env_name, default))


def _port_open(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def stack_hint(service: str) -> str:
    profile = STACK_PROFILES.get(service)
    if profile is None:
        return STACK_HINT
    return f"docker compose -f setup/mlops/compose.yaml --profile {profile} up -d --wait"


def require_stack(*services: str) -> None:
    for service in services:
        if not _port_open(stack_port(service)):
            pytest.skip(f"Stack MLOps chưa bật ({service}). Chạy: {stack_hint(service)}")


def mlflow_local(tmp_path: Path) -> str:
    import mlflow

    uri = f"sqlite:///{tmp_path}/mlflow.db"
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(uri)
    experiment = f"mlops-ex-{uuid.uuid4().hex[:8]}"
    mlflow.create_experiment(experiment, artifact_location=artifacts.as_uri())
    mlflow.set_experiment(experiment)
    return uri


def build_timeout() -> int:
    """Timeout build (giây) từ env MLOPS_BUILD_TIMEOUT, đọc lúc gọi; mặc định 1800."""
    raw = os.environ.get("MLOPS_BUILD_TIMEOUT", "").strip()
    try:
        value = int(raw)
    except ValueError:
        return BUILD_TIMEOUT_DEFAULT
    return value if value > 0 else BUILD_TIMEOUT_DEFAULT


def _timeout_message(what: str, seconds: int) -> str:
    return (
        f"{what} quá {seconds} giây (build lần đầu trên mạng chậm có thể mất ~20 phút). "
        "Hãy build trước (docker build / docker compose build) rồi chạy lại để dùng cache, "
        "hoặc tăng MLOPS_BUILD_TIMEOUT (giây), ví dụ MLOPS_BUILD_TIMEOUT=3600."
    )


def _docker(*args: str, timeout: float = 60, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout, env=env)


def _tail(result: subprocess.CompletedProcess, lines: int = 40) -> str:
    return "\n".join((result.stdout + result.stderr).splitlines()[-lines:])


@contextmanager
def built_image(context: Path, dockerfile: str = "Dockerfile", build_args: dict[str, str] | None = None) -> Iterator[str]:
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    tag = f"{PREFIX}{uuid.uuid4().hex[:8]}:test"
    command = ["build", "--label", LABEL, "-t", tag, "-f", str(Path(context) / dockerfile)]
    for key, value in (build_args or {}).items():
        command += ["--build-arg", f"{key}={value}"]
    command.append(str(context))
    try:
        seconds = build_timeout()
        try:
            result = _docker(*command, timeout=seconds)
        except subprocess.TimeoutExpired:
            pytest.fail(_timeout_message("docker build", seconds), pytrace=False)
        if result.returncode != 0:
            pytest.fail(f"docker build lỗi ({result.returncode}):\n{_tail(result)}", pytrace=False)
        yield tag
    finally:
        _docker("rmi", "-f", tag)


def image_inspect(tag: str, fmt: str) -> str:
    result = _docker("image", "inspect", "--format", fmt, tag)
    if result.returncode != 0:
        pytest.fail(f"docker image inspect {tag} lỗi:\n{_tail(result)}", pytrace=False)
    return result.stdout.strip()


def image_size_bytes(tag: str) -> int:
    return int(image_inspect(tag, "{{.Size}}"))


def image_has_healthcheck(tag: str) -> bool:
    return image_inspect(tag, "{{json .Config.Healthcheck}}") not in ("", "null")


def _remove_labeled_containers(label: str) -> None:
    ids = _names("ps", "-aq", "--filter", f"label={label}")
    if ids:
        _docker("rm", "-f", *ids, timeout=120)


def _run_container(image: str, args: list[str], *, tag: str, mounts: list[str] = (), env: dict[str, str] | None = None,
                   network: str | None = None, workdir: str | None = None, entrypoint: str | None = None,
                   user: bool = False, timeout: int = 300) -> subprocess.CompletedProcess:
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    name = f"{PREFIX}{uuid.uuid4().hex[:8]}-{tag}"
    command = ["run", "--rm", "--name", name, "--label", LABEL, *testkit.docker_cpu_args()]
    if user:
        command += ["--user", f"{os.getuid()}:{os.getgid()}"]
    if network:
        command += ["--network", network]
    if workdir:
        command += ["-w", workdir]
    if entrypoint:
        command += ["--entrypoint", entrypoint]
    for mount in mounts:
        command += ["-v", mount]
    for key, value in (env or {}).items():
        command += ["-e", f"{key}={value}"]
    command += [image, *args]
    try:
        return _docker(*command, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"{tag} quá {timeout} giây", pytrace=False)
    finally:
        _docker("rm", "-f", name)


DOCKERFILE_SHA_LABEL = "mlops-dockerfile-sha"


def _ensure_image(tag: str, context: Path) -> str:
    """Build `tag` từ `context` khi chưa có, hoặc khi nhãn sha256 của Dockerfile trong image lệch với tệp hiện tại."""
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    sha = hashlib.sha256((Path(context) / "Dockerfile").read_bytes()).hexdigest()
    found = _docker("image", "inspect", "--format", f'{{{{ index .Config.Labels "{DOCKERFILE_SHA_LABEL}" }}}}', tag)
    if found.returncode == 0 and found.stdout.strip() == sha:
        return tag
    seconds = build_timeout()
    try:
        result = _docker("build", "--label", f"{DOCKERFILE_SHA_LABEL}={sha}", "-t", tag, str(context), timeout=seconds)
    except subprocess.TimeoutExpired:
        pytest.fail(_timeout_message(f"docker build {tag}", seconds), pytrace=False)
    if result.returncode != 0:
        pytest.fail(f"docker build {tag} lỗi ({result.returncode}):\n{_tail(result)}", pytrace=False)
    return tag


def feast_image() -> str:
    """Image `mlops-feast:0.67.0`, build một lần; không gắn nhãn `mlops-ex=1` để không bị dọn."""
    return _ensure_image(FEAST_IMAGE, ROOT / "setup" / "mlops" / "feast")


def feast_run(repo: Path, *args: str, network: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    """Chạy `feast <args>` trong container, `repo` mount `/repo` (rw), user không root."""
    return _run_container(feast_image(), ["feast", *args], tag="feast", mounts=[f"{Path(repo).resolve()}:/repo"],
                          network=network, workdir="/repo", user=True, timeout=timeout)


def feast_python(repo: Path, script: str, *, network: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    """Chạy `python -c script` trong image Feast với `repo` mount `/repo`; script in JSON ra stdout."""
    return _run_container(feast_image(), ["python", "-c", script], tag="feast", mounts=[f"{Path(repo).resolve()}:/repo"],
                          network=network, workdir="/repo", user=True, timeout=timeout)


def evidently_image() -> str:
    """Image `mlops-evidently:0.7.23` (pandas 2.x), build một lần; không gắn nhãn `mlops-ex=1` để không bị dọn."""
    return _ensure_image(EVIDENTLY_IMAGE, ROOT / "setup" / "mlops" / "evidently")


def evidently_python(workdir: Path, script: str, *, timeout: int = 300) -> subprocess.CompletedProcess:
    """Chạy `python -c script` trong image Evidently với `workdir` mount `/work` (rw); script in JSON ra stdout."""
    return _run_container(evidently_image(), ["python", "-c", script], tag="evidently",
                          mounts=[f"{Path(workdir).resolve()}:/work"], workdir="/work", user=True, timeout=timeout)


def promtool(*args: str, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    """Chạy `promtool <args>` trong image Prometheus ghim; `cwd` mount chỉ đọc tại `/work`."""
    return _run_container(PROMETHEUS_IMAGE, list(args), tag="promtool", mounts=[f"{Path(cwd).resolve()}:/work:ro"],
                          workdir="/work", entrypoint="promtool", user=True, timeout=timeout)


def amtool(*args: str, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    """Chạy `amtool <args>` trong image Alertmanager ghim; `cwd` mount chỉ đọc tại `/work`."""
    return _run_container(ALERTMANAGER_IMAGE, list(args), tag="amtool", mounts=[f"{Path(cwd).resolve()}:/work:ro"],
                          workdir="/work", entrypoint="amtool", user=True, timeout=timeout)


def k6_run(script: Path, env: dict[str, str], network: str = "host", timeout: int = 300) -> subprocess.CompletedProcess:
    """Chạy một script k6; `.stdout` là JSON của `--summary-export`, `.stderr` gộp log và bảng tóm tắt của k6."""
    script = Path(script).resolve()
    out = Path(tempfile.mkdtemp(prefix="mlops-ex-k6-"))
    out.chmod(0o777)
    try:
        result = _run_container(
            K6_IMAGE, ["run", "--quiet", "--summary-export=/out/summary.json", f"/scripts/{script.name}"], tag="k6",
            mounts=[f"{script.parent}:/scripts:ro", f"{out}:/out"], env=env, network=network, user=True, timeout=timeout,
        )
        summary = out / "summary.json"
        stdout = summary.read_text(encoding="utf-8") if summary.is_file() else ""
        return subprocess.CompletedProcess(result.args, result.returncode, stdout, result.stdout + result.stderr)
    finally:
        shutil.rmtree(out, ignore_errors=True)


def act_run(workdir: Path, *args: str, event: str = "push", timeout: int = 600,
            container_options: str = "") -> subprocess.CompletedProcess:
    """Chạy workflow bằng `act` (runner image tự build, `--pull=false`, `--bind` thư mục làm việc).

    Chỉ đảm bảo không kéo image. Workflow không được dùng `uses:` action từ xa (act sẽ cần mạng và GitHub).
    Dọn đúng các container của lần chạy này (nhãn `mlops-ex-run=<uuid8>`), không đụng container khác.
    Tuỳ chọn container thêm (vd. `--user uid:gid`) truyền qua `container_options`, không truyền `--container-options`
    trong `args` vì act chỉ giữ giá trị cuối.
    """
    if "--container-options" in args:
        raise ValueError("Dùng tham số container_options thay cho --container-options trong args")
    binary = shutil.which("act")
    if binary is None:
        pytest.skip(ACT_INSTALL_HINT)
    runner = _ensure_image(ACT_RUNNER, ROOT / "setup" / "mlops" / "act-runner")
    run_label = f"mlops-ex-run={uuid.uuid4().hex[:8]}"
    command = [binary, event, "-P", f"ubuntu-latest={runner}", "--pull=false", "--bind",
               "--container-options", f"--label {LABEL} --label {run_label} {container_options}".strip(), *args]
    try:
        return subprocess.run(command, cwd=workdir, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"act quá {timeout} giây", pytrace=False)
    finally:
        _remove_labeled_containers(run_label)


def dvc_sh(repo: Path, cmd: str, args: tuple[str, ...] = (), *, ok: bool = True, env: dict[str, str] | None = None,
           timeout: int = 120) -> subprocess.CompletedProcess:
    """Chạy `bash -c cmd` trong sandbox với `repo` ghi được, DVC và git đã cấu hình riêng cho test (`args` thành `$1...`)."""
    repo = Path(repo)
    base = {
        "DVC_NO_ANALYTICS": "1",
        "DVC_SITE_CACHE_DIR": str(repo / ".site"),
        "DVC_GLOBAL_CONFIG_DIR": str(repo / ".gc"),
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    result = testkit.run_sandboxed(["bash", "-c", cmd, "bash", *args], writable=[repo], cwd=repo, env={**base, **(env or {})},
                                   timeout=timeout)
    if ok:
        assert result.returncode == 0, f"{cmd}\n{result.stdout}\n{result.stderr}"
    return result


REAL_SHA256: dict[str, str] = {
    "nyc-tlc/yellow_tripdata_2019-01.parquet": "3ad95f39714bfc9864219e69e577f119925c6ba32d384ac68d40bdad1dc7726d",
    "nyc-tlc/yellow_tripdata_2019-02.parquet": "d20a9e3edf838017ae641e664da085564341c729aed2ee05c7631c74dccf761a",
    "nyc-tlc/yellow_tripdata_2019-03.parquet": "6883b45b3c1a8908346334b6143804f9dab4a223a72b3b9e3140ef0239920978",
    "nyc-tlc/yellow_tripdata_2019-04.parquet": "0903fb6c20ef49f1bc1238ac5e7ea00d963477b14cf62f2440c090ac920d8013",
    "nyc-tlc/yellow_tripdata_2019-05.parquet": "6001f518a5871ec7e85b856075cab5b41a76791b2e6adced7e299cf26d125daa",
    "nyc-tlc/yellow_tripdata_2019-06.parquet": "acc434ffb54b70cbba1319f31f1a38584d9d4e8863fbbeaa4944bb577dfdf5cc",
    "nyc-tlc/yellow_tripdata_2019-07.parquet": "f4136f0df68a90415ca42c48956db12d82b957f0a941145c2bf7346053a564e4",
    "nyc-tlc/yellow_tripdata_2019-08.parquet": "2f7cae03501aedc96b8534034509f40b61d1ce93a0957f2ab4e2f32295665a67",
    "nyc-tlc/yellow_tripdata_2019-09.parquet": "61fec423071ca0b3cf6b97cd2a51d3b8cca897acfdc4bc9b4518320bcf847861",
    "nyc-tlc/yellow_tripdata_2019-10.parquet": "7a29ec212d73381398ef94d1ad3ba3963d157e57d2373dad0345981223c248fd",
    "nyc-tlc/yellow_tripdata_2019-11.parquet": "2187309e5b5f73aad224facf1e1f97b3120039a3cffceaf569b49b81ae30b004",
    "nyc-tlc/yellow_tripdata_2019-12.parquet": "fbf893219b1ddefd5113609c63600cff1f48fc4c5ded05113eb19a435cc16c48",
    "nyc-tlc-2020/yellow_tripdata_2020-01.parquet": "0c32c1d5ef0d37ac3ff1a3f1880f247cc40165edf18626e5a86866296a4a5b93",
    "nyc-tlc-2020/yellow_tripdata_2020-02.parquet": "e57df0e7c410c02d78cd59a31394a118f3d92c50560a2d8fa3a2bf5e17dcffaa",
    "nyc-tlc-2020/yellow_tripdata_2020-03.parquet": "6fa1343946bc1e3702fc351ff9818787cc40e4cf2b095d947ff5e452b5b42f84",
    "nyc-tlc-2020/yellow_tripdata_2020-04.parquet": "3104e1e5548ade630988a4a8b9ec76c51a057b88159f78676c7d344f48491450",
    "nyc-tlc-2020/yellow_tripdata_2020-05.parquet": "f6167e3c8f1039ec4015cb121e73f8e08710ad1681da747f2b5aa504008cf289",
    "nyc-tlc-2020/yellow_tripdata_2020-06.parquet": "1ad5d65c3951d9082ab5e24acca2235cc34f014a34b4225556cb9a885cb1101d",
    "nyc-tlc-2020/yellow_tripdata_2020-07.parquet": "14a450d61c1828a3e9f3f29e3e2594b4c0eb687cd2fb0e9eeb2e10dbed9e4eb2",
    "nyc-tlc-2020/yellow_tripdata_2020-08.parquet": "e1242bad250d52371f59dbe35e1925897dd6699a68130d69e49126b3e4ec8e86",
    "nyc-tlc-2020/yellow_tripdata_2020-09.parquet": "353574457176ea1528ba1c07128fa90cf6594920b26bc79721dc844077696606",
    "nyc-tlc-2020/yellow_tripdata_2020-10.parquet": "4e447b9c7cc6c48f6c0bf62ca93ef0051ff89b06d3d039a3c3489cf64a9c7e41",
    "nyc-tlc-2020/yellow_tripdata_2020-11.parquet": "478716ac6420213ab45d9a1107fe5a1ba8c59de0e4bc27588b6f3b2079ad7210",
    "nyc-tlc-2020/yellow_tripdata_2020-12.parquet": "b3e029240c4af3b8bc373169a7412150d5eb1721e2b8498975c13226dfd2bb55",
}
_SHA_CACHE: dict[tuple[str, int, int], str] = {}


def _sha256(path: Path) -> str:
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    if key not in _SHA_CACHE:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        _SHA_CACHE[key] = digest.hexdigest()
    return _SHA_CACHE[key]


def real_month(dataset: str, month: str) -> Path:
    """Đường dẫn tệp Parquet một tháng của `nyc-tlc` (2019) hay `nyc-tlc-2020`, đã kiểm sha256; skip khi chưa tải."""
    name = f"yellow_tripdata_{month}.parquet"
    expected = REAL_SHA256.get(f"{dataset}/{name}")
    if expected is None:
        pytest.fail(f"Không có tệp {dataset}/{name} trong bảng sha256 (tháng dạng YYYY-MM, 12 tháng của năm bộ dữ liệu).", pytrace=False)
    path = testkit.Exercise.dataset(dataset) / name
    if not path.is_file():
        pytest.skip(f"Chưa có {name}. Chạy: uv run python data/download_dataset.py {dataset}")
    if _sha256(path) != expected:
        pytest.fail(
            f"sha256 của {path.name} không khớp: tệp nguồn đã bị TLC sửa hoặc tải hỏng. "
            f"Xoá {path} và tải lại: uv run python data/download_dataset.py {dataset}",
            pytrace=False,
        )
    return path


class ComposeProject:
    def __init__(self, name: str, file: Path, env: dict[str, str]) -> None:
        self.name = name
        self.file = Path(file)
        self.env = env

    def _compose(self, *args: str, timeout: float = 60) -> subprocess.CompletedProcess:
        return _docker("compose", "-p", self.name, "-f", str(self.file), *args, timeout=timeout, env=self.env)

    def port(self, service: str, container_port: int) -> int:
        result = self._compose("port", service, str(container_port))
        if result.returncode != 0 or ":" not in result.stdout:
            pytest.fail(f"Không lấy được cổng {service}:{container_port}: {_tail(result)}", pytrace=False)
        return int(result.stdout.strip().splitlines()[0].rsplit(":", 1)[1])

    def logs(self, service: str) -> str:
        result = self._compose("logs", "--no-color", service)
        return result.stdout + result.stderr

    def exec(self, service: str, *cmd: str) -> subprocess.CompletedProcess:
        return self._compose("exec", "-T", service, *cmd, timeout=120)


@contextmanager
def compose_project(file: Path, env: dict[str, str] | None = None, services: tuple[str, ...] = ()) -> Iterator[ComposeProject]:
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    project = ComposeProject(f"{PREFIX}{uuid.uuid4().hex[:8]}", file, {**os.environ, **(env or {})})
    try:
        seconds = build_timeout()
        try:
            result = project._compose("up", "-d", "--build", "--wait", *services, timeout=seconds)
        except subprocess.TimeoutExpired:
            pytest.fail(_timeout_message("docker compose up", seconds), pytrace=False)
        if result.returncode != 0:
            pytest.fail(f"docker compose up lỗi ({result.returncode}):\n{_tail(result)}", pytrace=False)
        yield project
    finally:
        project._compose("down", "-v", "--remove-orphans", "--rmi", "local", timeout=180)


def _names(*args: str) -> list[str]:
    return _docker(*args).stdout.split()


def leftovers(needle: str | None = None) -> list[str]:
    if not testkit.docker_ready():
        return []
    found = set()
    for flag in (f"label={LABEL}", f"name={PREFIX}"):
        found.update(_names("ps", "-a", "--filter", flag, "--format", "{{.Names}}"))
        found.update(_names("network", "ls", "--filter", flag, "--format", "{{.Name}}"))
    found.update(_names("image", "ls", "--filter", f"label={LABEL}", "--format", "{{.Repository}}:{{.Tag}}"))
    found.update(_names("image", "ls", "--filter", f"reference={PREFIX}*", "--format", "{{.Repository}}:{{.Tag}}"))
    for line in _docker("ps", "-a", "--filter", "label=com.docker.compose.project", "--format",
                        '{{.Names}} {{.Label "com.docker.compose.project"}}').stdout.splitlines():
        name, _, project = line.partition(" ")
        if project.startswith(PREFIX):
            found.add(name)
    return sorted(n for n in found if needle is None or needle in n)
