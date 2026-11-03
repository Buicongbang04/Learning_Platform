import time

import k8sprodkit as kit
import mlopskit

from testkit import Exercise

ex = Exercise(__file__)
SMALL = {"cpu": "100m", "memory": "64Mi"}


def manifest() -> list[dict]:
    return kit.load_docs(ex.path("queues.yaml"))


def gpu_quota(cq: dict, gpu: str) -> dict:
    for group in (cq.get("spec") or {}).get("resourceGroups") or []:
        for flavor in group.get("flavors") or []:
            for resource in flavor.get("resources") or []:
                if resource.get("name") == gpu:
                    return resource
    return {}


def test_queue_contract():
    docs = manifest()
    flavors = kit.find_all(docs, "ResourceFlavor")
    assert flavors, "Cần ít nhất một ResourceFlavor"
    for team in ("team-a", "team-b"):
        cq = kit.find(docs, "ClusterQueue", f"{team}-{kit.RUN}")
        spec = cq.get("spec") or {}
        assert kit.RUN in str(spec.get("cohortName", "")), f"{team}: cohortName phải chứa {kit.RUN}"
        assert spec.get("namespaceSelector") is not None, f"{team}: namespaceSelector chưa cho namespace nào gửi job"
        quota = gpu_quota(cq, kit.GPU)
        assert kit.quantity(quota.get("nominalQuota", 0)) == 2, f"{team}: quota GPU danh nghĩa phải là 2"
        assert kit.quantity(quota.get("borrowingLimit", -1)) == 1, f"{team}: được mượn tối đa 1 GPU"
        local = kit.find(docs, "LocalQueue", team)
        assert (local.get("spec") or {}).get("clusterQueue") == f"{team}-{kit.RUN}", f"LocalQueue {team} trỏ sai ClusterQueue"
        assert "namespace" not in (local.get("metadata") or {}), "LocalQueue không ghi namespace (test tự đặt)"


def test_borrow_hold_reclaim_then_admit():
    test_queue_contract()
    mlopskit.require_senior_addons()
    with mlopskit.fake_extended_resource("gpu", 4) as gpu, mlopskit.k8s_namespace() as ns:
        docs = kit.substitute(manifest(), **{kit.GPU: gpu})
        with kit.applied(docs, ns):
            need = {**SMALL, gpu: "1"}
            double = {**SMALL, gpu: "2"}

            def submit(name: str, queue: str, resources: dict, seconds: int) -> None:
                mlopskit.apply_manifest(kit.dump([kit.job_manifest(name, queue, resources, seconds)]), ns)

            submit("b1", "team-b", need, 600)
            kit.wait_workload(ns, "b1", kit.admitted, 60, "chưa được admit dù team-b còn quota")
            submit("a1", "team-a", double, 45)
            kit.wait_workload(ns, "a1", kit.admitted, 60, "chưa được admit dù team-a còn quota danh nghĩa")
            submit("a2", "team-a", need, 600)
            kit.wait_workload(ns, "a2", kit.admitted, 60, "chưa được admit dù cohort còn GPU cho mượn")

            submit("a3", "team-a", need, 5)
            time.sleep(10)
            current = kit.workloads(ns)
            assert "a3" in current, "Job a3 không có Workload: Job chưa đi qua Kueue"
            assert not kit.admitted(current["a3"]), "Job a3 được admit dù team-a đã mượn hết hạn mức"

            submit("b2", "team-b", need, 5)
            kit.wait_workload(ns, "b2", kit.admitted, 90, "chưa được admit dù team-b chưa dùng hết quota danh nghĩa")
            evicted = [job for job, wl in kit.workloads(ns).items()
                       if job.startswith("a") and kit.condition(wl, "Evicted") is not None]
            assert evicted, "team-b lấy lại quota mà không job nào của team-a bị đẩy ra"

            kit.wait_workload(ns, "a3", kit.admitted, 150, "chưa được admit khi cohort đã có chỗ trống")
