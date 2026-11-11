import json
import re
import subprocess
import time

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
DATA = ex.fixtures / "data.yaml"
CLIENTS = ex.fixtures / "clients.yaml"
IDENTITY = "{sa}.{ns}.serviceaccount.identity.linkerd.cluster.local"
PROBE = """
import json, socket, sys, urllib.request
out = {}
for target in sys.argv[1:]:
    kind, _, rest = target.partition(":")
    try:
        if kind == "redis":
            host, port = rest.rsplit(":", 1)
            conn = socket.create_connection((host, int(port)), timeout=3)
            conn.settimeout(3)
            conn.sendall(b"PING\\r\\n")
            answer = conn.recv(64)
            conn.close()
            out[target] = "ok" if answer.startswith(b"+PONG") else "chan " + repr(answer[:20])
        elif kind in ("get", "post"):
            request = urllib.request.Request("http://" + rest, method=kind.upper(), data=b"" if kind == "post" else None)
            with urllib.request.urlopen(request, timeout=5) as answer:
                out[target] = "ok %d %s" % (answer.status, answer.read().decode()[:120])
        elif kind == "metric":
            with urllib.request.urlopen("http://127.0.0.1:9101/metrics", timeout=5) as answer:
                text = answer.read().decode()
            values = [float(line.split()[-1]) for line in text.splitlines() if line.startswith(rest + " ")]
            out[target] = "ok %d" % int(values[0]) if values else "thieu"
    except urllib.error.HTTPError as error:
        out[target] = "http %d %s" % (error.code, error.read().decode()[:120])
    except Exception as error:
        out[target] = "chan " + type(error).__name__ + " " + str(error)[:60]
print(json.dumps(out))
"""


def probe(lab, deployment: str, container: str, *targets: str) -> dict:
    result = lab.kubectl("exec", f"deployment/{deployment}", "-c", container, "--", "python", "-c", PROBE, *targets,
                         check=False, timeout=120)
    assert result.returncode == 0, f"Không exec được vào {deployment}: {result.stderr[-400:]}"
    return json.loads(result.stdout)


def eventually(check, timeout: float, interval: float = 2):
    deadline = time.monotonic() + timeout
    value = check()
    while not value and time.monotonic() < deadline:
        time.sleep(interval)
        value = check()
    return value


def mesh_until(lab, workload: str, condition, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    status = lab.mesh_status(workload)
    while not condition(status) and time.monotonic() < deadline:
        time.sleep(2)
        status = lab.mesh_status(workload)
    return status


def processed(lab) -> int:
    answer = probe(lab, "worker", "worker", "metric:jobs_processed_total")["metric:jobs_processed_total"]
    return int(answer.split()[1]) if answer.startswith("ok") else -1


def rollout(lab, *names: str) -> None:
    for name in names:
        lab.kubectl("rollout", "status", f"deployment/{name}", "--timeout=180s", timeout=200)


@pytest.fixture(scope="module")
def shop():
    ex.require_linkerd()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab() as lab:
        lab.apply_learner(DATA)
        lab.apply_learner(CLIENTS)
        rollout(lab, "postgres", "redis", "storefront", "intruder", "legacy-report")
        control = {
            "intruder": eventually(lambda: probe(lab, "intruder", "shell", "redis:redis:6379")["redis:redis:6379"] == "ok", 40),
            "legacy": probe(lab, "legacy-report", "shell", "redis:redis:6379")["redis:redis:6379"] == "ok",
        }
        try:
            applied = lab.apply_learner(ex.path("k8s"), check=False)
        except pytest.fail.Exception as error:
            applied = subprocess.CompletedProcess([], 1, "", str(error))
        if applied.returncode == 0:
            for name in ("api", "worker"):
                lab.kubectl("rollout", "status", f"deployment/{name}", "--timeout=180s", check=False, timeout=200)
        yield lab, applied, control


def test_manifests_apply(shop):
    _, applied, control = shop
    assert applied.returncode == 0, applied.stderr[-1500:]
    assert control == {"intruder": True, "legacy": True}, \
        f"Đối chứng: trước khi áp manifest của bạn, mọi pod đều PING được Redis ({control})"


@pytest.mark.parametrize("name", ["api", "worker"])
def test_workload_meshed_with_own_identity(shop, name):
    lab, _, _ = shop
    status = mesh_until(lab, f"deployment/{name}", lambda s: s["pods"] and s["mtls"], 60)
    assert status["pods"], f"{name} không có pod Running"
    assert status["injected"], f"Pod của {name} chưa có proxy linkerd-proxy: {status['pods']}"
    assert status["mtls"], f"Proxy của {name} chưa nhận chứng chỉ mTLS từ linkerd-identity"
    expected = IDENTITY.format(sa=name, ns=lab.namespace)
    assert status["identity"] == expected, f"Danh tính mTLS của {name} là {status['identity']}, cần {expected}"


def test_api_ready_and_worker_processes_job(shop):
    lab, _, _ = shop
    target = "get:127.0.0.1:8000/readyz"
    answers = []
    eventually(lambda: answers.append(probe(lab, "api", "api", target)[target]) or answers[-1].startswith("ok 200"), 60)
    ready = answers[-1]
    assert ready.startswith("ok 200") and '"redis":"ok"' in ready and '"db":"ok"' in ready, f"/readyz của api: {ready}"
    counts = []
    eventually(lambda: counts.append(processed(lab)) or counts[-1] >= 0, 60)
    before = counts[-1]
    assert before >= 0, "Không đọc được jobs_processed_total của worker ở cổng 9101"
    queued = probe(lab, "api", "api", "post:127.0.0.1:8000/jobs/recompute")["post:127.0.0.1:8000/jobs/recompute"]
    assert queued.startswith("ok 202"), f"POST /jobs/recompute: {queued}"
    done = eventually(lambda: processed(lab) > before, 60)
    assert done, f"Worker chưa xử lý job sau 60 giây (jobs_processed_total vẫn {before})"


def test_storefront_calls_api_over_mtls(shop):
    lab, _, _ = shop
    answer = probe(lab, "storefront", "shell", "get:api:8000/healthz")["get:api:8000/healthz"]
    assert answer.startswith("ok 200"), f"storefront gọi http://api:8000/healthz: {answer}"
    expected = IDENTITY.format(sa="storefront", ns=lab.namespace)
    status = mesh_until(lab, "deployment/api", lambda s: expected in s["clients"], 30)
    assert expected in status["clients"], f"api chưa thấy storefront gọi qua mTLS; clients = {status['clients']}"
    assert status["success"] > 0, status


def test_redis_refuses_other_clients(shop):
    lab, _, _ = shop
    before = lab.mesh_status("deployment/redis")
    assert before["injected"] and before["mtls"], f"Redis của bài phải nằm trong mesh: {before}"
    intruder = probe(lab, "intruder", "shell", "redis:redis:6379")["redis:redis:6379"]
    legacy = probe(lab, "legacy-report", "shell", "redis:redis:6379")["redis:redis:6379"]
    assert intruder != "ok", "intruder (trong mesh, ServiceAccount intruder) vẫn PING được Redis"
    assert legacy != "ok", "legacy-report (ngoài mesh, không mTLS) vẫn PING được Redis"
    after = mesh_until(lab, "deployment/redis", lambda s: s["denied"] >= before["denied"] + 2, 30)
    assert after["denied"] >= before["denied"] + 2, f"Proxy của Redis phải ghi nhận hai kết nối bị AuthorizationPolicy từ chối (denied {before['denied']} -> {after['denied']})"


def test_policy_names_only_api_and_worker(shop):
    lab, _, _ = shop
    listed = lab.kubectl("get", "meshtlsauthentications.policy.linkerd.io", "-o", "json")
    items = json.loads(listed.stdout).get("items") or []
    assert items, "Chưa có MeshTLSAuthentication nào trong namespace"
    names = set()
    for item in items:
        spec = item.get("spec") or {}
        names |= {ref.get("name") for ref in spec.get("identityRefs") or [] if str(ref.get("kind")).lower() == "serviceaccount"}
        names |= {re.sub(r"\..*", "", i) for i in spec.get("identities") or []}
    assert names == {"api", "worker"}, f"MeshTLSAuthentication chỉ nên nêu api và worker, đang có {sorted(names)}"
