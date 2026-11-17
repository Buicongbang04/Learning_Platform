import json
import socket
import time

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
ROLLOUTS = ("statefulset/postgres", "deployment/redis", "deployment/api", "deployment/worker")
PASSWORD = "olist-k8s-lab"
FORWARD = r"""
kubectl port-forward svc/api "$PORT:8000" >"$HOME/port-forward.log" 2>&1 &
pid=$!
trap 'kill $pid 2>/dev/null' EXIT
code=000
for i in $(seq 1 100); do
  code=$(curl -s -o "$HOME/body" -w '%{http_code}' -X "$METHOD" "http://127.0.0.1:$PORT$URL_PATH") || code=000
  [ "$code" != 000 ] && break
  sleep 0.2
done
echo "$code"
cat "$HOME/body" 2>/dev/null
"""


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def through_port_forward(lab, method: str, path: str) -> tuple[str, str]:
    result = lab.run(["bash", "-c", FORWARD], env={"PORT": str(free_port()), "METHOD": method, "URL_PATH": path}, timeout=60)
    lines = result.stdout.splitlines()
    return (lines[0] if lines else "000"), "\n".join(lines[1:])


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def container(lab, deployment: str, name: str) -> dict:
    found = get_json(lab, "deployment", deployment)
    assert found, f"Không có Deployment {deployment}"
    containers = {c["name"]: c for c in found["spec"]["template"]["spec"]["containers"]}
    assert name in containers, f"Deployment {deployment} không có container {name}"
    return containers[name]


@pytest.fixture(scope="module")
def stack():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab() as lab:
        applied = lab.apply_learner(ex.path("k8s"), check=False)
        rollouts = {}
        if applied.returncode == 0:
            for target in ROLLOUTS:
                rollouts[target] = lab.kubectl("rollout", "status", target, "--timeout=180s", check=False)
        yield lab, applied, rollouts


def test_manifests_apply_and_roll_out(stack):
    lab, applied, rollouts = stack
    assert applied.returncode == 0, applied.stderr
    for target in ROLLOUTS:
        result = rollouts[target]
        assert result.returncode == 0, f"{target} chưa rollout xong: {result.stdout[-400:]}{result.stderr[-400:]}"


def test_postgres_statefulset_has_headless_service_and_pvc(stack):
    lab, _, _ = stack
    sts = get_json(lab, "statefulset", "postgres")
    assert sts, "Postgres phải là StatefulSet tên postgres"
    assert sts["spec"].get("serviceName") == "postgres", "StatefulSet cần serviceName trỏ Service headless postgres"
    service = get_json(lab, "service", "postgres")
    assert service and service["spec"].get("clusterIP") == "None", "Service postgres phải headless (clusterIP: None)"
    templates = sts["spec"].get("volumeClaimTemplates") or []
    assert templates, "StatefulSet cần volumeClaimTemplates để dữ liệu sống qua lần pod bị tạo lại"
    claim = f"{templates[0]['metadata']['name']}-postgres-0"
    pvc = get_json(lab, "pvc", claim)
    assert pvc and pvc["status"].get("phase") == "Bound", f"PVC {claim} chưa Bound"
    assert pvc["spec"].get("storageClassName") == "standard", "PVC dùng StorageClass standard (local-path) có sẵn của kind"


def test_api_probes(stack):
    lab, _, _ = stack
    api = container(lab, "api", "api")
    readiness = (api.get("readinessProbe") or {}).get("httpGet") or {}
    liveness = (api.get("livenessProbe") or {}).get("httpGet") or {}
    assert readiness.get("path") == "/readyz", "readinessProbe của api gọi /readyz (kiểm DB và Redis)"
    assert liveness.get("path") == "/healthz", "livenessProbe của api gọi /healthz, không phụ thuộc DB hay Redis"


def test_resources_give_burstable_or_guaranteed(stack):
    lab, _, _ = stack
    for name in ("api", "worker"):
        spec = container(lab, name, name)
        resources = spec.get("resources") or {}
        assert (resources.get("requests") or {}).get("memory"), f"{name}: thiếu requests.memory"
        assert (resources.get("limits") or {}).get("memory"), f"{name}: thiếu limits.memory"
        pods = get_json(lab, "pods", "-l", f"app.kubernetes.io/name={name}") or {"items": []}
        assert pods["items"], f"Không thấy pod nhãn app.kubernetes.io/name={name}"
        assert all(p["status"].get("qosClass") in ("Burstable", "Guaranteed") for p in pods["items"]), name


def test_credentials_come_from_secret(stack):
    lab, _, _ = stack
    secret = get_json(lab, "secret", "olist-db")
    assert secret, "Cần Secret olist-db"
    for kind, name in (("deployment", "api"), ("deployment", "worker"), ("statefulset", "postgres")):
        found = get_json(lab, kind, name)
        assert found, f"Không có {kind} {name}"
        text = json.dumps(found["spec"]["template"])
        assert PASSWORD not in text, f"{kind} {name}: mật khẩu nằm thẳng trong pod spec; lấy từ Secret olist-db"
        assert "olist-db" in text, f"{kind} {name}: chưa tham chiếu Secret olist-db"


def test_readyz_through_port_forward(stack):
    lab, _, _ = stack
    code, body = through_port_forward(lab, "GET", "/readyz")
    assert code == "200", f"/readyz qua kubectl port-forward svc/api trả {code}: {body[:300]}"
    assert json.loads(body) == {"db": "ok", "redis": "ok"}


def test_service_has_two_ready_endpoints(stack):
    lab, _, _ = stack
    slices = get_json(lab, "endpointslices", "-l", "kubernetes.io/service-name=api") or {"items": []}
    ready = [e for s in slices["items"] for e in s.get("endpoints") or [] if (e.get("conditions") or {}).get("ready")]
    assert len(ready) >= 2, f"Service api cần ít nhất 2 endpoint sẵn sàng, đang có {len(ready)}"


def test_worker_processes_job(stack):
    lab, _, _ = stack
    code, body = through_port_forward(lab, "POST", "/jobs/recompute")
    assert code == "202", f"POST /jobs/recompute trả {code}: {body[:300]}"
    deadline = time.monotonic() + 60
    logs = ""
    while time.monotonic() < deadline:
        logs = lab.kubectl("logs", "deployment/worker", "--tail=200", check=False).stdout
        if '"job done"' in logs:
            return
        time.sleep(2)
    pytest.fail(f"Worker chưa xử lý job sau 60 giây. Log cuối:\n{logs[-800:]}")


RESOLVE = ("import json, socket, sys; "
           "print(json.dumps({n: sorted({a[4][0] for a in socket.getaddrinfo(n, None, socket.AF_INET)}) for n in sys.argv[1:]}))")


def test_cluster_dns_names(stack):
    lab, _, _ = stack
    names = [f"redis.{lab.namespace}.svc.cluster.local", f"postgres-0.postgres.{lab.namespace}.svc.cluster.local"]
    result = lab.kubectl("exec", "deployment/worker", "--", "python", "-c", RESOLVE, *names, check=False)
    assert result.returncode == 0, f"Pod worker không phân giải được {names}: {result.stderr[-400:]}"
    resolved = json.loads(result.stdout)
    redis = get_json(lab, "service", "redis")
    assert resolved[names[0]] == [redis["spec"]["clusterIP"]], "Tên Service redis phải trỏ ClusterIP của nó"
    pod = get_json(lab, "pod", "postgres-0")
    assert resolved[names[1]] == [pod["status"]["podIP"]], "postgres-0.postgres phải trỏ IP của pod postgres-0 (Service headless)"
