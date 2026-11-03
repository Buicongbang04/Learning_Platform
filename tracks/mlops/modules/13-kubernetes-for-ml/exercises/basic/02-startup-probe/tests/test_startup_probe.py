from pathlib import Path

import k8slab
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
ORIGINAL = Path(__file__).parent / "fixtures" / "eta-api.original.yaml"
LOAD_SECONDS = 40


def budget(probe: dict) -> int:
    return probe.get("initialDelaySeconds", 0) + probe.get("periodSeconds", 10) * probe.get("failureThreshold", 3)


def deploy(ns: str, path: Path) -> None:
    docs = k8slab.with_image(k8slab.load_docs(path), k8slab.eta_image())
    container = k8slab.containers(k8slab.find(docs, "Deployment", "eta-api"))[0]
    k8slab.set_env(container, "MODEL_FETCH_SECONDS", str(LOAD_SECONDS))
    mlopskit.apply_manifest(k8slab.dump(docs), ns)


def container() -> dict:
    return k8slab.containers(k8slab.find(k8slab.load_docs(ex.path("eta-api.yaml")), "Deployment", "eta-api"))[0]


def test_original_manifest_restarts_while_loading():
    with mlopskit.k8s_namespace() as ns:
        deploy(ns, ORIGINAL)
        count = k8slab.wait_restarts(ns, "app=eta-api", 1, 120)
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
        assert k8slab.restarts(ns, "app=eta-api") == 0, "Pod bị restart trong lúc nạp model"
        with mlopskit.port_forward(ns, "deployment/eta-api", 8080) as port:
            body = k8slab.call(port, "/predict", {"rows": k8slab.ROWS})
        assert body["model_version"] == "v1"
        assert body["predictions"] == pytest.approx(k8slab.expected_predictions("v1"), abs=1e-3)
