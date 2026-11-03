import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import mlopskit
import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))


class Broken:
    def __init__(self, message: str) -> None:
        self.message = message


def need(value):
    if isinstance(value, Broken):
        pytest.fail(value.message, pytrace=False)
    return value


@pytest.fixture(scope="module")
def spec() -> dict:
    return yaml.safe_load(ex.read("compose.yaml"))


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    from make_model import build

    root = tmp_path_factory.mktemp("stack")
    shutil.copytree(FIXTURES / "service", root / "service")
    shutil.copytree(FIXTURES / "mlflow", root / "mlflow")
    (root / "models").mkdir()
    build(root / "models" / "model.joblib")
    shutil.copyfile(ex.path("compose.yaml"), root / "compose.yaml")
    shutil.copyfile(ex.path("api.env"), root / "api.env")
    manager = mlopskit.compose_project(root / "compose.yaml")
    try:
        running = manager.__enter__()
    except (pytest.fail.Exception, subprocess.TimeoutExpired) as error:
        yield Broken(str(error))
        return
    try:
        yield running
    finally:
        manager.__exit__(None, None, None)


def service(spec: dict, name: str) -> dict:
    assert name in (spec.get("services") or {}), f"Thiếu dịch vụ `{name}` trong compose.yaml"
    return spec["services"][name]


def volume_mounts(item) -> tuple[str, str]:
    if isinstance(item, dict):
        return str(item.get("source", "")), str(item.get("target", ""))
    parts = str(item).split(":")
    return parts[0], (parts[1] if len(parts) > 1 else "")


def named_targets(spec: dict) -> list[str]:
    named = (spec.get("volumes") or {}).keys()
    mounts = [volume_mounts(item) for item in service(spec, "mlflow").get("volumes", [])]
    return [target for source, target in mounts if source in named]


def command_text(spec: dict) -> str:
    command = service(spec, "mlflow").get("command")
    return " ".join(command) if isinstance(command, list) else str(command)


def host_port_is_fixed(port) -> bool:
    if isinstance(port, dict):
        return bool(port.get("published"))
    text = str(port)
    return text.count(":") > 0 and not text.startswith("127.0.0.1::")


def container_port(port) -> int:
    if isinstance(port, dict):
        return int(port["target"])
    return int(str(port).split(":")[-1].split("/")[0])


def test_both_services_have_healthchecks(spec):
    for name in ("mlflow", "api"):
        check = service(spec, name).get("healthcheck")
        assert check and check.get("test"), f"`{name}` chưa có healthcheck.test"
        assert check.get("interval") and check.get("retries"), f"`{name}`: đặt interval và retries cho healthcheck"


def test_api_waits_for_healthy_mlflow(spec):
    depends = service(spec, "api").get("depends_on")
    assert isinstance(depends, dict), "depends_on phải ở dạng map có `condition`"
    assert depends.get("mlflow", {}).get("condition") == "service_healthy"


def test_mlflow_store_is_a_named_volume(spec):
    targets = named_targets(spec)
    assert targets, "MLflow phải ghi vào một named volume khai báo ở `volumes:` cấp cao nhất"
    command = command_text(spec)
    assert any(target in command for target in targets), (
        f"command của mlflow phải trỏ --backend-store-uri và --default-artifact-root vào {targets}"
    )
    assert "--backend-store-uri" in command and "--default-artifact-root" in command


def test_config_comes_from_env_file_and_ports_are_not_fixed(spec):
    assert service(spec, "api").get("env_file"), "Biến môi trường của API phải nằm trong env_file (api.env)"
    for name, needed in (("api", 8000), ("mlflow", 5000)):
        ports = service(spec, name).get("ports", [])
        assert needed in [container_port(port) for port in ports], f"{name} phải publish cổng container {needed}"
        for port in ports:
            assert not host_port_is_fixed(port), (
                f"{name}: cổng `{port}` cố định trên host; chỉ khai báo cổng container để Docker chọn cổng trống"
            )


def test_stack_comes_up_healthy(project):
    need(project)


def test_prediction_is_recorded_in_mlflow(project):
    project = need(project)
    api = f"http://127.0.0.1:{project.port('api', 8000)}"
    mlflow = f"http://127.0.0.1:{project.port('mlflow', 5000)}"
    response = httpx.post(api + "/predict", json={"rows": [[5, 8, 1], [12, 14, 2]]}, timeout=10)
    assert response.status_code == 200, response.text
    run_id = response.json()["run_id"]
    run = httpx.get(mlflow + "/api/2.0/mlflow/runs/get", params={"run_id": run_id}, timeout=10).json()["run"]
    metrics = {metric["key"]: metric["value"] for metric in run["data"]["metrics"]}
    assert metrics["predictions"] == 2


def test_mlflow_data_lives_on_the_volume(project, spec):
    project = need(project)
    target = named_targets(spec)[0]
    listing = project.exec("mlflow", "sh", "-c", f"ls -A {target} | head -20")
    assert listing.returncode == 0 and listing.stdout.strip(), f"Không thấy dữ liệu MLflow trong {target}: {listing.stderr}"
