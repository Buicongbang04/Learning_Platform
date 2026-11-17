import json
import subprocess
import tarfile
import time
from pathlib import Path

import pytest
import yaml

import fdekit
from testkit import ROOT, Exercise

ex = Exercise(__file__)
BUNDLE = ROOT / "tracks" / "fde" / "product" / "dist" / "quillo-1.0.0.tar"
BUILD = "nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist"
CHART_MEMBER = "quillo-1.0.0/chart/quillo-1.0.0.tgz"
WORK = "/home/fde/values-check"
K8S_WAIT = 180
REGISTRY = "10.0.2.101:5000/vendors/quillo"
IMAGES = {f"{REGISTRY}/quillo-api:1.0.0", f"{REGISTRY}/pgvector/pgvector:0.8.6-pg16",
          f"{REGISTRY}/ggml-org/llama.cpp:server-b11718", f"{REGISTRY}/quillo-models:1.0.0"}
CPU_BUDGET_M = 1000
MINIMUM = {
    "api": {"requests.cpu": 100, "requests.memory": 256, "limits.memory": 512},
    "worker": {"requests.cpu": 50, "requests.memory": 128, "limits.memory": 384},
    "db": {"requests.cpu": 100, "requests.memory": 256, "limits.memory": 512},
    "llm": {"requests.cpu": 250, "requests.memory": 1024, "limits.memory": 1536},
    "embed": {"requests.cpu": 100, "requests.memory": 384, "limits.memory": 512},
}
AGENT = """apiVersion: v1
kind: Pod
metadata:
  name: it-backup-agent
  labels: {app.kubernetes.io/name: it-backup-agent}
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 65534
    runAsGroup: 65534
    seccompProfile: {type: RuntimeDefault}
  containers:
    - name: agent
      image: rancher/mirrored-library-busybox:1.37.0
      imagePullPolicy: IfNotPresent
      command: [sleep, "86400"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities: {drop: [ALL]}
      resources:
        requests: {cpu: 200m, memory: 1Gi}
        limits: {cpu: 500m, memory: 1Gi}
"""


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def wait_api(m) -> None:
    deadline = time.monotonic() + K8S_WAIT
    while time.monotonic() < deadline:
        if sh(m, "kubectl --request-timeout=5s get --raw=/readyz", timeout=30).stdout.strip() == "ok":
            return
        time.sleep(2)
    pytest.fail(f"API server k3s chưa sẵn sàng sau {K8S_WAIT} s")


def cpu_m(value) -> float:
    text = str(value)
    return float(text[:-1]) if text.endswith("m") else float(text) * 1000


def mem_mi(value) -> float:
    text = str(value)
    units = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024, "k": 1e3 / 2**20, "M": 1e6 / 2**20,
             "G": 1e9 / 2**20}
    for suffix, factor in units.items():
        if text.endswith(suffix):
            return float(text[: -len(suffix)]) * factor
    return float(text) / 2**20


def container_need(container: dict) -> dict:
    res = container.get("resources") or {}
    req, lim = res.get("requests") or {}, res.get("limits") or {}
    return {"requests.cpu": cpu_m(req["cpu"]) if "cpu" in req else 0.0,
            "requests.memory": mem_mi(req["memory"]) if "memory" in req else 0.0,
            "limits.memory": mem_mi(lim["memory"]) if "memory" in lim else 0.0}


def pod_need(spec: dict) -> dict:
    total = {key: 0.0 for key in ("requests.cpu", "requests.memory", "limits.memory")}
    for container in spec.get("containers", []):
        for key, value in container_need(container).items():
            total[key] += value
    for container in spec.get("initContainers", []) or []:
        for key, value in container_need(container).items():
            total[key] = max(total[key], value)
    return total


def workloads(docs: list[dict]) -> list[dict]:
    return [d for d in docs if d.get("kind") in ("Deployment", "StatefulSet")]


def component(doc: dict) -> str:
    return doc["spec"]["template"]["metadata"]["labels"].get("app.kubernetes.io/component", doc["metadata"]["name"])


def render(m) -> tuple[str, list[dict]]:
    run = sh(m, f"helm template quillo {WORK}/quillo-1.0.0.tgz -n quillo -f {WORK}/values.yaml > {WORK}/rendered.yaml")
    assert run.returncode == 0, f"helm template lỗi với values.yaml của bạn:\n{run.stderr[-2000:]}"
    text = sh(m, f"cat {WORK}/rendered.yaml").stdout
    return text, [d for d in yaml.safe_load_all(text) if d]


def check_images(docs: list[dict]) -> None:
    found = set()
    for doc in workloads(docs):
        spec = doc["spec"]["template"]["spec"]
        for container in [*spec.get("containers", []), *(spec.get("initContainers") or [])]:
            found.add(container["image"])
    assert found == IMAGES, f"Image trong manifest phải đúng {sorted(IMAGES)}, đang là {sorted(found)}"


def check_run_as_user(docs: list[dict]) -> None:
    for doc in workloads(docs):
        spec = doc["spec"]["template"]["spec"]
        pod_uid = (spec.get("securityContext") or {}).get("runAsUser")
        for container in [*spec.get("containers", []), *(spec.get("initContainers") or [])]:
            uid = (container.get("securityContext") or {}).get("runAsUser", pod_uid)
            assert isinstance(uid, int) and uid > 0, (
                f"{doc['metadata']['name']}/{container['name']}: cần runAsUser là số khác 0 (đang {uid!r})")


def check_dry_run(m) -> None:
    run = sh(m, f"kubectl apply --dry-run=server -n quillo -f {WORK}/rendered.yaml")
    assert run.returncode == 0, f"kubectl apply --dry-run=server bị từ chối:\n{run.stderr[-2500:]}"
    warnings = [line for line in run.stderr.splitlines() if line.startswith("Warning:")]
    assert not warnings, "kubectl apply --dry-run=server có cảnh báo (cluster sẽ từ chối pod tạo ra):\n" + "\n".join(
        warnings[:10])


def check_pods(m, tmp_path: Path, docs: list[dict]) -> None:
    pods = []
    for doc in workloads(docs):
        template = doc["spec"]["template"]
        spec = dict(template["spec"])
        claims = [{"name": c["metadata"]["name"],
                   "persistentVolumeClaim": {"claimName": f"{c['metadata']['name']}-{doc['metadata']['name']}-0"}}
                  for c in doc["spec"].get("volumeClaimTemplates", [])]
        if claims:
            spec["volumes"] = [*(spec.get("volumes") or []), *claims]
        pods.append({"apiVersion": "v1", "kind": "Pod",
                     "metadata": {"name": f"check-{doc['metadata']['name']}", "labels": template["metadata"]["labels"]},
                     "spec": spec})
    local = tmp_path / "pods.yaml"
    local.write_text(yaml.safe_dump_all(pods))
    m.put(local, f"{WORK}/pods.yaml")
    run = sh(m, f"kubectl create --dry-run=server -n quillo -f {WORK}/pods.yaml -o name")
    assert run.returncode == 0, f"Pod sinh từ manifest bị từ chối (kubectl create --dry-run=server):\n{run.stderr[-2500:]}"


def check_budget(m, docs: list[dict]) -> None:
    quota = json.loads(sh(m, "kubectl -n quillo get resourcequota quillo-quota -o json").stdout)
    hard, used = quota["status"]["hard"], quota["status"]["used"]
    total = {key: 0.0 for key in ("requests.cpu", "requests.memory", "limits.memory")}
    lines = []
    for doc in workloads(docs):
        name = component(doc)
        need = pod_need(doc["spec"]["template"]["spec"])
        floor = MINIMUM.get(name)
        if floor:
            low = {k: (need[k], v) for k, v in floor.items() if need[k] + 1e-6 < v}
            assert not low, f"{name}: dưới mức tối thiểu của vendor (đang, cần): {low}"
        replicas = int(doc["spec"].get("replicas", 1))
        strategy = (doc["spec"].get("strategy") or {}).get("type", "RollingUpdate")
        count = replicas + (1 if doc["kind"] == "Deployment" and strategy == "RollingUpdate" else 0)
        for key in total:
            total[key] += need[key] * count
        lines.append(f"{name}: {count} pod × {need}")
    detail = "\n".join(lines)
    cpu_used = cpu_m(used.get("requests.cpu", "0"))
    assert cpu_used + total["requests.cpu"] <= CPU_BUDGET_M + 1e-6, (
        f"requests.cpu của cả namespace sẽ là {cpu_used + total['requests.cpu']:.0f}m > {CPU_BUDGET_M}m\n{detail}")
    for key in ("requests.memory", "limits.memory"):
        room = mem_mi(hard[key]) - mem_mi(used.get(key, "0"))
        assert total[key] <= room + 1e-6, f"{key}: quillo cần {total[key]:.0f}Mi, quota còn {room:.0f}Mi\n{detail}"


def test_values_fit_lawfirm_prod(tmp_path):
    if not BUNDLE.is_file():
        pytest.skip(f"Chưa có {BUNDLE.relative_to(ROOT)}; dựng bằng: {BUILD}")
    with tarfile.open(BUNDLE) as bundle:
        (tmp_path / "quillo-1.0.0.tgz").write_bytes(bundle.extractfile(CHART_MEMBER).read())
    values = ex.path("values.yaml")
    with fdekit.vm("lawfirm-prod") as m:
        wait_api(m)
        assert sh(m, f"mkdir -p {WORK}").returncode == 0
        m.put(tmp_path / "quillo-1.0.0.tgz", f"{WORK}/quillo-1.0.0.tgz")
        m.put(values, f"{WORK}/values.yaml")
        (tmp_path / "agent.yaml").write_text(AGENT)
        m.put(tmp_path / "agent.yaml", f"{WORK}/agent.yaml")
        done = sh(m, f"kubectl -n quillo apply -f {WORK}/agent.yaml")
        assert done.returncode == 0, f"Test không tạo được pod it-backup-agent: {done.stderr}"

        text, docs = render(m)
        assert workloads(docs), "helm template không sinh Deployment/StatefulSet nào"
        check_images(docs)
        check_run_as_user(docs)
        check_dry_run(m)
        check_pods(m, tmp_path, docs)
        check_budget(m, docs)
