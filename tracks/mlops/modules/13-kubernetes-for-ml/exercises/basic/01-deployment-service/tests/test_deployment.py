import k8slab
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)


def manifest() -> list[dict]:
    return k8slab.load_docs(ex.path("eta-api.yaml"))


def api_container(docs: list[dict]) -> dict:
    found = k8slab.containers(k8slab.find(docs, "Deployment", "eta-api"))
    assert found, "Deployment eta-api chưa có container"
    return found[0]


def test_config_comes_from_configmap():
    docs = manifest()
    config = k8slab.find(docs, "ConfigMap", "eta-api-config")
    assert config.get("data", {}).get("MODEL_PATH") == "/models/eta-v2.joblib", "ConfigMap thiếu MODEL_PATH của model v2"
    container = api_container(docs)
    hardcoded = [e for e in container.get("env") or [] if e.get("name") == "MODEL_PATH" and "value" in e]
    assert not hardcoded, "MODEL_PATH phải lấy từ ConfigMap, không ghi cứng trong env"
    prefixed = [s for s in container.get("envFrom") or [] if s.get("prefix")]
    assert not prefixed, "envFrom có prefix thì biến trong container không còn tên MODEL_PATH"
    refs = [s.get("configMapRef", {}).get("name") for s in container.get("envFrom") or []]
    refs += [e.get("valueFrom", {}).get("configMapKeyRef", {}).get("name") for e in container.get("env") or []]
    assert "eta-api-config" in refs, "Container chưa đọc ConfigMap eta-api-config"


def test_deployment_contract():
    docs = manifest()
    deployment = k8slab.find(docs, "Deployment", "eta-api")
    assert deployment["spec"].get("replicas") == 2, "Cần 2 replica"
    container = api_container(docs)
    resources = container.get("resources") or {}
    for part in ("requests", "limits"):
        for key in ("cpu", "memory"):
            assert key in (resources.get(part) or {}), f"Thiếu resources.{part}.{key}"
    assert "httpGet" in (container.get("readinessProbe") or {}), "Cần readinessProbe kiểu httpGet"
    pod = deployment["spec"]["template"]["spec"]
    assert pod.get("automountServiceAccountToken") is False, "Pod serving không cần token API: automountServiceAccountToken: false"
    assert (pod.get("securityContext") or {}).get("runAsNonRoot") is True, "Cần securityContext.runAsNonRoot: true ở mức pod"
    hardening = container.get("securityContext") or {}
    assert hardening.get("allowPrivilegeEscalation") is False, "Container cần allowPrivilegeEscalation: false"
    assert "ALL" in ((hardening.get("capabilities") or {}).get("drop") or []), "Container cần capabilities.drop: [ALL]"
    service = k8slab.find(docs, "Service", "eta-api")
    ports = service["spec"].get("ports") or []
    assert ports and ports[0].get("port") == 80, "Service eta-api phải mở cổng 80"


def test_serves_model_v1_through_service():
    docs = manifest()
    assert k8slab.find(docs, "Deployment", "eta-api")["spec"].get("replicas") == 2, "Cần 2 replica"
    docs = k8slab.with_image(docs, k8slab.eta_image())
    with mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(k8slab.dump(docs), ns)
        mlopskit.wait_for("deployment", "eta-api", "jsonpath={.status.readyReplicas}=2", ns, 180)
        with mlopskit.port_forward(ns, "svc/eta-api", 80) as port:
            health = k8slab.call(port, "/healthz")
            assert health["model_version"] == "v2", f"Service nạp model {health['model_version']}: MODEL_PATH chưa tới container"
            body = k8slab.call(port, "/predict", {"rows": k8slab.ROWS})
        assert body["model_version"] == "v2", f"Service đang trả model {body['model_version']}, cần v2"
        assert body["predictions"] == pytest.approx(k8slab.expected_predictions("v2"), abs=1e-3)
