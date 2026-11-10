import k8skit
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)


def manifest() -> list[dict]:
    return k8skit.load_docs(ex.path("isvc.yaml"))


def test_custom_predictor_shape():
    isvc = k8skit.find(manifest(), "InferenceService", "eta")
    predictor = isvc["spec"]["predictor"]
    annotations = isvc.get("metadata", {}).get("annotations") or {}
    fixed = predictor.get("minReplicas") is not None and predictor.get("minReplicas") == predictor.get("maxReplicas")
    assert annotations.get("serving.kserve.io/autoscalerClass") == "none" or fixed, (
        "Cluster không có metrics-server: autoscalerClass none hoặc minReplicas == maxReplicas"
    )
    assert "model" not in predictor, "Bài này dùng custom container, không dùng predictor.model (runtime có sẵn)"
    containers = predictor.get("containers") or []
    assert len(containers) == 1 and containers[0].get("name") == "kserve-container", (
        "Cần đúng một container tên kserve-container"
    )
    probe = containers[0].get("readinessProbe") or {}
    assert probe.get("httpGet", {}).get("path") == "/v1/models/eta", (
        "readinessProbe phải hỏi /v1/models/eta (model đã nạp), không chỉ kiểm cổng TCP"
    )


def test_serves_v2_over_http_not_just_ready():
    docs = k8skit.with_image(manifest(), k8skit.eta_image())
    with mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(k8skit.dump(docs), ns)
        mlopskit.wait_for("inferenceservice", "eta", "Ready", ns, 180)
        with mlopskit.port_forward(ns, "svc/eta-predictor", 80) as port:
            meta = k8skit.call(port, "/v1/models/eta")
            body = k8skit.call(port, "/v1/models/eta:predict", {"instances": k8skit.ROWS})
        assert meta["model_version"] == "v2", f"InferenceService Ready nhưng đang phục vụ model {meta['model_version']}"
        assert body["model_version"] == "v2", f"/predict trả model {body['model_version']}, cần v2"
        assert body["predictions"] == pytest.approx(k8skit.expected_predictions("v2"), abs=1e-3)
