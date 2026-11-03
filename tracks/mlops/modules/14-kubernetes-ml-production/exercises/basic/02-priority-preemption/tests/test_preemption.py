import time

import k8sprodkit as kit
import mlopskit

from testkit import Exercise

ex = Exercise(__file__)
CLASSES = ("ml-serving", "ml-research", "ml-training")


def classes() -> dict[str, dict]:
    docs = kit.load_docs(ex.path("priorityclasses.yaml"))
    found = {}
    for prefix in CLASSES:
        found[prefix] = kit.find(docs, "PriorityClass", f"{prefix}-{kit.RUN}")
    return found


def pod(name: str, priority_class: str, gpu: str) -> dict:
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": name, "labels": {"app": name.rsplit("-", 1)[0]}},
        "spec": {
            "priorityClassName": priority_class,
            "terminationGracePeriodSeconds": 1,
            "automountServiceAccountToken": False,
            "containers": [{
                "name": "main",
                "image": kit.JOB_IMAGE,
                "imagePullPolicy": "IfNotPresent",
                "command": ["sh", "-c", "sleep 600"],
                "resources": {"requests": {"cpu": "10m", "memory": "16Mi", gpu: "1"},
                              "limits": {"cpu": "100m", "memory": "32Mi", gpu: "1"}},
            }],
        },
    }


def phases(ns: str) -> dict[str, str]:
    return {p["metadata"]["name"]: p["status"].get("phase", "") for p in kit.pods(ns)
            if not p["metadata"].get("deletionTimestamp")}


def test_priority_contract():
    found = classes()
    for prefix, doc in found.items():
        assert doc.get("globalDefault") is not True, f"{prefix}: không được globalDefault (cluster dùng chung)"
        assert isinstance(doc.get("value"), int), f"{prefix}: value phải là số nguyên"
    values = {prefix: doc["value"] for prefix, doc in found.items()}
    assert values["ml-serving"] > values["ml-research"] > values["ml-training"] > 0, \
        "Thứ tự ưu tiên chưa đúng yêu cầu của đề"
    assert values["ml-serving"] < 1_000_000_000, "Giá trị từ 1 tỉ trở lên dành cho class hệ thống"
    assert found["ml-research"].get("preemptionPolicy") == "Never", "ml-research chưa đúng chính sách của đề"
    assert found["ml-serving"].get("preemptionPolicy", "PreemptLowerPriority") == "PreemptLowerPriority", \
        "ml-serving chưa đúng chính sách của đề"


def test_serving_preempts_training_but_research_waits():
    test_priority_contract()
    found = classes()
    mlopskit.require_kind()
    with mlopskit.fake_extended_resource("gpu", 2) as gpu, \
            kit.applied(list(found.values()), "") as run, \
            mlopskit.k8s_namespace() as ns:
        name = {prefix: f"{prefix}-{run}" for prefix in CLASSES}
        for i in (1, 2):
            mlopskit.apply_manifest(kit.dump([pod(f"train-{i}", name["ml-training"], gpu)]), ns)
        for i in (1, 2):
            mlopskit.wait_for("pod", f"train-{i}", "Ready", ns, 120)

        mlopskit.apply_manifest(kit.dump([pod("research-1", name["ml-research"], gpu)]), ns)
        time.sleep(15)
        state = phases(ns)
        assert state.get("research-1") == "Pending", "Pod research không được chạy khi hết GPU"
        assert state.get("train-1") == "Running" and state.get("train-2") == "Running", \
            "Pod training bị đẩy ra khi pod research xếp hàng"

        mlopskit.apply_manifest(kit.dump([pod("serving-1", name["ml-serving"], gpu)]), ns)
        mlopskit.wait_for("pod", "serving-1", "Ready", ns, 120)
        state = phases(ns)
        training = [n for n in state if n.startswith("train-")]
        assert len(training) == 1, f"Cần đúng một pod training bị đẩy ra, còn lại {training}"
        assert state.get("research-1") == "Pending", "Pod research không được chạy khi hết GPU"

