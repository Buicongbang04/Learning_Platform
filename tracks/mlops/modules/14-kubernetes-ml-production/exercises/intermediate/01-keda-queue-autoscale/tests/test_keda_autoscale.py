import time

import k8sprodkit as kit
import mlopskit

from testkit import Exercise

ex = Exercise(__file__)
JOBS = 160
JOB_SECONDS = 0.5


def scaled_object() -> dict:
    return kit.find(kit.load_docs(ex.path("scaledobject.yaml")), "ScaledObject", "worker-autoscale")


def test_scaledobject_contract():
    spec = scaled_object().get("spec") or {}
    assert (spec.get("scaleTargetRef") or {}).get("name") == "batch-worker", "scaleTargetRef phải trỏ Deployment batch-worker"
    assert spec.get("minReplicaCount") == 0, "minReplicaCount phải là 0 (scale-to-zero)"
    assert spec.get("maxReplicaCount") == 4, "maxReplicaCount phải là 4"
    assert 1 <= int(spec.get("pollingInterval", 30)) <= 10, "pollingInterval phải từ 1 đến 10 giây"
    assert 1 <= int(spec.get("cooldownPeriod", 300)) <= 30, "cooldownPeriod phải từ 1 đến 30 giây"
    types = [t.get("type") for t in spec.get("triggers") or []]
    assert types == ["metrics-api"], "Cần đúng một trigger kiểu metrics-api"


def test_scales_with_queue_and_back_to_zero():
    mlopskit.require_senior_addons()
    image = kit.lab_image()
    with mlopskit.k8s_namespace() as ns:
        values = {kit.IMAGE: image, kit.NAMESPACE: ns}
        fixture = kit.substitute(kit.load_docs(ex.fixtures / "batch-inference.yaml"), **values)
        mlopskit.apply_manifest(kit.dump(fixture), ns)
        mlopskit.wait_for("deployment", "batch-queue", "Available", ns, 180)
        mlopskit.apply_manifest(kit.dump(kit.substitute([scaled_object()], **values)), ns)
        mlopskit.wait_for("scaledobject", "worker-autoscale", "Ready", ns, 120)
        kit.wait_until(lambda: mlopskit.kubectl("get", "hpa", "keda-hpa-worker-autoscale", namespace=ns).returncode == 0,
                       60, "KEDA chưa tạo HPA keda-hpa-worker-autoscale")
        hpa = kit.get_json("hpa", "keda-hpa-worker-autoscale", namespace=ns)["spec"]
        assert hpa.get("maxReplicas") == 4, f"HPA do KEDA tạo có maxReplicas {hpa.get('maxReplicas')}, cần 4"
        assert hpa.get("scaleTargetRef", {}).get("name") == "batch-worker", "HPA do KEDA tạo không trỏ batch-worker"
        kit.wait_until(lambda: kit.replicas(ns, "batch-worker") == 0, 120,
                       "Deployment batch-worker chưa về 0 replica khi hàng đợi rỗng")

        with mlopskit.port_forward(ns, "svc/batch-queue", 8080) as port:
            kit.call(port, "/enqueue", {"n": JOBS, "seconds": JOB_SECONDS})
            peak, deadline = 0, time.monotonic() + 240
            while time.monotonic() < deadline:
                peak = max(peak, kit.replicas(ns, "batch-worker"))
                stats = kit.call(port, "/stats")
                if stats["done"] >= JOBS:
                    break
                time.sleep(2)
            assert stats["done"] >= JOBS, f"Sau 240 giây mới xong {stats['done']}/{JOBS} job"
            assert peak <= 4, f"Số replica cao nhất {peak} vượt 4"
            assert peak >= 3, f"Số replica cao nhất khi có tải là {peak}, cần tăng lên ít nhất 3"
            assert len(stats["pods"]) >= 3, f"Chỉ {len(stats['pods'])} pod worker đã xử lý job, cần ít nhất 3"
            cold = stats["cold_start_s"]
            assert cold is not None and 0 < cold < 120, f"Cold start đo được không hợp lệ: {cold}"
            print(f"\nCold start (enqueue khi 0 replica → job đầu được lấy): {cold:.1f} s; replica cao nhất {peak}")

        kit.wait_until(lambda: kit.replicas(ns, "batch-worker") == 0, 150,
                       "Hết việc mà Deployment batch-worker chưa về 0 replica")

