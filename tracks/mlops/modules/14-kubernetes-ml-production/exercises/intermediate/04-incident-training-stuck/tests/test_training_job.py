import time
from pathlib import Path

import k8sprodkit as kit
import mlopskit

from testkit import Exercise

ex = Exercise(__file__)
INCIDENT = ex.fixtures / "training.incident.yaml"


def quotas(docs: list[dict]) -> dict[str, float]:
    cq = kit.find(docs, "ClusterQueue", f"ml-train-{kit.RUN}")
    found = {}
    for group in (cq.get("spec") or {}).get("resourceGroups") or []:
        for flavor in group.get("flavors") or []:
            for resource in flavor.get("resources") or []:
                found[resource.get("name")] = found.get(resource.get("name"), 0) + kit.quantity(resource.get("nominalQuota", 0))
    return found


def by_name(items: list[dict]) -> dict[str, dict]:
    return {c.get("name"): c for c in items or []}


def run(path: Path, observe):
    mlopskit.require_senior_addons()
    with mlopskit.fake_extended_resource("gpu", 4) as gpu, mlopskit.k8s_namespace() as ns:
        docs = kit.substitute(kit.load_docs(path), **{kit.GPU: gpu})
        with kit.applied(docs, ns):
            observe(ns)


def test_contract_kept():
    original, mine = kit.load_docs(INCIDENT), kit.load_docs(ex.path("training.yaml"))
    assert quotas(mine) == quotas(original), "Quota của ClusterQueue ml-train do đội platform cấp, không được đổi"
    assert (kit.find(mine, "LocalQueue", "training").get("spec") or {}).get("clusterQueue") == f"ml-train-{kit.RUN}", \
        "LocalQueue training phải trỏ ClusterQueue ml-train"
    job, before = kit.find(mine, "Job", "train-eta"), kit.find(original, "Job", "train-eta")
    labels = (job.get("metadata") or {}).get("labels") or {}
    assert labels.get("kueue.x-k8s.io/queue-name") == "training", "Job phải gửi vào LocalQueue training"
    for field in ("parallelism", "completions", "completionMode"):
        assert job["spec"].get(field) == before["spec"].get(field), f"Không đổi {field} của Job"
    pod, pod_before = kit.pod_spec(job), kit.pod_spec(before)
    for part in ("initContainers", "containers"):
        mine_c, before_c = by_name(pod.get(part)), by_name(pod_before.get(part))
        assert set(mine_c) == set(before_c), f"Không thêm/bớt container trong {part}"
        for name, container in mine_c.items():
            assert container.get("command") == before_c[name].get("command"), f"Không đổi lệnh của {name}"
            assert container.get("image") == before_c[name].get("image"), f"Không đổi image của {name}"
    train = by_name(pod.get("containers"))["train"]
    for part in ("requests", "limits"):
        assert kit.quantity(((train.get("resources") or {}).get(part) or {}).get(kit.GPU, 0)) == 1, \
            "Mỗi worker training vẫn cần đúng 1 GPU"


def test_original_reproduces_symptom():
    def observe(ns: str) -> None:
        kit.wait_workload(ns, "train-eta", lambda w: True, 60, "không thấy Workload")
        time.sleep(20)
        workload = kit.workloads(ns)["train-eta"]
        job = kit.get_json("job", "train-eta", namespace=ns)
        stuck = not kit.admitted(workload) and job["spec"].get("suspend") is True and not kit.pods(ns)
        assert stuck, "Bản lúc sự cố không còn tái hiện triệu chứng (Job phải đứng yên, không có pod)"

    run(INCIDENT, observe)


def test_training_job_completes():
    test_contract_kept()

    def observe(ns: str) -> None:
        kit.wait_workload(ns, "train-eta", kit.admitted, 90, "Job vẫn chưa được chạy", details=False)
        mlopskit.wait_for("job", "train-eta", "Complete", ns, 180)
        job = kit.get_json("job", "train-eta", namespace=ns)
        assert (job.get("status") or {}).get("succeeded") == 2, "Cần cả 2 worker chạy xong"

    run(ex.path("training.yaml"), observe)
