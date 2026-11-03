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
    mlflow = service(spec, "mlflow")
    named = (spec.get("volumes") or {}).keys()
    mounts = [str(item).split(":") for item in mlflow.get("volumes", [])]
    targets = [parts[1] for parts in mounts if len(parts) >= 2 and parts[0] in named]
    assert targets, "MLflow phải ghi vào một named volume khai báo ở `volumes:` cấp cao nhất"
    command = mlflow.get("command")
    command = " ".join(command) if isinstance(command, list) else str(command)
    assert any(target in command for target in targets), (
        f"command của mlflow phải trỏ --backend-store-uri và --default-artifact-root vào {targets}"
    )
    assert "--backend-store-uri" in command and "--default-artifact-root" in command


def test_config_comes_from_env_file_and_ports_are_not_fixed(spec):
    api = service(spec, "api")
    assert api.get("env_file"), "Biến môi trường của API phải nằm trong env_file (api.env)"
    for name in ("api", "mlflow"):
        for port in service(spec, name).get("ports", []):
            text = str(port)
            assert text.count(":") == 0 or text.startswith("127.0.0.1::"), (
                f"{name}: cổng `{text}` cố định trên host; chỉ khai báo cổng container để Docker chọn cổng trống"
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
    command = service(spec, "mlflow")["command"]
    command = " ".join(command) if isinstance(command, list) else str(command)
    target = next(
        str(item).split(":")[1] for item in service(spec, "mlflow")["volumes"] if str(item).split(":")[0] in spec["volumes"]
    )
    assert target in command
    listing = project.exec("mlflow", "sh", "-c", f"ls {target}/mlruns | head -20")
    assert listing.returncode == 0 and listing.stdout.strip(), f"Không thấy dữ liệu MLflow trong {target}: {listing.stderr}"
