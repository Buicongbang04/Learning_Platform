import os
import re

import httpx
import k8sprodkit as kit
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
TRITON_IMAGE = "nvcr.io/nvidia/tritonserver:26.09-py3"
GATE = ("Bài Triton chạy thật chỉ khi MLOPS_TRITON=1 (CHƯA chạy thật lần nào khi viết bài): image NGC nhỏ nhất có "
        f"server là {TRITON_IMAGE} (9,04 GB nén, không có bản CPU-only); kéo + nạp vào kind tốn ~2–3 lần trên đĩa "
        "(Docker, tar tạm ~/.cache/mlops-kind/load, containerd của node), vượt ngân sách của module. "
        "Kéo trước bằng `docker pull` rồi đặt MLOPS_TRITON=1; gỡ khỏi node: "
        f"docker exec mlops-control-plane crictl rmi {TRITON_IMAGE}")


TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|#.*|[{}\[\]<>:,;]|[^\s{}\[\]<>:,;"#]+')
CLOSE = {"{": "}", "<": ">"}


def tokens(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        for token in TOKEN.findall(line):
            if token.startswith("#"):
                break
            found.append(token)
    return found


def parse(text: str) -> dict:
    """Đọc protobuf text format (`config.pbtxt`) thành dict tên trường → danh sách giá trị; chịu `{}`, `<>`, `[]` lồng, `;`."""
    items, pos = tokens(text), 0

    def scalar(token: str):
        if token.startswith('"'):
            return token[1:-1]
        try:
            return int(token)
        except ValueError:
            try:
                return float(token)
            except ValueError:
                return token

    def value():
        nonlocal pos
        token = items[pos]
        pos += 1
        if token in CLOSE:
            return message(CLOSE[token])
        return scalar(token)

    def message(close: str | None) -> dict:
        nonlocal pos
        fields: dict[str, list] = {}
        while pos < len(items) and items[pos] != close:
            name = items[pos]
            pos += 1
            if pos < len(items) and items[pos] == ":":
                pos += 1
            if pos < len(items) and items[pos] == "[":
                pos += 1
                while items[pos] != "]":
                    fields.setdefault(name, []).append(value())
                    if items[pos] in (",", ";"):
                        pos += 1
                pos += 1
            else:
                fields.setdefault(name, []).append(value())
            if pos < len(items) and items[pos] in (",", ";"):
                pos += 1
        if close is not None:
            pos += 1
        return fields

    try:
        return message(None)
    except IndexError:
        pytest.fail("config.pbtxt không đúng cú pháp protobuf text format (thiếu dấu đóng?)", pytrace=False)


def config() -> dict:
    return parse(ex.read("triton/eta/config.pbtxt"))


def one(fields: dict, name: str, default=None):
    values = fields.get(name) or []
    return values[0] if values else default


def test_triton_config():
    text = config()
    assert one(text, "name") == "eta", "Model phải tên eta"
    batch = one(text, "max_batch_size", 0)
    assert isinstance(batch, int) and 8 <= batch <= 64, "max_batch_size phải từ 8 đến 64"
    dynamic = one(text, "dynamic_batching")
    assert isinstance(dynamic, dict), "Thiếu dynamic_batching"
    delay = one(dynamic, "max_queue_delay_microseconds")
    assert isinstance(delay, int) and 0 < delay <= 5000, "max_queue_delay_microseconds phải từ 1 đến 5000"
    groups = [g for g in text.get("instance_group") or [] if isinstance(g, dict)]
    assert groups, "Thiếu instance_group"
    assert all(one(g, "kind", "KIND_AUTO") == "KIND_CPU" for g in groups), "Mọi instance_group phải là KIND_CPU"
    counts = [one(g, "count", 1) for g in groups]
    assert all(isinstance(c, int) and not isinstance(c, bool) for c in counts), "count của instance_group phải là số nguyên"
    assert sum(counts) == 2, "Cần tổng cộng 2 instance KIND_CPU"


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
