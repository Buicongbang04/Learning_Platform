from pathlib import Path

import k8skit
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
ORIGINAL = Path(__file__).parent / "fixtures" / "eta-api.original.yaml"
LOAD_SECONDS = 40


def budget(probe: dict) -> int:
    return probe.get("initialDelaySeconds", 0) + probe.get("periodSeconds", 10) * probe.get("failureThreshold", 3)


def deploy(ns: str, path: Path) -> None:
    docs = k8skit.with_image(k8skit.load_docs(path), k8skit.eta_image())
    container = k8skit.containers(k8skit.find(docs, "Deployment", "eta-api"))[0]
    k8skit.set_env(container, "MODEL_FETCH_SECONDS", str(LOAD_SECONDS))
    mlopskit.apply_manifest(k8skit.dump(docs), ns)


def container() -> dict:
    return k8skit.containers(k8skit.find(k8skit.load_docs(ex.path("eta-api.yaml")), "Deployment", "eta-api"))[0]


def test_original_manifest_restarts_while_loading():
    with mlopskit.k8s_namespace() as ns:
        deploy(ns, ORIGINAL)
        count = k8skit.wait_restarts(ns, "app=eta-api", 1, 120)
        assert count >= 1, "Bản gốc phải tái hiện triệu chứng: pod bị restart khi model còn đang nạp"


def test_probe_rules():
    api = container()
    startup = api.get("startupProbe") or {}
    assert "httpGet" in startup, "Cần startupProbe kiểu httpGet"
    assert 2 * LOAD_SECONDS <= budget(startup) <= 300, (
        f"Ngân sách startupProbe {budget(startup)} s, cần trong [{2 * LOAD_SECONDS}, 300]"
    )
    liveness = api.get("livenessProbe") or {}
    assert "httpGet" in liveness, "Giữ livenessProbe kiểu httpGet"
    assert liveness.get("initialDelaySeconds", 0) <= 15 and budget(liveness) <= 60, (
        "livenessProbe phải phát hiện treo trong vòng 60 s; đừng nới nó để che thời gian nạp model"
    )
    assert "httpGet" in (api.get("readinessProbe") or {}), "Giữ readinessProbe kiểu httpGet"


def test_becomes_ready_without_restarts():
    assert "startupProbe" in container(), "Chưa có startupProbe"
    with mlopskit.k8s_namespace() as ns:
        deploy(ns, ex.path("eta-api.yaml"))
        mlopskit.wait_for("deployment", "eta-api", "Available", ns, 4 * LOAD_SECONDS + 60)
        assert k8skit.restarts(ns, "app=eta-api") == 0, "Pod bị restart trong lúc nạp model"
        with mlopskit.port_forward(ns, "deployment/eta-api", 8080) as port:
            body = k8skit.call(port, "/predict", {"rows": k8skit.ROWS})
        assert body["model_version"] == "v1"
        assert body["predictions"] == pytest.approx(k8skit.expected_predictions("v1"), abs=1e-3)
