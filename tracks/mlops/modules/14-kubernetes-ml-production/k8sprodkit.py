"""Tiện ích chung cho test module 14: image lab, đọc manifest, tách tài nguyên cluster-scoped, đọc Workload Kueue, gọi k6.

Mọi lệnh tới Docker và cluster đi qua `mlopskit` (context `kind-mlops`, namespace tạm `mlops-ex-*`, tài nguyên
cluster-scoped có hậu tố run id và được xoá trong `finally`).
"""

import json
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import httpx
import mlopskit
import pytest
import yaml

LAB = Path(__file__).resolve().parent / "lab" / "service"
IMAGE = "ml-lab:dev"
JOB_IMAGE = "busybox:1.37"
RUN = mlopskit.RUN_TOKEN
GPU = "__GPU__"
NAMESPACE = "__NAMESPACE__"
CLUSTER_KINDS = {"ResourceFlavor", "ClusterQueue", "Cohort", "PriorityClass", "WorkloadPriorityClass"}
_CACHE: dict[str, str] = {}


def lab_image() -> str:
    """Build `lab/service` một lần mỗi phiên pytest, nạp vào node kind, trả tag thay cho `ml-lab:dev`."""
    mlopskit.require_kind()
    if "image" not in _CACHE:
        with mlopskit.built_image(LAB) as tag:
            mlopskit.kind_load(tag)
        _CACHE["image"] = tag
    return _CACHE["image"]


def load_docs(path: Path) -> list[dict]:
    try:
        docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} không phải YAML hợp lệ: {error}", pytrace=False)
    if not all(isinstance(d, dict) for d in docs):
        pytest.fail(f"{path.name}: mỗi document phải là một object Kubernetes", pytrace=False)
    return docs


def find(docs: list[dict], kind: str, name: str | None = None) -> dict:
    for doc in docs:
        if doc.get("kind") == kind and (name is None or (doc.get("metadata") or {}).get("name") == name):
            return doc
    pytest.fail(f"Không thấy {kind}{' ' + name if name else ''} trong manifest", pytrace=False)


def find_all(docs: list[dict], kind: str) -> list[dict]:
    return [d for d in docs if d.get("kind") == kind]


def dump(docs: list[dict]) -> str:
    return yaml.safe_dump_all(docs, sort_keys=False)


def substitute(docs: list[dict], **values: str) -> list[dict]:
    """Thay chuỗi giữ chỗ (`__GPU__`, `__NAMESPACE__`, `ml-lab:dev`...) ở mọi chỗ trong manifest, kể cả khoá."""
    text = dump(docs)
    for placeholder, value in values.items():
        text = text.replace(placeholder, value)
    return [d for d in yaml.safe_load_all(text) if d]


def pod_spec(doc: dict) -> dict:
    spec = doc.get("spec") or {}
    if doc.get("kind") == "Pod":
        return spec
    if doc.get("kind") == "InferenceService":
        return spec.get("predictor") or {}
    return (spec.get("template") or {}).get("spec") or {}


def containers(doc: dict) -> list[dict]:
    return pod_spec(doc).get("containers") or []


QUANTITY = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))(?:([eE][+-]?\d+)|(Ki|Mi|Gi|Ti|Pi|Ei|n|u|m|k|M|G|T|P|E))?$")
BINARY = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "Pi": 2**50, "Ei": 2**60}
DECIMAL = {"n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15, "E": 1e18}


def quantity(value) -> float:
    """Đổi quantity K8s (`500m`, `256Mi`, `1Gi`, `2`) ra số (CPU theo nhân, bộ nhớ theo byte)."""
    match = QUANTITY.match(str(value).strip())
    if not match:
        pytest.fail(f"{value!r} không phải quantity Kubernetes hợp lệ (vd. 500m, 256Mi, 1Gi, 2)", pytrace=False)
    number, exponent, suffix = match.groups()
    if exponent:
        return float(number + exponent)
    return float(number) * (BINARY.get(suffix) or DECIMAL.get(suffix) or 1)


def _run_id(template_docs: list[dict], names: list[str]) -> str:
    for doc in template_docs:
        template = str((doc.get("metadata") or {}).get("name", ""))
        if RUN not in template:
            continue
        pattern = re.escape(template).replace(re.escape(RUN), "([0-9a-f]{8})")
        for name in names:
            match = re.fullmatch(pattern, name.split("/", 1)[1])
            if match:
                return match.group(1)
    pytest.fail(f"Không suy ra được run id từ {names}", pytrace=False)


@contextmanager
def applied(docs: list[dict], namespace: str) -> Iterator[str]:
    """Apply tài nguyên cluster-scoped qua `mlopskit.cluster_scoped`, rồi phần namespaced vào `namespace`.

    `__RUN__` ở cả hai phần được thay bằng cùng một run id (LocalQueue trỏ đúng ClusterQueue của lần chạy này). Trả run
    id; ra khỏi khối thì cluster-scoped bị xoá (namespace do `k8s_namespace` của test xoá).
    """
    cluster = [d for d in docs if d.get("kind") in CLUSTER_KINDS]
    local = [d for d in docs if d.get("kind") not in CLUSTER_KINDS]
    if not cluster:
        pytest.fail("Manifest không có tài nguyên cluster-scoped nào", pytrace=False)
    with mlopskit.cluster_scoped(dump(cluster)) as names:
        run = _run_id(cluster, names)
        if local:
            mlopskit.apply_manifest(dump(local).replace(RUN, run), namespace)
        yield run


def get_json(*args: str, namespace: str | None = None) -> dict:
    result = mlopskit.kubectl("get", *args, "-o", "json", namespace=namespace)
    if result.returncode != 0:
        pytest.fail(f"kubectl get {' '.join(args)} lỗi: {result.stderr[-500:]}", pytrace=False)
    return json.loads(result.stdout)


def condition(obj: dict, kind: str) -> dict | None:
    for item in (obj.get("status") or {}).get("conditions") or []:
        if item.get("type") == kind:
            return item
    return None


def is_true(obj: dict | None, kind: str) -> bool:
    found = condition(obj or {}, kind)
    return bool(found and found.get("status") == "True")


def workloads(namespace: str) -> dict[str, dict]:
    """Workload Kueue trong namespace, theo tên Job sở hữu."""
    found = {}
    for item in get_json("workloads.kueue.x-k8s.io", namespace=namespace)["items"]:
        for owner in item["metadata"].get("ownerReferences") or []:
            if owner.get("kind") == "Job":
                found[owner["name"]] = item
    return found


def wait_workload(namespace: str, job: str, predicate, timeout: float, what: str, details: bool = True) -> dict:
    """Chờ Workload của `job` thoả `predicate`; quá hạn thì fail kèm `what` (và các condition hiện có nếu `details`)."""
    deadline = time.monotonic() + timeout
    current = None
    while time.monotonic() < deadline:
        current = workloads(namespace).get(job)
        if current is not None and predicate(current):
            return current
        time.sleep(1)
    if not details:
        pytest.fail(f"Job {job}: {what} sau {timeout:.0f} giây", pytrace=False)
    states = [(c.get("type"), c.get("status"), c.get("reason")) for c in ((current or {}).get("status") or {}).get("conditions") or []]
    pytest.fail(f"Job {job}: {what} sau {timeout:.0f} giây (condition của Workload: {states or 'chưa có Workload'})",
                pytrace=False)


def admitted(workload: dict) -> bool:
    return is_true(workload, "Admitted")


def job_manifest(name: str, queue: str | None, resources: dict, seconds: float, *, parallelism: int = 1,
                 priority_class: str | None = None) -> dict:
    """Job busybox ngủ `seconds` giây, mỗi pod xin `resources` (requests = limits), gắn nhãn hàng đợi Kueue nếu có."""
    labels = {"kueue.x-k8s.io/queue-name": queue} if queue else {}
    if priority_class:
        labels["kueue.x-k8s.io/priority-class"] = priority_class
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": name, "labels": labels},
        "spec": {
            "parallelism": parallelism,
            "completions": parallelism,
            "backoffLimit": 0,
            "template": {
                "spec": {
                    "restartPolicy": "Never",
                    "terminationGracePeriodSeconds": 1,
                    "automountServiceAccountToken": False,
                    "containers": [{
                        "name": "main",
                        "image": JOB_IMAGE,
                        "imagePullPolicy": "IfNotPresent",
                        "command": ["sh", "-c", f"sleep {seconds}"],
                        "resources": {"requests": dict(resources), "limits": dict(resources)},
                    }],
                },
            },
        },
    }


def pods(namespace: str, selector: str | None = None) -> list[dict]:
    args = ["pods"] + (["-l", selector] if selector else [])
    return get_json(*args, namespace=namespace)["items"]


def replicas(namespace: str, deployment: str) -> int:
    spec = get_json("deployment", deployment, namespace=namespace).get("spec") or {}
    return int(spec.get("replicas") or 0)


def wait_until(predicate, timeout: float, what: str, interval: float = 2) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            pytest.fail(f"{what} sau {timeout:.0f} giây", pytrace=False)
        time.sleep(interval)


def ready_endpoints(namespace: str, service: str) -> int:
    result = mlopskit.kubectl("get", "endpointslices", "-l", f"kubernetes.io/service-name={service}", "-o", "json",
                              namespace=namespace)
    if result.returncode != 0:
        return 0
    return sum(1 for s in json.loads(result.stdout)["items"] for e in s.get("endpoints") or []
               if (e.get("conditions") or {}).get("ready"))


def node_port_service(name: str, selector: dict, port: int) -> dict:
    """Service NodePort (cổng node do API server tự cấp) để client trong mạng Docker `kind` gọi tới mọi pod."""
    return {"apiVersion": "v1", "kind": "Service", "metadata": {"name": name},
            "spec": {"type": "NodePort", "selector": selector, "ports": [{"port": port, "targetPort": port}]}}


def node_url(namespace: str, service: str) -> str:
    """URL `http://<node>:<nodePort>` của Service NodePort, dùng được từ container trong mạng Docker `kind`."""
    spec = get_json("service", service, namespace=namespace)["spec"]
    return f"http://{node_name()}:{spec['ports'][0]['nodePort']}"


def call(port: int, path: str, payload: dict | None = None) -> dict:
    url = f"http://127.0.0.1:{port}{path}"
    response = httpx.post(url, json=payload, timeout=10) if payload is not None else httpx.get(url, timeout=10)
    assert response.status_code == 200, f"{path} trả {response.status_code}: {response.text[:300]}"
    return response.json()


def node_name() -> str:
    result = mlopskit.kubectl("get", "nodes", "-o", "jsonpath={.items[0].metadata.name}")
    if result.returncode != 0 or not result.stdout.strip():
        pytest.fail(f"Không lấy được tên node: {result.stderr[-300:]}", pytrace=False)
    return result.stdout.strip()


def k6(script: Path, target: str, timeout: int = 240) -> dict:
    """Chạy k6 trong mạng Docker `kind` (thấy node qua tên container); trả summary JSON của `--summary-export`."""
    result = mlopskit.k6_run(script, {"TARGET": target}, network="kind", timeout=timeout)
    if not result.stdout:
        pytest.fail(f"k6 không xuất summary (rc={result.returncode}):\n{result.stderr[-2500:]}", pytrace=False)
    return json.loads(result.stdout)
