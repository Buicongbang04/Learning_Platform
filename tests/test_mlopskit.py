import subprocess

import pytest

import mlopskit
import testkit


def _docker_image_exists(tag: str) -> bool:
    result = subprocess.run(["docker", "image", "inspect", tag], capture_output=True, text=True)
    return result.returncode == 0


def _need_docker():
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")


def _busybox():
    _need_docker()
    if subprocess.run(["docker", "image", "inspect", "busybox:1.37"], capture_output=True).returncode != 0:
        subprocess.run(["docker", "pull", "busybox:1.37"], capture_output=True, timeout=300)


def test_stack_services_table():
    assert mlopskit.STACK_SERVICES == {
        "postgres": ("MLOPS_PG_PORT", 25433),
        "minio": ("MLOPS_MINIO_PORT", 29000),
        "mlflow": ("MLOPS_MLFLOW_PORT", 25000),
    }


def test_stack_port_default(monkeypatch):
    monkeypatch.delenv("MLOPS_MLFLOW_PORT", raising=False)
    assert mlopskit.stack_port("mlflow") == 25000


def test_stack_port_env(monkeypatch):
    monkeypatch.setenv("MLOPS_MLFLOW_PORT", "25999")
    assert mlopskit.stack_port("mlflow") == 25999


def test_require_stack_down_skips(monkeypatch):
    monkeypatch.setenv("MLOPS_MLFLOW_PORT", str(testkit.free_port()))
    with pytest.raises(pytest.skip.Exception) as info:
        mlopskit.require_stack("mlflow")
    assert "docker compose -f setup/mlops/compose.yaml up -d" in str(info.value)
    assert "mlflow" in str(info.value)


def test_require_stack_up_passes(monkeypatch):
    import socket

    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        monkeypatch.setenv("MLOPS_MLFLOW_PORT", str(server.getsockname()[1]))
        mlopskit.require_stack("mlflow")


def test_mlflow_local_roundtrip(tmp_path):
    import mlflow

    uri = mlopskit.mlflow_local(tmp_path)
    assert uri.startswith("sqlite:///")
    assert str(tmp_path) in uri
    with mlflow.start_run():
        mlflow.log_metric("mae", 1.0)
    runs = mlflow.search_runs()
    assert len(runs) == 1
    assert runs["metrics.mae"].iloc[0] == 1.0


def test_built_image_removed(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\n")
    with mlopskit.built_image(tmp_path) as tag:
        assert tag.startswith("mlops-ex-") and tag.endswith(":test")
        assert _docker_image_exists(tag)
    assert not _docker_image_exists(tag)


def test_built_image_removed_on_error(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\n")
    holder = []
    with pytest.raises(RuntimeError):
        with mlopskit.built_image(tmp_path) as tag:
            holder.append(tag)
            raise RuntimeError("boom")
    assert not _docker_image_exists(holder[0])


def test_built_image_build_args(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\nARG WHO=x\nENV WHO=$WHO\n")
    with mlopskit.built_image(tmp_path, build_args={"WHO": "mlops"}) as tag:
        out = subprocess.run(["docker", "run", "--rm", tag, "sh", "-c", "echo $WHO"], capture_output=True, text=True)
        assert out.stdout.strip() == "mlops"


def test_built_image_failure_reports_log(tmp_path):
    _busybox()
    (tmp_path / "Dockerfile").write_text("FROM busybox:1.37\nRUN exit 3\n")
    with pytest.raises(pytest.fail.Exception):
        with mlopskit.built_image(tmp_path):
            pass


COMPOSE = """services:
  app:
    image: busybox:1.37
    command: sleep 300
"""


def test_compose_roundtrip_and_down(tmp_path):
    _busybox()
    (tmp_path / "compose.yaml").write_text(COMPOSE)
    with mlopskit.compose_project(tmp_path / "compose.yaml") as project:
        assert project.name.startswith("mlops-ex-")
        assert project.exec("app", "echo", "hi").stdout.strip() == "hi"
        assert isinstance(project.logs("app"), str)
        name = project.name
        assert mlopskit.leftovers(name)
    assert mlopskit.leftovers(name) == []


def test_compose_down_on_error(tmp_path):
    _busybox()
    (tmp_path / "compose.yaml").write_text(COMPOSE)
    with pytest.raises(RuntimeError):
        with mlopskit.compose_project(tmp_path / "compose.yaml") as project:
            name = project.name
            raise RuntimeError("boom")
    assert mlopskit.leftovers(name) == []
