import copy
import time

import k8sprodkit as kit
import mlopskit

from testkit import Exercise

ex = Exercise(__file__)
REPLICAS = (1, 3)
SELECTOR = {"serving.kserve.io/inferenceservice": "eta-load"}


def isvc() -> dict:
    return kit.find(kit.load_docs(ex.path("isvc.yaml")), "InferenceService", "eta-load")


def with_replicas(doc: dict, n: int, image: str) -> dict:
    doc = kit.substitute([copy.deepcopy(doc)], **{kit.IMAGE: image})[0]
    doc["spec"]["predictor"]["minReplicas"] = n
    doc["spec"]["predictor"]["maxReplicas"] = n
    return doc


def metric(summary: dict, name: str) -> dict:
    found = (summary.get("metrics") or {}).get(name)
    assert found is not None, f"Summary của k6 không có metric {name}"
    return found


def test_isvc_contract():
    doc = isvc()
    annotations = (doc.get("metadata") or {}).get("annotations") or {}
    predictor = doc["spec"]["predictor"]
    fixed = predictor.get("minReplicas") is not None and predictor.get("minReplicas") == predictor.get("maxReplicas")
    assert annotations.get("serving.kserve.io/autoscalerClass") == "none" or fixed, \
        "Cần tắt autoscaler: autoscalerClass none hoặc minReplicas == maxReplicas"
    container = kit.containers(doc)[0]
    env = {e.get("name"): e.get("value") for e in container.get("env") or []}
    assert env.get("SERVICE_MS") == "20" and env.get("CONCURRENCY") == "1", "Không đổi SERVICE_MS, CONCURRENCY"


def check_predictor_pod(ns: str) -> None:
    """Kiểm pod predictor KServe thật sinh ra (không phải YAML): probe, resources, token API."""
    found = kit.pods(ns, "serving.kserve.io/inferenceservice=eta-load")
    assert found, "Không thấy pod predictor của eta-load"
    spec = found[0]["spec"]
    assert spec.get("automountServiceAccountToken") is False, "Pod serving không cần token API"
    container = next((c for c in spec["containers"] if c["name"] == "kserve-container"), None)
    assert container is not None, "Pod predictor không có container kserve-container"
    probe = (container.get("readinessProbe") or {}).get("httpGet") or {}
    assert probe.get("path") == "/v1/models/eta", "readinessProbe phải là httpGet vào /v1/models/eta"
    resources = container.get("resources") or {}
    for part in ("requests", "limits"):
        for key in ("cpu", "memory"):
            assert key in (resources.get(part) or {}), f"Pod predictor thiếu resources.{part}.{key}"


def measure(script, ns: str, n: int) -> tuple[float, float, float]:
    summary = kit.k6(script, kit.node_url(ns, "eta-load-np"))
    requests = metric(summary, "http_reqs")
    duration = metric(summary, "http_req_duration")
    failed = metric(summary, "http_req_failed")
    checks = metric(summary, "checks")
    assert requests.get("count", 0) > 0, "k6 không gửi request nào"
    assert checks.get("passes", 0) > 0, "Script k6 chưa có check nào chạy"
    assert any("thresholds" in m for m in summary["metrics"].values()), "Script k6 chưa khai báo thresholds"
    assert failed.get("value", 1) < 0.01, f"{n} replica: tỉ lệ lỗi {failed.get('value')}"
    return requests["rate"], duration["med"], duration["p(95)"]


def balanced(one: tuple[float, float, float], many: tuple[float, float, float]) -> bool:
    """Lần đo 3 replica trông như mọi pod đều nhận tải (chặt hơn ngưỡng chấm); không thì đo lại một lần."""
    return many[0] >= 2 * one[0] and many[1] <= 0.5 * one[1]


def test_throughput_scales_with_replicas():
    test_isvc_contract()
    script = ex.path("load.js")
    mlopskit.require_kind()
    image = kit.lab_image()
    results = {}
    with mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(kit.dump([kit.node_port_service("eta-load-np", SELECTOR, 8080)]), ns)
        for n in REPLICAS:
            mlopskit.apply_manifest(kit.dump([with_replicas(isvc(), n, image)]), ns)
            mlopskit.wait_for("inferenceservice", "eta-load", "Ready", ns, 180)
            kit.wait_until(lambda: kit.ready_endpoints(ns, "eta-load-np") == n, 180,
                           f"Service chưa có đúng {n} pod Ready")
            time.sleep(5)
            check_predictor_pod(ns)
            results[n] = measure(script, ns, n)
        if not balanced(results[1], results[3]):
            print(f"\nLần đo 3 replica đầu lệch {results[3]}, đo lại một lần (kết nối keep-alive chia lệch pod)")
            again = measure(script, ns, 3)
            results[3] = max(results[3], again, key=lambda r: r[0])

    print("\nreplica | req/s | median (ms) | p95 (ms)")
    for n, (rate, med, p95) in results.items():
        print(f"{n:>7} | {rate:5.1f} | {med:11.1f} | {p95:8.1f}")
    (one_rate, one_med, one_p95), (many_rate, many_med, many_p95) = results[1], results[3]
    assert many_rate >= 1.5 * one_rate, "Thông lượng không tăng theo số replica như kỳ vọng"
    assert many_med <= 0.7 * one_med, "Latency trung vị không giảm khi thêm replica như kỳ vọng"
    assert many_p95 <= 0.9 * one_p95, "p95 không giảm khi thêm replica như kỳ vọng"
