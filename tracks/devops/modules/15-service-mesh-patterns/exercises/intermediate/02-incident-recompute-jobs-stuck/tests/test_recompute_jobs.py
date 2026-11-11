import json
import subprocess
import time

import pytest
import yaml

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
PLATFORM = ex.fixtures / "platform.yaml"
CLIENTS = ex.fixtures / "clients.yaml"
INCIDENT = ex.fixtures / "incident" / "worker.yaml"
PLATFORM_KINDS = {"Server", "AuthorizationPolicy", "MeshTLSAuthentication", "HTTPRoute"}
PLATFORM_NAMES = {"api", "redis", "postgres", "olist-db", "intruder", "legacy-report"}
FOREIGN_ACCOUNTS = {"api", "redis", "postgres", "intruder"}
WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob", "Pod"}
IDENTITY_MESSAGE = "worker không được chạy bằng ServiceAccount/danh tính của team platform"
PROBE = """
import json, socket, sys, urllib.request
out = {}
for target in sys.argv[1:]:
    kind, _, rest = target.partition(":")
    try:
        if kind == "redis":
            conn = socket.create_connection(("redis", 6379), timeout=3)
            conn.settimeout(3)
            conn.sendall(b"PING\\r\\n")
            answer = conn.recv(64)
            conn.close()
            out[target] = "ok" if answer.startswith(b"+PONG") else "chan " + repr(answer[:20])
        elif kind == "enqueue":
            request = urllib.request.Request("http://127.0.0.1:8000/jobs/recompute", method="POST", data=b"")
            with urllib.request.urlopen(request, timeout=5) as answer:
                out[target] = "ok %d" % answer.status
        elif kind == "processed":
            with urllib.request.urlopen("http://127.0.0.1:9101/metrics", timeout=5) as answer:
                text = answer.read().decode()
            values = [float(line.split()[-1]) for line in text.splitlines() if line.startswith("jobs_processed_total ")]
            out[target] = "ok %d" % int(values[0]) if values else "thieu"
    except Exception as error:
        out[target] = "chan " + type(error).__name__ + " " + str(error)[:60]
print(json.dumps(out))
"""


def pod_spec(document: dict) -> dict:
    spec = document.get("spec") or {}
    if document.get("kind") == "Pod":
        return spec
    if document.get("kind") == "CronJob":
        spec = ((spec.get("jobTemplate") or {}).get("spec")) or {}
    return ((spec.get("template") or {}).get("spec")) or {}


def borrowed_accounts(documents) -> list[str]:
    found = []
    for document in documents:
        if not isinstance(document, dict) or document.get("kind") not in WORKLOADS:
            continue
        spec = pod_spec(document)
        account = spec.get("serviceAccountName") or spec.get("serviceAccount") or "default"
        if account in FOREIGN_ACCOUNTS:
            found.append(f"{document['kind']}/{(document.get('metadata') or {}).get('name')}")
    return found


def probe(lab, deployment: str, container: str, target: str) -> str:
    result = lab.kubectl("exec", f"deployment/{deployment}", "-c", container, "--", "python", "-c", PROBE, target,
                         check=False, timeout=120)
    if result.returncode != 0:
        return "exec-loi " + result.stderr[-200:]
    return json.loads(result.stdout)[target]


def processed(lab) -> int:
    answer = probe(lab, "worker", "worker", "processed:")
    return int(answer.split()[1]) if answer.startswith("ok") else -1


def queue_length(lab) -> int:
    result = lab.kubectl("exec", "deployment/redis", "-c", "redis", "--", "redis-cli", "llen", "olist:jobs", check=False, timeout=60)
    return int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip().isdigit() else -1


def wait_until(check, timeout: float, interval: float = 2) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(interval)
    return bool(check())


def enqueue(lab, count: int) -> list[str]:
    return [probe(lab, "api", "api", "enqueue:") for _ in range(count)]


def deploy_worker(lab, path) -> subprocess.CompletedProcess:
    try:
        applied = lab.apply_learner(path, check=False)
    except pytest.fail.Exception as error:
        return subprocess.CompletedProcess([], 1, "", str(error))
    if applied.returncode == 0:
        lab.kubectl("rollout", "status", "deployment/worker", "--timeout=180s", check=False, timeout=200)
        wait_until(lambda: processed(lab) >= 0, 60)
    return applied


@pytest.fixture(scope="module")
def shop():
    ex.require_linkerd()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab(mesh=True) as lab:
        lab.apply_learner(PLATFORM)
        lab.apply_learner(CLIENTS)
        for name in ("postgres", "redis", "api", "intruder", "legacy-report"):
            lab.kubectl("rollout", "status", f"deployment/{name}", "--timeout=180s", timeout=200)
        assert wait_until(lambda: probe(lab, "api", "api", "enqueue:") == "ok 202", 60), "api chưa nhận job trước khi thử"
        lab.kubectl("exec", "deployment/redis", "-c", "redis", "--", "redis-cli", "del", "olist:jobs", timeout=60)
        incident = deploy_worker(lab, INCIDENT)
        denied_before = lab.mesh_status("deployment/redis")["denied"]
        enqueue(lab, 2)
        time.sleep(25)
        regression = {"applied": incident.returncode, "processed": processed(lab), "queue": queue_length(lab),
                      "denied": lab.mesh_status("deployment/redis")["denied"] - denied_before}
        lab.kubectl("delete", "-f", str(INCIDENT), "--ignore-not-found", "--wait=true", timeout=120)
        lab.kubectl("exec", "deployment/redis", "-c", "redis", "--", "redis-cli", "del", "olist:jobs", timeout=60)
        applied = deploy_worker(lab, ex.path("k8s"))
        yield lab, applied, regression


def test_incident_manifest_reproduces_symptom(shop):
    _, _, regression = shop
    assert regression["applied"] == 0, "Manifest sự cố phải apply được"
    assert regression["processed"] == 0 and regression["queue"] == 2, f"Bản sự cố: job phải nằm lại trong hàng đợi ({regression})"
    assert regression["denied"] > 0, f"Bản sự cố: Redis phải từ chối kết nối của worker ({regression})"


def test_worker_manifest_applies(shop):
    lab, applied, _ = shop
    assert applied.returncode == 0, applied.stderr[-1500:]
    documents = lab.manifests(ex.path("k8s"))
    touched = sorted({f"{d.get('kind')}/{(d.get('metadata') or {}).get('name')}" for d in documents
                      if d.get("kind") in PLATFORM_KINDS or (d.get("metadata") or {}).get("name") in PLATFORM_NAMES})
    assert not touched, f"Chỉ sửa manifest của worker; không tạo hay đổi object của team platform: {touched}"


def test_recompute_jobs_complete(shop):
    lab, _, _ = shop
    before = processed(lab)
    assert before >= 0, "Không đọc được jobs_processed_total của worker ở cổng 9101"
    queued = enqueue(lab, 3)
    assert queued == ["ok 202"] * 3, f"POST /jobs/recompute: {queued}"
    assert wait_until(lambda: processed(lab) >= before + 3, 90), \
        f"Worker chưa xử lý xong 3 job sau 90 giây (jobs_processed_total {before} -> {processed(lab)})"
    assert wait_until(lambda: queue_length(lab) == 0, 30), f"Hàng đợi olist:jobs còn {queue_length(lab)} job"


def test_worker_stays_in_mesh(shop):
    lab, _, _ = shop
    status = lab.mesh_status("deployment/worker")
    assert status["pods"] and status["injected"] and status["mtls"], f"worker phải chạy trong mesh như các service khác: {status}"


def test_worker_uses_its_own_identity(shop):
    lab, _, _ = shop
    assert not borrowed_accounts(lab.manifests(ex.path("k8s"))), IDENTITY_MESSAGE
    identity = lab.mesh_status("deployment/worker")["identity"] or ""
    assert identity, "worker chưa có danh tính mTLS"
    assert identity.split(".", 1)[0] not in FOREIGN_ACCOUNTS, IDENTITY_MESSAGE


def test_identity_check_catches_borrowed_account():
    solution = ex.dir.parents[2] / "solutions" / ex.dir.parent.name / ex.dir.name / "k8s" / "worker.yaml"
    starter = ex.dir / "starter" / "k8s" / "worker.yaml"
    documents = list(yaml.safe_load_all(solution.read_text(encoding="utf-8")))
    assert not borrowed_accounts(documents)
    assert not borrowed_accounts(list(yaml.safe_load_all(starter.read_text(encoding="utf-8"))))
    for document in documents:
        if document.get("kind") == "Deployment":
            document["spec"]["template"]["spec"]["serviceAccountName"] = "api"
    assert borrowed_accounts(documents) == ["Deployment/worker"]


def test_redis_still_refuses_strangers(shop):
    lab, _, _ = shop
    intruder = probe(lab, "intruder", "shell", "redis:")
    legacy = probe(lab, "legacy-report", "shell", "redis:")
    assert intruder != "ok" and legacy != "ok", f"Redis chỉ phục vụ Olist Shop: intruder {intruder!r}, legacy-report {legacy!r}"
    assert not intruder.startswith("exec-loi") and not legacy.startswith("exec-loi"), (intruder, legacy)
