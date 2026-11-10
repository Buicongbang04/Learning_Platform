import shutil
import sys
import time
from pathlib import Path

import httpx
import yaml
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))


def prepare(root: Path, compose: Path) -> Path:
    from make_model import build

    shutil.copytree(FIXTURES / "service", root / "service")
    (root / "models").mkdir()
    build(root / "models" / "model.joblib")
    target = root / "compose.yaml"
    shutil.copyfile(compose, target)
    return target


def test_incident_compose_reproduces_the_symptom(tmp_path):
    target = prepare(tmp_path, FIXTURES / "compose.incident.yaml")
    with pytest.raises(pytest.fail.Exception):
        with mlopskit.compose_project(target):
            pass


def test_api_keeps_a_healthcheck():
    spec = yaml.safe_load(ex.read("compose.yaml"))
    check = spec["services"]["api"].get("healthcheck")
    assert check and check.get("test"), "Dịch vụ api phải có healthcheck chạy được (đừng xoá nó để `up --wait` qua)"


def test_stack_comes_up_healthy(tmp_path):
    target = prepare(tmp_path, ex.path("compose.yaml"))
    with mlopskit.compose_project(target) as project:
        url = f"http://127.0.0.1:{project.port('api', 8000)}"
        response = httpx.get(url + "/healthz", timeout=5)
        assert response.status_code == 200
        prediction = httpx.post(url + "/predict", json={"rows": [[5, 8, 1]]}, timeout=5)
        assert prediction.status_code == 200 and len(prediction.json()["predictions"]) == 1


def test_service_stays_up_without_restarts(tmp_path):
    target = prepare(tmp_path, ex.path("compose.yaml"))
    with mlopskit.compose_project(target) as project:
        time.sleep(8)
        logs = project.logs("api")
        assert logs.count("serving /models/model.joblib") == 1, f"Service khởi động nhiều lần (restart):\n{logs[-1500:]}"
        assert project.exec("api", "python", "-c", "print(1)").returncode == 0
