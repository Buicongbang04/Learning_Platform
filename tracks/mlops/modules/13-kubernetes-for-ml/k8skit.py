"""Tiện ích chung cho test module 13: image service ETA dùng chung, đọc/sửa manifest, gọi service, đếm restart.

Mọi lệnh tới Docker và cluster đi qua `mlopskit` (context `kind-mlops`, namespace tạm `mlops-ex-*`).
"""

import importlib.util
import json
import re
import time
from pathlib import Path

import httpx
import mlopskit
import pytest
import yaml

LAB = Path(__file__).resolve().parent / "lab" / "service"
IMAGE = "eta-serve:dev"
_CACHE: dict[str, object] = {}


def eta_image() -> str:
    """Build `lab/service` một lần mỗi phiên pytest, nạp vào node kind, trả tag dùng trong manifest."""
    mlopskit.require_kind()
    if "image" not in _CACHE:
        with mlopskit.built_image(LAB) as tag:
            mlopskit.kind_load(tag)
        _CACHE["image"] = tag
    return _CACHE["image"]


def etaml():
    if "etaml" not in _CACHE:
        spec = importlib.util.spec_from_file_location("k8skit_etaml", LAB / "app" / "etaml.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CACHE["etaml"] = module
    return _CACHE["etaml"]


ROWS = [[3.2, 8, 1], [12.5, 14, 2], [20.0, 18, 4]]


def expected_predictions(version: str, rows: list[list[float]] = ROWS) -> list[float]:
    model = etaml().release_model(version)
    return [round(float(v), 4) for v in model.predict(rows)]


def load_docs(path: Path) -> list[dict]:
    try:
        return [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} không phải YAML hợp lệ: {error}", pytrace=False)


def find(docs: list[dict], kind: str, name: str | None = None) -> dict:
    for doc in docs:
        if doc.get("kind") == kind and (name is None or doc.get("metadata", {}).get("name") == name):
            return doc
    pytest.fail(f"Không thấy {kind}{' ' + name if name else ''} trong manifest", pytrace=False)


def containers(doc: dict) -> list[dict]:
    kind = doc.get("kind")
    if kind == "Deployment":
        return doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers") or []
    if kind == "InferenceService":
        return doc.get("spec", {}).get("predictor", {}).get("containers") or []
    if kind == "Workflow":
        return [t[key] for t in doc.get("spec", {}).get("templates") or [] for key in ("script", "container") if key in t]
    return []


def with_image(docs: list[dict], image: str) -> list[dict]:
    """Thay mọi `image: eta-serve:dev` bằng image vừa build; image khác giữ nguyên."""
    for doc in docs:
        for container in containers(doc):
            if container.get("image") == IMAGE:
                container["image"] = image
    return docs


def set_env(container: dict, name: str, value: str) -> None:
    env = [e for e in container.get("env") or [] if e.get("name") != name]
    container["env"] = env + [{"name": name, "value": value}]


def dump(docs: list[dict]) -> str:
    return yaml.safe_dump_all(docs, sort_keys=False)


QUANTITY = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))(?:([eE][+-]?\d+)|(Ki|Mi|Gi|Ti|Pi|Ei|n|u|m|k|M|G|T|P|E))?$")
BINARY = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "Pi": 2**50, "Ei": 2**60}
DECIMAL = {"n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15, "E": 1e18}


def quantity(value) -> float:
    """Đổi quantity K8s (`500m`, `256Mi`, `1Gi`, `2`, `1.5e3`, `2P`...) ra số (CPU theo nhân, bộ nhớ theo byte)."""
    match = QUANTITY.match(str(value).strip())
    if not match:
        pytest.fail(f"{value!r} không phải quantity Kubernetes hợp lệ (vd. 500m, 256Mi, 1Gi, 2)", pytrace=False)
    number, exponent, suffix = match.groups()
    if exponent:
        return float(number + exponent)
    return float(number) * (BINARY.get(suffix) or DECIMAL.get(suffix) or 1)


def pods(namespace: str, selector: str) -> list[dict]:
    result = mlopskit.kubectl("get", "pods", "-l", selector, "-o", "json", namespace=namespace)
    if result.returncode != 0:
        pytest.fail(f"kubectl get pods lỗi: {result.stderr}", pytrace=False)
    return json.loads(result.stdout)["items"]


def restarts(namespace: str, selector: str) -> int:
    return sum(s.get("restartCount", 0) for p in pods(namespace, selector) for s in p["status"].get("containerStatuses") or [])


def wait_restarts(namespace: str, selector: str, at_least: int, timeout: int) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        count = restarts(namespace, selector)
        if count >= at_least:
            return count
        time.sleep(3)
    return restarts(namespace, selector)


def wait_available(namespace: str, deployment: str, selector: str, timeout: int, max_restarts: int = 2) -> None:
    """Chờ Deployment có condition Available; dừng sớm (fail) khi pod đã khởi động lại `max_restarts` lần."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        conditions = get_json("deployment", deployment, namespace).get("status", {}).get("conditions") or []
        if any(c["type"] == "Available" and c["status"] == "True" for c in conditions):
            return
        count = restarts(namespace, selector)
        if count >= max_restarts:
            pytest.fail(f"Pod của {deployment} đã khởi động lại {count} lần mà chưa sẵn sàng", pytrace=False)
        time.sleep(3)
    mlopskit.wait_for("deployment", deployment, "Available", namespace, 5)


def get_json(kind: str, name: str, namespace: str) -> dict:
    result = mlopskit.kubectl("get", kind, name, "-o", "json", namespace=namespace)
    if result.returncode != 0:
        pytest.fail(f"kubectl get {kind}/{name} lỗi: {result.stderr}", pytrace=False)
    return json.loads(result.stdout)


def ready_endpoints(namespace: str, service: str) -> int:
    result = mlopskit.kubectl("get", "endpointslices", "-l", f"kubernetes.io/service-name={service}", "-o", "json",
                              namespace=namespace)
    if result.returncode != 0:
        return 0
    return sum(1 for s in json.loads(result.stdout)["items"] for e in s.get("endpoints") or []
               if (e.get("conditions") or {}).get("ready"))


def wait_endpoints(namespace: str, service: str, count: int, timeout: int) -> None:
    """Chờ Service có đúng `count` endpoint Ready (pod đã vào bảng cân bằng tải); quá hạn thì fail."""
    deadline = time.monotonic() + timeout
    while (found := ready_endpoints(namespace, service)) != count:
        if time.monotonic() > deadline:
            pytest.fail(f"Service {service} có {found} endpoint Ready sau {timeout} giây, cần {count}", pytrace=False)
        time.sleep(2)
    time.sleep(3)


def call(port: int, path: str, payload: dict | None = None) -> dict:
    url = f"http://127.0.0.1:{port}{path}"
    response = httpx.post(url, json=payload, timeout=10) if payload is not None else httpx.get(url, timeout=10)
    assert response.status_code == 200, f"{path} trả {response.status_code}: {response.text[:300]}"
    return response.json()


CLIENT = """
import collections, json, urllib.request
counts, errors = collections.Counter(), []
for _ in range({n}):
    request = urllib.request.Request("{url}", data=json.dumps({{"instances": [[3.2, 8, 1]]}}).encode(),
                                     headers={{"Content-Type": "application/json", "Connection": "close"}})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            counts[json.load(response)["model_version"]] += 1
    except Exception as error:
        counts["error"] += 1
        if len(errors) < 3:
            errors.append(f"{{type(error).__name__}}: {{error}}")
print(json.dumps({{"counts": counts, "errors": errors}}))
"""

HARDENED_POD = {
    "automountServiceAccountToken": False,
    "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "seccompProfile": {"type": "RuntimeDefault"}},
}
HARDENED_CONTAINER = {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]}}


def in_cluster_versions(namespace: str, url: str, n: int, timeout: int = 180) -> tuple[dict[str, int], list[str]]:
    """Gửi `n` request từ một pod trong namespace tới `url` (DNS Service); trả (số request theo `model_version`, mẫu lỗi).

    `port_forward` chỉ nối tới một pod, nên tỉ lệ chia traffic giữa nhiều pod phải đo từ trong cluster.
    """
    name = f"client-{int(time.time() * 1000) % 10**8}"
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": name},
        "spec": {
            **HARDENED_POD,
            "restartPolicy": "Never",
            "containers": [{
                "name": "client",
                "image": eta_image(),
                "command": ["python", "-c", CLIENT.format(n=n, url=url)],
                "securityContext": HARDENED_CONTAINER,
                "resources": {"requests": {"cpu": "50m", "memory": "64Mi"}, "limits": {"cpu": "1", "memory": "256Mi"}},
            }],
        },
    }
    mlopskit.apply_manifest(dump([pod]), namespace)
    try:
        mlopskit.wait_for("pod", name, "jsonpath={.status.phase}=Succeeded", namespace, timeout, fail_on=("Failed",))
    except pytest.fail.Exception as error:
        logs = mlopskit.kubectl("logs", name, "--tail=40", namespace=namespace)
        described = mlopskit.kubectl("describe", "pod", name, namespace=namespace)
        pytest.fail(f"Pod client {name} không chạy xong:\n--- logs\n{(logs.stdout + logs.stderr)[-2000:]}\n"
                    f"--- describe\n{described.stdout[-2500:]}\n--- wait_for\n{str(error)[-1500:]}", pytrace=False)
    logs = mlopskit.kubectl("logs", name, namespace=namespace)
    mlopskit.kubectl("delete", "pod", name, "--wait=false", namespace=namespace)
    lines = logs.stdout.strip().splitlines()
    if logs.returncode != 0 or not lines:
        pytest.fail(f"Không đọc được kết quả của pod client {name} (rc={logs.returncode}): {logs.stderr[-500:]}",
                    pytrace=False)
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError:
        pytest.fail(f"Pod client {name} in kết quả không phải JSON: {lines[-1][:300]}", pytrace=False)
    return dict(result["counts"]), result["errors"]
