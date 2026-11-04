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
        cohort = (cq.get("spec") or {}).get("cohortName")
        assert cohort is None or kit.RUN in str(cohort), f"{team}: tên cohort phải chứa {kit.RUN} (không trùng lần chạy khác)"
        quota = gpu_quota(cq, kit.GPU)
        assert kit.quantity(quota.get("nominalQuota", 0)) == 2, f"{team}: quota GPU danh nghĩa phải là 2"
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

            burst = [f"x{i}" for i in range(1, 5)]
            for name in burst:
                submit(name, "team-a", need, 600)
            kit.wait_until(lambda: sum(kit.admitted(w) for j, w in kit.workloads(ns).items() if j in burst) >= 3, 60,
                           "team-a nộp 4 job 1 GPU khi team-b rảnh mà chưa tới 3 job được admit")
            time.sleep(10)
            current = kit.workloads(ns)
            running = sum(kit.admitted(current[j]) for j in burst if j in current)
            assert len([j for j in burst if j in current]) == 4, "Có job không đi qua Kueue"
            assert running == 3, f"team-a nộp 4 job 1 GPU khi team-b rảnh: {running} job được admit, cần đúng 3"
            kit.delete(ns, *burst)
            kit.wait_until(lambda: not set(burst) & set(kit.workloads(ns)), 60, "Workload của các job đã xoá chưa biến mất")

            submit("b1", "team-b", need, 600)
            kit.wait_workload(ns, "b1", kit.admitted, 60, "chưa được admit dù team-b còn quota")
            submit("a1", "team-a", double, 90)
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
