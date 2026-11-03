import os
import re

import httpx
import k8sprodkit as kit
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
TRITON_IMAGE = "nvcr.io/nvidia/tritonserver:26.09-py3"
GATE = ("Bài Triton chạy thật chỉ khi MLOPS_TRITON=1: image NGC nhỏ nhất có server là "
        f"{TRITON_IMAGE} (9,04 GB nén, ~2 lần khi giải nén, không có bản CPU-only), vượt ngân sách đĩa và thời gian "
        "của module. Kéo trước bằng `docker pull` rồi đặt MLOPS_TRITON=1")


def config() -> str:
    text = ex.read("triton/eta/config.pbtxt")
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def field(text: str, name: str) -> str | None:
    match = re.search(rf"\b{name}\s*:\s*([A-Za-z0-9_]+)", text)
    return match.group(1) if match else None


def block(text: str, name: str, open_: str, close: str) -> str | None:
    match = re.search(rf"\b{name}\s*{re.escape(open_)}(.*?){re.escape(close)}", text, re.S)
    return match.group(1) if match else None


def test_triton_config():
    text = config()
    assert re.search(r'^name\s*:\s*"eta"', text, re.M), "Model phải tên eta"
    batch = int(field(text, "max_batch_size") or 0)
    assert 8 <= batch <= 64, "max_batch_size phải từ 8 đến 64"
    dynamic = block(text, "dynamic_batching", "{", "}")
    assert dynamic is not None, "Thiếu dynamic_batching"
    delay = field(dynamic, "max_queue_delay_microseconds")
    assert delay is not None and 0 < int(delay) <= 5000, "max_queue_delay_microseconds phải từ 1 đến 5000"
    group = block(text, "instance_group", "[", "]")
    assert group is not None, "Thiếu instance_group"
    assert field(group, "kind") == "KIND_CPU" and field(group, "count") == "2", "Cần 2 instance KIND_CPU"


def metric_value(text: str, name: str) -> float:
    total = 0.0
    for line in text.splitlines():
        if line.startswith(name + "{") and 'model="eta"' in line:
            total += float(line.rsplit(" ", 1)[1])
    return total


@pytest.mark.skipif(os.environ.get("MLOPS_TRITON") != "1", reason=GATE)
def test_triton_batches_under_load():
    test_triton_config()
    mlopskit.require_kind()
    mlopskit.kind_load(TRITON_IMAGE, timeout=1800)
    configmap = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "triton-models"},
                 "data": {"config.pbtxt": ex.read("triton/eta/config.pbtxt"),
                          "model.py": ex.read("triton/eta/1/model.py")}}
    with mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(kit.dump([configmap]), ns)
        mlopskit.apply_manifest(ex.fixtures / "triton.yaml", ns)
        mlopskit.apply_manifest(kit.dump([kit.node_port_service("triton-np", {"app": "triton"}, 8000)]), ns)
        mlopskit.wait_for("deployment", "triton", "Available", ns, 600)
        kit.wait_until(lambda: kit.ready_endpoints(ns, "triton-np") == 1, 120, "Service Triton chưa có pod Ready")
        summary = kit.k6(ex.fixtures / "triton-load.js", kit.node_url(ns, "triton-np"))
        with mlopskit.port_forward(ns, "deploy/triton", 8002) as port:
            metrics = httpx.get(f"http://127.0.0.1:{port}/metrics", timeout=10).text
    requests = metric_value(metrics, "nv_inference_request_success")
    executions = metric_value(metrics, "nv_inference_exec_count")
    rate = summary["metrics"]["http_reqs"]["rate"]
    p95 = summary["metrics"]["http_req_duration"]["p(95)"]
    print(f"\nTriton: {rate:.1f} req/s, p95 {p95:.1f} ms, {requests:.0f} request / {executions:.0f} lần chạy model")
    assert summary["metrics"]["http_req_failed"]["value"] < 0.01, "Triton trả lỗi dưới tải"
    assert requests > 0 and executions < requests / 2, "Dynamic batching không gộp request như kỳ vọng"
