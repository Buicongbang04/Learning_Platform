"""Công cụ dùng chung cho các bài tập của track MLOps: stack `setup/mlops`, MLflow cục bộ, build image và compose tạm."""
from __future__ import annotations

import os
import socket
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

import testkit

ROOT = testkit.ROOT
LABEL = "mlops-ex=1"
PREFIX = "mlops-ex-"
BUILD_TIMEOUT = 600
STACK_HINT = "docker compose -f setup/mlops/compose.yaml up -d"

STACK_SERVICES: dict[str, tuple[str, int]] = {
    "postgres": ("MLOPS_PG_PORT", 25433),
    "minio": ("MLOPS_MINIO_PORT", 29000),
    "mlflow": ("MLOPS_MLFLOW_PORT", 25000),
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


def require_stack(*services: str) -> None:
    for service in services:
        if not _port_open(stack_port(service)):
            pytest.skip(f"Stack MLOps chưa bật ({service}). Chạy: {STACK_HINT}")


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
        try:
            result = _docker(*command, timeout=BUILD_TIMEOUT)
        except subprocess.TimeoutExpired:
            pytest.fail(f"docker build quá {BUILD_TIMEOUT} giây", pytrace=False)
        if result.returncode != 0:
            pytest.fail(f"docker build lỗi ({result.returncode}):\n{_tail(result)}", pytrace=False)
        yield tag
    finally:
        _docker("rmi", "-f", tag)


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
        result = project._compose("up", "-d", "--build", "--wait", *services, timeout=BUILD_TIMEOUT)
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
