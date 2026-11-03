import time
from pathlib import Path

import k8skit
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
INCIDENT = Path(__file__).parent / "fixtures" / "eta-api.incident.yaml"
WATCH_SECONDS = 30


def deploy(ns: str, path: Path) -> None:
    mlopskit.apply_manifest(k8skit.dump(k8skit.with_image(k8skit.load_docs(path), k8skit.eta_image())), ns)


def api() -> dict:
    return k8skit.containers(k8skit.find(k8skit.load_docs(ex.path("eta-api.yaml")), "Deployment", "eta-api"))[0]


def test_incident_manifest_reproduces_the_symptom():
    with mlopskit.k8s_namespace() as ns:
        deploy(ns, INCIDENT)
        count = k8skit.wait_restarts(ns, "app=eta-api", 2, 150)
        assert count >= 2, "Bản lúc sự cố phải tái hiện triệu chứng: pod khởi động lại nhiều lần"


def test_contract_kept():
    container = api()
    env = {e.get("name"): e.get("value") for e in container.get("env") or []}
    assert env.get("MODEL_PATH") == "/models/eta-v3.joblib", "Bản phải deploy vẫn là model v3"
    assert "httpGet" in (container.get("livenessProbe") or {}) and "httpGet" in (container.get("readinessProbe") or {}), (
        "Giữ livenessProbe và readinessProbe"
    )
    resources = container.get("resources") or {}
    for part in ("requests", "limits"):
        for key in ("cpu", "memory"):
            assert key in (resources.get(part) or {}), f"Phải khai báo resources.{part}.{key}"
    limits, requests = resources["limits"], resources["requests"]
    assert k8skit.quantity(limits["cpu"]) <= 2 and k8skit.quantity(limits["memory"]) <= 2**30, (
        "Vượt ngân sách namespace: limits tối đa 2 CPU và 1Gi"
    )
    for key in ("cpu", "memory"):
        assert k8skit.quantity(requests[key]) <= k8skit.quantity(limits[key]), f"requests.{key} lớn hơn limits.{key}"


def test_v3_serves_without_restarts():
    with mlopskit.k8s_namespace() as ns:
        deploy(ns, ex.path("eta-api.yaml"))
        k8skit.wait_available(ns, "eta-api", "app=eta-api", 180)
        time.sleep(WATCH_SECONDS)
        assert k8skit.restarts(ns, "app=eta-api") == 0, f"Pod vẫn khởi động lại trong {WATCH_SECONDS} giây theo dõi"
        with mlopskit.port_forward(ns, "svc/eta-api", 80) as port:
            body = k8skit.call(port, "/predict", {"rows": k8skit.ROWS})
        assert body["model_version"] == "v3"
        assert body["predictions"] == pytest.approx(k8skit.expected_predictions("v3"), abs=1e-3)
