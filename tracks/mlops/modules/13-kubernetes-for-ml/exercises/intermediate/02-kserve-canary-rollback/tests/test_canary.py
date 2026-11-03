import time

import k8slab
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
URL = "http://eta/v1/models/eta:predict"
REQUESTS = 200


def docs(name: str) -> list[dict]:
    return k8slab.with_image(k8slab.load_docs(ex.path(name)), k8slab.eta_image())


def test_no_canary_traffic_percent_in_raw_mode():
    for doc in k8slab.load_docs(ex.path("canary.yaml")) + k8slab.load_docs(ex.path("rollback.yaml")):
        if doc.get("kind") == "InferenceService":
            assert "canaryTrafficPercent" not in doc["spec"].get("predictor", {}), (
                "Cluster chạy KServe RawDeployment: canaryTrafficPercent bị bỏ qua, đừng dựa vào nó"
            )


def deploy_canary(ns: str) -> None:
    mlopskit.apply_manifest(k8slab.dump(docs("canary.yaml")), ns)
    for name in ("eta-stable", "eta-canary"):
        mlopskit.wait_for("inferenceservice", name, "Ready", ns, 180)
    mlopskit.wait_for("deployment", "eta-stable-predictor", "jsonpath={.status.readyReplicas}=3", ns, 180)
    k8slab.wait_endpoints(ns, "eta", 4, 120)


@pytest.fixture(scope="module")
def canary():
    with mlopskit.k8s_namespace() as ns:
        try:
            deploy_canary(ns)
            yield ns, None
        except pytest.fail.Exception as error:
            yield ns, str(error)


def test_canary_gets_a_quarter_of_traffic(canary):
    canary, problem = canary
    if problem:
        pytest.fail(problem, pytrace=False)
    counts = k8slab.in_cluster_versions(canary, URL, REQUESTS)
    assert counts.get("error", 0) == 0, f"Có request lỗi qua Service eta: {counts}"
    share = counts.get("v2", 0) / REQUESTS
    assert counts.get("v1", 0) > 0, f"Không request nào tới v1: {counts}"
    assert 0.10 <= share <= 0.45, f"v2 nhận {share:.0%} traffic ({counts}), cần quanh 25% (cho phép 10-45%)"


def test_rollback_sends_zero_percent_to_canary(canary):
    canary, problem = canary
    if problem:
        pytest.fail(problem, pytrace=False)
    stable_before = k8slab.get_json("deployment", "eta-stable-predictor", canary)["metadata"]["generation"]
    mlopskit.apply_manifest(k8slab.dump(docs("rollback.yaml")), canary)
    selector = k8slab.get_json("service", "eta", canary)["spec"].get("selector") or {}
    behind_service = ",".join(f"{k}={v}" for k, v in selector.items())
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        serving = k8slab.pods(canary, behind_service)
        if not any(p["metadata"]["labels"].get("serving.kserve.io/inferenceservice") == "eta-canary" for p in serving):
            break
        time.sleep(3)
    counts = k8slab.in_cluster_versions(canary, URL, 100)
    assert counts == {"v1": 100}, f"Sau rollback vẫn còn traffic ngoài v1: {counts}"
    stable = k8slab.get_json("deployment", "eta-stable-predictor", canary)
    assert stable["metadata"]["generation"] == stable_before, "Rollback không được động vào eta-stable"
    assert stable["status"].get("readyReplicas") == 3
    canary_isvc = k8slab.get_json("inferenceservice", "eta-canary", canary)
    assert canary_isvc["spec"]["predictor"].get("containers"), "Giữ InferenceService eta-canary (để bật lại), chỉ đưa traffic về 0%"
