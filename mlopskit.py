"""Công cụ dùng chung cho các bài tập của track MLOps: stack `setup/mlops`, MLflow cục bộ, build image và compose tạm."""
from __future__ import annotations

import hashlib
import os
import re
import signal
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pytest
import yaml

import testkit

ROOT = testkit.ROOT
LABEL = "mlops-ex=1"
PREFIX = "mlops-ex-"
BUILD_TIMEOUT_DEFAULT = 1800
STACK_HINT = "docker compose -f setup/mlops/compose.yaml up -d --wait"
FEAST_IMAGE = "mlops-feast:0.67.0"
EVIDENTLY_IMAGE = "mlops-evidently:0.7.23"
MODELSCAN_IMAGE = "mlops-modelscan:0.8.8"
ACT_RUNNER = "mlops-act-runner:1"
PROMETHEUS_IMAGE = "prom/prometheus:v3.5.0"
ALERTMANAGER_IMAGE = "prom/alertmanager:v0.34.1"
K6_IMAGE = "grafana/k6:1.8.1"
ACT_INSTALL_HINT = "Chưa cài act. Xem module 08-cicd-for-ml, mục 0"
KIND_CLUSTER = "mlops"
KUBE_CONTEXT = "kind-mlops"
KIND_HINT = "Chạy: bash setup/mlops/kind/up.sh (xem module 13-kubernetes-for-ml, mục 0)"
LOCAL_BIN = Path.home() / ".local" / "bin"
GPU_PROJECT = ROOT / "setup" / "gpu"
TERMINATING_GRACE_S = 120

STACK_SERVICES: dict[str, tuple[str, int]] = {
    "postgres": ("MLOPS_PG_PORT", 25433),
    "minio": ("MLOPS_MINIO_PORT", 29000),
    "mlflow": ("MLOPS_MLFLOW_PORT", 25000),
    "prometheus": ("MLOPS_PROMETHEUS_PORT", 29090),
    "alertmanager": ("MLOPS_ALERTMANAGER_PORT", 29093),
    "grafana": ("MLOPS_GRAFANA_PORT", 23000),
    "redis": ("MLOPS_REDIS_PORT", 26390),
    "kafka": ("MLOPS_KAFKA_PORT", 29092),
}
STACK_PROFILES: dict[str, str] = {
    "prometheus": "monitoring",
    "alertmanager": "monitoring",
    "grafana": "monitoring",
    "redis": "feast",
    "kafka": "streaming",
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


def modelscan_run(target: Path, *, timeout: int = 300) -> subprocess.CompletedProcess:
    """Quét `target` (tệp hoặc thư mục) bằng `modelscan` trong image `mlops-modelscan:0.8.8`, không mạng, chỉ đọc.

    `.returncode` là mã thoát của modelscan (0 sạch, 1 có vấn đề, 2 lỗi, 3 không có gì để quét, 4 định dạng không hỗ
    trợ); `.stdout` là báo cáo JSON (rỗng khi modelscan không ghi báo cáo), `.stderr` gộp log của modelscan.
    modelscan chỉ đọc byte, không bao giờ nạp model; container vẫn chạy `--network none`, user không root.
    """
    target = Path(target).resolve()
    if not target.exists():
        pytest.fail(f"modelscan_run: không có {target}", pytrace=False)
    image = _ensure_image(MODELSCAN_IMAGE, ROOT / "setup" / "mlops" / "modelscan")
    out = Path(tempfile.mkdtemp(prefix=f"{PREFIX}modelscan-"))
    out.chmod(0o777)
    try:
        result = _run_container(
            image, ["modelscan", "-p", f"/scan/{target.name}", "-r", "json", "-o", "/out/report.json"], tag="modelscan",
            mounts=[f"{target.parent}:/scan:ro", f"{out}:/out"], network="none", user=True, timeout=timeout,
        )
        report = out / "report.json"
        stdout = report.read_text(encoding="utf-8") if report.is_file() else ""
        return subprocess.CompletedProcess(result.args, result.returncode, stdout, result.stdout + result.stderr)
    finally:
        shutil.rmtree(out, ignore_errors=True)


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
    """Rác còn lại: container, network, image Docker có nhãn/tiền tố `mlops-ex`; trong cluster kind `mlops`: namespace
    `mlops-ex-*` (Active, hoặc kẹt Terminating quá 2 phút), tài nguyên cluster-scoped có nhãn `mlops-ex-run`, extended
    resource `mlops.example/*` trên node; topic Kafka `mlops-ex-*`; thư mục tạm Ray `mlops-ex-ray-*`.
    """
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
    found.update(_leftover_namespaces())
    found.update(_leftover_cluster_scoped())
    found.update(_leftover_extended_resources())
    found.update(_leftover_kafka_topics())
    found.update(_leftover_ray_dirs())
    return sorted(n for n in found if needle is None or needle in n)


def _bin(name: str) -> str | None:
    """Ưu tiên bản ghim, đã kiểm checksum trong `~/.local/bin` (do `setup/mlops/kind/up.sh` cài), rồi mới tới PATH."""
    local = LOCAL_BIN / name
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    return shutil.which(name)


def _kind_clusters(timeout: float = 30) -> list[str]:
    binary = _bin("kind")
    if binary is None:
        return []
    try:
        result = subprocess.run([binary, "get", "clusters"], capture_output=True, text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError):
        return []
    return result.stdout.split() if result.returncode == 0 else []


def _kube_ready() -> bool:
    try:
        result = kubectl("get", "--raw", "/readyz", timeout=15)
    except pytest.fail.Exception:
        return False
    return result.returncode == 0 and result.stdout.strip() == "ok"


def require_kind() -> None:
    """Skip khi thiếu `kind`/`kubectl`, khi chưa có cluster `mlops` hoặc API server không phản hồi."""
    missing = [name for name in ("kind", "kubectl") if _bin(name) is None]
    if missing:
        pytest.skip(f"Chưa cài {', '.join(missing)}. {KIND_HINT}")
    if KIND_CLUSTER not in _kind_clusters():
        pytest.skip(f"Chưa có cluster kind `{KIND_CLUSTER}`. {KIND_HINT}")
    if not _kube_ready():
        pytest.skip(f"Cluster kind `{KIND_CLUSTER}` không phản hồi (node bị dừng?). {KIND_HINT}")


def kubectl(*args: str, namespace: str | None = None, input: str | None = None,
            timeout: int = 120) -> subprocess.CompletedProcess:
    """Chạy `kubectl --context kind-mlops [-n namespace] <args>`; không bao giờ dùng context hiện hành của máy."""
    binary = _bin("kubectl")
    if binary is None:
        pytest.skip(f"Chưa cài kubectl. {KIND_HINT}")
    command = [binary, "--context", KUBE_CONTEXT]
    if namespace:
        command += ["-n", namespace]
    command += list(args)
    try:
        return subprocess.run(command, input=input, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"kubectl {' '.join(args)} quá {timeout} giây", pytrace=False)


def _kubectl_quiet(*args: str, namespace: str | None = None, timeout: int = 15) -> subprocess.CompletedProcess:
    """`kubectl` best-effort: không bao giờ raise; lỗi/quá hạn trả `CompletedProcess` mã 1 kèm lý do trong stderr."""
    try:
        return kubectl(*args, namespace=namespace, timeout=timeout)
    except (pytest.fail.Exception, pytest.skip.Exception, subprocess.SubprocessError, OSError) as error:
        return subprocess.CompletedProcess(list(args), 1, "", f"kubectl {' '.join(args)}: {error}")


def _namespace_manifest(name: str, run: str) -> str:
    return (
        "apiVersion: v1\nkind: Namespace\nmetadata:\n"
        f"  name: {name}\n  labels:\n    \"mlops-ex\": \"1\"\n    \"mlops-ex-run\": \"{run}\"\n"
        "---\napiVersion: rbac.authorization.k8s.io/v1\nkind: RoleBinding\nmetadata:\n"
        f"  name: mlops-argo-executor\n  namespace: {name}\n"
        "roleRef:\n  apiGroup: rbac.authorization.k8s.io\n  kind: ClusterRole\n  name: mlops-argo-executor\n"
        f"subjects:\n  - kind: ServiceAccount\n    name: default\n    namespace: {name}\n"
    )


@contextmanager
def k8s_namespace() -> Iterator[str]:
    """Namespace tạm `mlops-ex-<uuid8>` (nhãn `mlops-ex=1`, `mlops-ex-run=<uuid8>`), xoá đúng namespace này trong `finally`.

    ServiceAccount `default` của namespace được gắn ClusterRole `mlops-argo-executor` để chạy được Workflow Argo.
    """
    require_kind()
    run = uuid.uuid4().hex[:8]
    name = f"{PREFIX}{run}"
    try:
        result = kubectl("apply", "-f", "-", input=_namespace_manifest(name, run))
        if result.returncode != 0:
            pytest.fail(f"Không tạo được namespace {name}:\n{_tail(result)}", pytrace=False)
        yield name
    finally:
        _delete_namespace(name)


def _delete_namespace(name: str) -> None:
    """Xoá namespace `name` (`--wait=false`); lỗi khi xoá chỉ ghi ra stderr, không che lỗi của chính test."""
    result = _kubectl_quiet("delete", "namespace", name, "--wait=false", "--ignore-not-found", timeout=30)
    if result.returncode != 0:
        sys.stderr.write(f"mlopskit: không xoá được namespace {name}:\n{_tail(result)}\n")


_XDG_CACHE = os.environ.get("XDG_CACHE_HOME") or ""
CACHE_ROOT = Path(_XDG_CACHE) if os.path.isabs(_XDG_CACHE) else Path.home() / ".cache"
KIND_LOAD_DIR = CACHE_ROOT / "mlops-kind" / "load"


def kind_load(tag: str, timeout: int = 600) -> None:
    """Nạp image `tag` từ Docker trên máy vào node của cluster `mlops`.

    Dùng `docker save --platform` rồi `kind load image-archive`: Docker dùng containerd image store chỉ giữ blob của
    nền tảng máy, nên `kind load docker-image` với image đa nền tảng kéo từ registry sẽ lỗi `content digest ... not found`.
    Tệp tar tạm nằm trên đĩa (`~/.cache/mlops-kind/load`, quyền 0700), không ở `/tmp` (tmpfs, tốn RAM), xoá ngay sau khi nạp.
    """
    require_kind()
    platform = f"linux/{_docker('version', '--format', '{{.Server.Arch}}').stdout.strip() or 'amd64'}"
    KIND_LOAD_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    KIND_LOAD_DIR.chmod(0o700)
    workdir = Path(tempfile.mkdtemp(prefix=PREFIX, dir=KIND_LOAD_DIR))
    archive = workdir / "image.tar"
    try:
        try:
            saved = _docker("save", "--platform", platform, "-o", str(archive), tag, timeout=timeout)
            if saved.returncode != 0:
                pytest.fail(f"docker save {tag} lỗi:\n{_tail(saved)}", pytrace=False)
            result = subprocess.run([_bin("kind"), "load", "image-archive", str(archive), "--name", KIND_CLUSTER],
                                    capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"kind load {tag} quá {timeout} giây", pytrace=False)
        if result.returncode != 0:
            pytest.fail(f"kind load {tag} lỗi:\n{_tail(result)}", pytrace=False)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def apply_manifest(path_or_text: Path | str, namespace: str, *, check: bool = True,
                   timeout: int = 120) -> subprocess.CompletedProcess:
    """`kubectl apply` một tệp/thư mục (`Path`) hoặc nội dung YAML (`str`) vào `namespace`; `check` fail khi lỗi."""
    if isinstance(path_or_text, Path):
        result = kubectl("apply", "-f", str(path_or_text), namespace=namespace, timeout=timeout)
    else:
        result = kubectl("apply", "-f", "-", namespace=namespace, input=path_or_text, timeout=timeout)
    if check and result.returncode != 0:
        pytest.fail(f"kubectl apply lỗi ({result.returncode}):\n{_tail(result)}", pytrace=False)
    return result


def _diagnose(kind: str, name: str, namespace: str) -> str:
    """Thông tin chẩn đoán best-effort (timeout ngắn, không bao giờ raise)."""
    parts = [f"--- kubectl describe {kind}/{name}", _tail(_kubectl_quiet("describe", kind, name, namespace=namespace), 60)]
    pods = _kubectl_quiet("get", "pods", "-o", "name", namespace=namespace).stdout.split()
    parts += ["--- pods", _tail(_kubectl_quiet("get", "pods", "-o", "wide", namespace=namespace), 20)]
    for pod in pods[:6]:
        logs = _kubectl_quiet("logs", pod, "--all-containers", "--prefix", "--tail=30", namespace=namespace)
        parts += [f"--- logs {pod}", _tail(logs, 30)]
    events = _kubectl_quiet("get", "events", "--sort-by=.lastTimestamp", namespace=namespace)
    parts += ["--- events", _tail(events, 20)]
    return "\n".join(parts)


def _wait_fail(kind: str, name: str, namespace: str, reason: str) -> None:
    pytest.fail(f"{kind}/{name}: {reason}\n{_diagnose(kind, name, namespace)}", pytrace=False)


def _wait_timed_out(result: subprocess.CompletedProcess) -> bool:
    return "timed out waiting" in result.stderr


def wait_for(kind: str, name: str, condition: str, namespace: str, timeout: int,
             fail_on: tuple[str, ...] = ()) -> None:
    """Chờ tài nguyên xuất hiện (`--for=create`) rồi đạt `condition`, cả hai trong cùng `timeout` giây.

    `condition` là tên condition (`Ready`) hoặc biểu thức đủ (`jsonpath={.status.phase}=Succeeded`, `delete`).
    Với `delete` thì không chờ tạo; tài nguyên đã không còn là đạt. `fail_on` (vd. `("Failed", "Error")`) fail ngay khi
    `.status.phase` rơi vào một trong các giá trị đó (Workflow Argo, Pod), thay vì chờ hết hạn. Lỗi không phải hết hạn
    (condition sai cú pháp, thiếu quyền...) fail ngay kèm stderr của kubectl. Fail kèm `describe`, pod, log và events.
    """
    expr = condition if condition.startswith(("condition=", "jsonpath=", "delete", "create")) else f"condition={condition}"
    deadline = time.monotonic() + timeout
    target = f"{kind}/{name}"
    if not expr.startswith(("delete", "create")):
        created = kubectl("wait", "--for=create", target, f"--timeout={timeout}s", namespace=namespace,
                          timeout=timeout + 30)
        if created.returncode != 0:
            reason = "không xuất hiện" if _wait_timed_out(created) else "kubectl wait --for=create lỗi"
            _wait_fail(kind, name, namespace, f"{reason} (timeout {timeout} giây): {_tail(created, 5)}")
    step = 5 if fail_on else None
    while True:
        remaining = max(1, int(deadline - time.monotonic()))
        chunk = min(step, remaining) if step else remaining
        result = kubectl("wait", f"--for={expr}", target, f"--timeout={chunk}s", namespace=namespace, timeout=chunk + 30)
        if result.returncode == 0:
            return
        if not _wait_timed_out(result):
            _wait_fail(kind, name, namespace, f"kubectl wait --for={expr} lỗi: {_tail(result, 5)}")
        if fail_on:
            phase = _kubectl_quiet("get", target, "-o", "jsonpath={.status.phase}", namespace=namespace).stdout.strip()
            if phase in fail_on:
                _wait_fail(kind, name, namespace, f"vào phase {phase} (chờ {expr})")
        if time.monotonic() >= deadline:
            _wait_fail(kind, name, namespace, f"không đạt {expr} sau {timeout} giây: {_tail(result, 5)}")
        time.sleep(1)


@contextmanager
def port_forward(namespace: str, target: str, port: int, timeout: float = 30) -> Iterator[int]:
    """`kubectl port-forward target <cổng tự do>:port` trên 127.0.0.1; trả cổng local, dừng tiến trình khi ra.

    Sẵn sàng khi kubectl in `Forwarding from 127.0.0.1:<cổng>` (không thử kết nối vào cổng, để không gửi request thừa
    tới service). Output của kubectl ghi (append) vào tệp tạm, không dùng PIPE (PIPE không đọc sẽ đầy và làm kubectl
    treo); test đọc bằng một lần mở riêng, không đụng offset ghi của kubectl.
    """
    binary = _bin("kubectl")
    if binary is None:
        pytest.skip(f"Chưa cài kubectl. {KIND_HINT}")
    local = testkit.free_port()
    command = [binary, "--context", KUBE_CONTEXT, "-n", namespace, "port-forward", "--address", "127.0.0.1",
               target, f"{local}:{port}"]
    logdir = Path(tempfile.mkdtemp(prefix=PREFIX))
    out_path, err_path = logdir / "stdout.log", logdir / "stderr.log"
    ready = f"Forwarding from 127.0.0.1:{local}"
    with open(out_path, "a", encoding="utf-8") as out, open(err_path, "a", encoding="utf-8") as err:
        process = subprocess.Popen(command, stdout=out, stderr=err, text=True)
    try:
        deadline = time.monotonic() + timeout
        while ready not in out_path.read_text(encoding="utf-8", errors="replace"):
            if process.poll() is not None:
                stderr = err_path.read_text(encoding="utf-8", errors="replace")
                pytest.fail(f"kubectl port-forward {target} thoát sớm:\n{stderr[-4000:]}", pytrace=False)
            if time.monotonic() > deadline:
                stderr = err_path.read_text(encoding="utf-8", errors="replace")
                pytest.fail(f"kubectl port-forward {target} chưa sẵn sàng sau {timeout} giây:\n{stderr[-2000:]}",
                            pytrace=False)
            time.sleep(0.1)
        yield local
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        shutil.rmtree(logdir, ignore_errors=True)


def _leftover_namespaces() -> list[str]:
    """Best-effort: không có cluster hay cluster không phản hồi thì trả `[]` nhanh, không bao giờ fail."""
    if _bin("kubectl") is None or KIND_CLUSTER not in _kind_clusters(timeout=10):
        return []
    result = _kubectl_quiet(
        "get", "namespaces", "-o",
        'jsonpath={range .items[*]}{.metadata.name} {.status.phase} {.metadata.deletionTimestamp}{"\\n"}{end}',
        timeout=10,
    )
    if result.returncode != 0:
        return []
    now = datetime.now(timezone.utc)
    names = []
    for line in result.stdout.splitlines():
        name, phase, deleted = (line.split(" ") + ["", ""])[:3]
        if not name.startswith(PREFIX):
            continue
        if phase == "Active":
            names.append(name)
        elif phase == "Terminating" and deleted:
            since = datetime.fromisoformat(deleted.replace("Z", "+00:00"))
            if (now - since).total_seconds() > TERMINATING_GRACE_S:
                names.append(name)
    return names


def require_cuda() -> None:
    """Skip `"Không có CUDA"` khi máy không có GPU NVIDIA dùng được (`nvidia-smi -L` lỗi hoặc không thấy GPU)."""
    binary = shutil.which("nvidia-smi")
    if binary is None:
        pytest.skip("Không có CUDA (không thấy nvidia-smi); bài này có đường CPU")
    try:
        result = subprocess.run([binary, "-L"], capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        pytest.skip("Không có CUDA (nvidia-smi không phản hồi); bài này có đường CPU")
    if result.returncode != 0 or "GPU" not in result.stdout:
        pytest.skip("Không có CUDA (nvidia-smi không thấy GPU); bài này có đường CPU")


GPU_SYNC_HINT = "Chạy: uv sync --project setup/gpu"
_GPU_ENV_STATE: dict[str, str] = {}


def _gpu_env_problem() -> str:
    """Rỗng khi env `setup/gpu` dùng được (có onnxruntime-gpu, không có onnxruntime CPU đè lên); ngược lại là lý do."""
    if "problem" in _GPU_ENV_STATE:
        return _GPU_ENV_STATE["problem"]
    python = GPU_PROJECT / ".venv" / "bin" / "python"
    if not python.is_file():
        problem = "Chưa có môi trường setup/gpu"
    else:
        probe = (
            "import importlib.metadata as m\n"
            "import re\n"
            "names = {re.sub(r'[-_.]+', '-', d.metadata['Name']).lower() for d in m.distributions() if d.metadata['Name']}\n"
            "print('gpu' if 'onnxruntime-gpu' in names else 'nogpu', 'cpu' if 'onnxruntime' in names else 'nocpu')\n"
        )
        try:
            result = subprocess.run([str(python), "-I", "-c", probe], capture_output=True, text=True, timeout=60)
            state = result.stdout.split()
        except (subprocess.SubprocessError, OSError) as error:
            state = [f"lỗi {error}"]
        if state == ["gpu", "nocpu"]:
            problem = ""
        elif "cpu" in state:
            problem = "Môi trường setup/gpu còn gói onnxruntime (CPU) đè lên onnxruntime-gpu"
        else:
            problem = f"Môi trường setup/gpu chưa có onnxruntime-gpu ({' '.join(state)})"
    _GPU_ENV_STATE["problem"] = problem
    return problem


def _gpu_env_ready() -> bool:
    return _gpu_env_problem() == ""


def gpu_python(script: str, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    """Chạy `python -I -c script` bằng môi trường `setup/gpu` (torch CUDA, onnxruntime-gpu) trong `cwd`; script in JSON ra stdout.

    Dùng `uv run --no-sync` (test không bao giờ tự sync/tải gói) và `python -I` (không import module nằm trong `cwd`).
    Skip kèm lệnh `uv sync --project setup/gpu` khi env chưa có hoặc chưa đúng.
    """
    if not _gpu_env_ready():
        pytest.skip(f"{_gpu_env_problem()}. {GPU_SYNC_HINT}")
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    command = ["uv", "run", "--no-sync", "--project", str(GPU_PROJECT), "python", "-I", "-c", script]
    try:
        return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"gpu_python quá {timeout} giây", pytrace=False)


SENIOR_HINT = "Chạy: bash setup/mlops/kind/up.sh --senior (xem module 14-kubernetes-ml-production, mục 0)"
SENIOR_CRDS = ("scaledobjects.keda.sh", "clusterqueues.kueue.x-k8s.io")
RUN_TOKEN = "__RUN__"
RUN_LABEL = "mlops-ex-run"
EXTENDED_DOMAIN = "mlops.example"
CLUSTER_KINDS_CORE = "priorityclasses.scheduling.k8s.io,clusterroles.rbac.authorization.k8s.io,clusterrolebindings.rbac.authorization.k8s.io"
CLUSTER_KINDS_SENIOR = ("resourceflavors.kueue.x-k8s.io,clusterqueues.kueue.x-k8s.io,cohorts.kueue.x-k8s.io,"
                        "workloadpriorityclasses.kueue.x-k8s.io,clustertriggerauthentications.keda.sh")


def require_senior_addons() -> None:
    """Như `require_kind`, thêm skip khi cluster chưa có add-on senior (CRD của KEDA hoặc Kueue)."""
    require_kind()
    missing = [crd for crd in SENIOR_CRDS if _kubectl_quiet("get", "crd", crd, timeout=15).returncode != 0]
    if missing:
        pytest.skip(f"Cluster kind `{KIND_CLUSTER}` chưa có add-on senior (thiếu CRD {', '.join(missing)}). {SENIOR_HINT}")


def _cluster_scoped_kinds() -> set[str]:
    result = kubectl("api-resources", "--namespaced=false", "--no-headers", "-o", "wide", timeout=30)
    if result.returncode != 0:
        pytest.fail(f"kubectl api-resources lỗi:\n{_tail(result)}", pytrace=False)
    kinds = set()
    for line in result.stdout.splitlines():
        columns = line.split()
        kinds.update(c for c in columns if c[:1].isupper())
    return kinds


def _render_cluster_scoped(manifest: str, run: str, allowed: set[str]) -> tuple[str, list[str]]:
    docs = [d for d in yaml.safe_load_all(manifest.replace(RUN_TOKEN, run)) if d]
    if not docs:
        pytest.fail("cluster_scoped: manifest rỗng", pytrace=False)
    names = []
    for doc in docs:
        kind = doc.get("kind", "")
        meta = doc.setdefault("metadata", {}) or {}
        doc["metadata"] = meta
        name = str(meta.get("name", ""))
        if kind not in allowed or "namespace" in meta:
            pytest.fail(f"cluster_scoped chỉ nhận tài nguyên cluster-scoped; {kind}/{name} là namespaced "
                        "(dùng apply_manifest trong k8s_namespace)", pytrace=False)
        if run not in name:
            pytest.fail(f"cluster_scoped: tên {kind}/{name or '<trống>'} phải chứa {RUN_TOKEN} (thay bằng run id) "
                        "để không đụng tài nguyên của lần chạy khác", pytrace=False)
        labels = meta.get("labels") or {}
        labels.update({"mlops-ex": "1", RUN_LABEL: run})
        meta["labels"] = labels
        names.append(f"{kind.lower()}/{name}")
    return yaml.safe_dump_all(docs, sort_keys=False), names


@contextmanager
def cluster_scoped(manifest: str) -> Iterator[list[str]]:
    """Apply tài nguyên cluster-scoped (ClusterQueue, ResourceFlavor, PriorityClass...) cho riêng lần chạy này.

    Mọi `__RUN__` trong `manifest` được thay bằng run id `<uuid8>`; tên mỗi tài nguyên phải chứa run id. Helper ép nhãn
    `mlops-ex=1`, `mlops-ex-run=<uuid8>`, trả danh sách `kind/tên` theo thứ tự, và xoá đúng các đối tượng đó trong
    `finally` (kể cả khi apply lỗi giữa chừng; `--wait=false`, ClusterQueue/ResourceFlavor có finalizer nên biến mất sau
    vài giây). Tài nguyên namespaced bị từ chối: dùng `apply_manifest` trong `k8s_namespace`.
    """
    require_kind()
    run = uuid.uuid4().hex[:8]
    rendered, names = _render_cluster_scoped(manifest, run, _cluster_scoped_kinds())
    try:
        result = kubectl("apply", "-f", "-", input=rendered)
        if result.returncode != 0:
            pytest.fail(f"kubectl apply (cluster-scoped) lỗi:\n{_tail(result)}", pytrace=False)
        yield names
    finally:
        for name in reversed(names):
            deleted = _kubectl_quiet("delete", name, "--ignore-not-found", "--wait=false", timeout=30)
            if deleted.returncode != 0:
                sys.stderr.write(f"mlopskit: không xoá được {name}:\n{_tail(deleted)}\n")


def _node_name() -> str:
    result = kubectl("get", "nodes", "-o", "jsonpath={.items[0].metadata.name}", timeout=30)
    if result.returncode != 0 or not result.stdout.strip():
        pytest.fail(f"Không lấy được tên node:\n{_tail(result)}", pytrace=False)
    return result.stdout.strip()


def _patch_node_status(node: str, ops: list[dict], quiet: bool = False) -> subprocess.CompletedProcess:
    import json

    args = ("patch", "node", node, "--subresource=status", "--type=json", "-p", json.dumps(ops))
    return _kubectl_quiet(*args, timeout=30) if quiet else kubectl(*args, timeout=30)


@contextmanager
def fake_extended_resource(name_suffix: str, quantity: int) -> Iterator[str]:
    """Thêm extended resource giả `mlops.example/<name_suffix>-<uuid8>` = `quantity` vào node, gỡ trong `finally`.

    Dùng để thực hành lập lịch kiểu `nvidia.com/gpu` (request/limit, quota Kueue) mà không cần GPU thật. Trả tên
    resource; chỉ trả về khi node đã báo `allocatable` cho resource này (scheduler thấy được).
    """
    if not re.fullmatch(r"[a-z0-9]([-a-z0-9]{0,40}[a-z0-9])?", name_suffix):
        raise ValueError("name_suffix chỉ gồm chữ thường, số, '-' (vd. 'gpu')")
    if quantity < 1:
        raise ValueError("quantity phải >= 1")
    require_kind()
    resource = f"{EXTENDED_DOMAIN}/{name_suffix}-{uuid.uuid4().hex[:8]}"
    path = resource.replace("~", "~0").replace("/", "~1")
    node = _node_name()
    try:
        added = _patch_node_status(node, [{"op": "add", "path": f"/status/capacity/{path}", "value": str(quantity)}])
        if added.returncode != 0:
            pytest.fail(f"Không thêm được {resource} vào node {node}:\n{_tail(added)}", pytrace=False)
        jsonpath = "jsonpath={.status.allocatable." + resource.replace(".", "\\.") + "}"
        deadline = time.monotonic() + 60
        while kubectl("get", "node", node, "-o", jsonpath, timeout=30).stdout.strip() != str(quantity):
            if time.monotonic() > deadline:
                pytest.fail(f"Node {node} chưa báo allocatable {resource}={quantity} sau 60 giây", pytrace=False)
            time.sleep(0.5)
        yield resource
    finally:
        _remove_extended_resource(node, resource)


def _remove_extended_resource(node: str, resource: str) -> None:
    path = resource.replace("~", "~0").replace("/", "~1")
    errors = []
    for field in ("capacity", "allocatable"):
        result = _patch_node_status(node, [{"op": "remove", "path": f"/status/{field}/{path}"}], quiet=True)
        if result.returncode != 0 and "nonexistent" not in result.stderr and "not found" not in result.stderr.lower():
            errors.append(_tail(result, 5))
    if errors:
        sys.stderr.write(f"mlopskit: không gỡ được {resource} khỏi node {node}:\n" + "\n".join(errors) + "\n")


def _cluster_reachable() -> bool:
    return _bin("kubectl") is not None and KIND_CLUSTER in _kind_clusters(timeout=10)


def _leftover_cluster_scoped() -> list[str]:
    """Best-effort: đối tượng cluster-scoped có nhãn `mlops-ex-run` (không tính namespace, đã có ở `_leftover_namespaces`).

    Dạng `<kind>.<group>/<tên>` như `kubectl get -o name`. Đối tượng đang xoá (có finalizer, vd. ClusterQueue chờ
    workload) chỉ tính khi kẹt quá 2 phút, giống namespace.
    """
    if not _cluster_reachable():
        return []
    jsonpath = ('jsonpath={range .items[*]}{.apiVersion} {.kind} {.metadata.name} '
                '{.metadata.deletionTimestamp}{"\\n"}{end}')
    now = datetime.now(timezone.utc)
    found = []
    for kinds in (CLUSTER_KINDS_CORE, CLUSTER_KINDS_SENIOR):
        result = _kubectl_quiet("get", kinds, "-l", RUN_LABEL, "-o", jsonpath, timeout=10)
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            api_version, kind, name, deleted = (line.split(" ") + ["", "", "", ""])[:4]
            if not name:
                continue
            if deleted:
                since = datetime.fromisoformat(deleted.replace("Z", "+00:00"))
                if (now - since).total_seconds() <= TERMINATING_GRACE_S:
                    continue
            group = api_version.rpartition("/")[0]
            found.append(f"{kind.lower()}.{group}/{name}" if group else f"{kind.lower()}/{name}")
    return found


def _leftover_extended_resources() -> list[str]:
    """Best-effort: extended resource `mlops.example/*` còn trên node (dạng `node/<tên>:<resource>`)."""
    if not _cluster_reachable():
        return []
    import json

    result = _kubectl_quiet("get", "nodes", "-o", "json", timeout=10)
    if result.returncode != 0:
        return []
    try:
        nodes = json.loads(result.stdout)["items"]
    except (ValueError, KeyError):
        return []
    found = set()
    for node in nodes:
        status = node.get("status", {})
        for field in ("capacity", "allocatable"):
            for key in status.get(field, {}):
                if key.startswith(f"{EXTENDED_DOMAIN}/"):
                    found.add(f"node/{node['metadata']['name']}:{key}")
    return sorted(found)


def require_kafka() -> str:
    """Skip khi Kafka của stack (profile `streaming`) chưa bật; trả bootstrap `127.0.0.1:<cổng>` cho client trên máy."""
    require_stack("kafka")
    return f"127.0.0.1:{stack_port('kafka')}"


def _kafka_admin(bootstrap: str, timeout_ms: int = 10000):
    from kafka.admin import KafkaAdminClient

    return KafkaAdminClient(bootstrap_servers=bootstrap, client_id=f"{PREFIX}admin", request_timeout_ms=timeout_ms)


@contextmanager
def kafka_topic(partitions: int = 1) -> Iterator[str]:
    """Topic tạm `mlops-ex-<uuid8>` (`partitions` partition, replication 1) trên Kafka của stack, xoá trong `finally`.

    Broker tắt tự tạo topic (`auto.create.topics.enable=false`): producer/consumer chỉ dùng được topic đã tạo.
    """
    bootstrap = require_kafka()
    from kafka.admin import NewTopic

    name = f"{PREFIX}{uuid.uuid4().hex[:8]}"
    admin = _kafka_admin(bootstrap)
    try:
        admin.create_topics([NewTopic(name=name, num_partitions=partitions, replication_factor=1)])
        deadline = time.monotonic() + 30
        while name not in admin.list_topics():
            if time.monotonic() > deadline:
                pytest.fail(f"Topic {name} chưa xuất hiện sau 30 giây", pytrace=False)
            time.sleep(0.2)
        yield name
    finally:
        try:
            admin.delete_topics([name], timeout_ms=30000)
        except Exception as error:
            if "UnknownTopicOrPartition" not in type(error).__name__:
                sys.stderr.write(f"mlopskit: không xoá được topic {name}: {error!r}\n")
        finally:
            admin.close()


def _leftover_kafka_topics() -> list[str]:
    """Best-effort: topic `mlops-ex-*` còn trên Kafka của stack; Kafka tắt thì trả `[]` ngay."""
    port = stack_port("kafka")
    if not _port_open(port):
        return []
    try:
        admin = _kafka_admin(f"127.0.0.1:{port}", timeout_ms=5000)
    except Exception:
        return []
    try:
        return [f"kafka-topic/{t}" for t in admin.list_topics() if t.startswith(PREFIX)]
    except Exception:
        return []
    finally:
        admin.close()


RAY_TMP_PREFIX = f"{PREFIX}ray-"


def _ray_processes(marker: str) -> list[int]:
    pids = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if marker in cmdline:
            pids.append(int(entry.name))
    return pids


def _kill_ray_processes(marker: str, grace: float = 5) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        pids = _ray_processes(marker)
        if not pids:
            return
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + grace
        while _ray_processes(marker) and time.monotonic() < deadline:
            time.sleep(0.1)


@contextmanager
def ray_local(num_cpus: int = 2) -> Iterator[Path]:
    """`ray.init` cục bộ `num_cpus` CPU, không dashboard; trả thư mục `storage` (dùng cho `RunConfig(storage_path=...)`).

    Tắt tích hợp `uv run` của Ray (`RAY_ENABLE_UV_RUN_RUNTIME_ENV=0`): khi pytest chạy qua `uv run`, Ray mặc định bắt
    worker chạy lại `uv run` trong bản sao thư mục làm việc (không có `.venv`), worker kẹt cài gói và trial Tune treo
    `PENDING` mãi. Thư mục tạm của Ray nằm ở `/tmp/mlops-ex-ray-<uuid8>` (đường dẫn ngắn vì giới hạn độ dài socket
    Unix). Trong `finally`: `ray.shutdown()`, diệt mọi tiến trình còn mang đường dẫn tạm này (raylet, worker mồ côi),
    xoá thư mục.
    """
    os.environ["RAY_ENABLE_UV_RUN_RUNTIME_ENV"] = "0"
    import ray
    from ray._private import ray_constants

    ray_constants.RAY_ENABLE_UV_RUN_RUNTIME_ENV = False
    if ray.is_initialized():
        pytest.fail("ray_local: Ray đã được init ở chỗ khác trong tiến trình này", pytrace=False)
    temp = Path(tempfile.mkdtemp(prefix=RAY_TMP_PREFIX, dir="/tmp"))
    storage = temp / "storage"
    storage.mkdir()
    try:
        ray.init(num_cpus=num_cpus, include_dashboard=False, _temp_dir=str(temp / "r"))
        yield storage
    finally:
        try:
            ray.shutdown()
        finally:
            _kill_ray_processes(str(temp))
            shutil.rmtree(temp, ignore_errors=True)


def _leftover_ray_dirs() -> list[str]:
    return sorted(str(p) for p in Path("/tmp").glob(f"{RAY_TMP_PREFIX}*"))
