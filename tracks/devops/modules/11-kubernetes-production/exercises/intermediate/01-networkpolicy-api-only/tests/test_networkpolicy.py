import json
import subprocess
import time

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
DEPS = ex.fixtures / "deps.yaml"
APP = ex.fixtures / "app.yaml"
TRAP = ex.fixtures / "deny-without-dns.yaml"
PROBE = """
import json, socket, sys, urllib.request
out = {}
for target in sys.argv[1:]:
    kind, _, rest = target.partition(":")
    try:
        if kind == "dns":
            out[target] = "ok " + socket.gethostbyname(rest)
        elif kind == "http":
            with urllib.request.urlopen("http://" + rest, timeout=4) as answer:
                out[target] = "ok %d %s" % (answer.status, answer.read().decode()[:80])
        else:
            host, port = rest.rsplit(":", 1)
            socket.create_connection((host, int(port)), timeout=3).close()
            out[target] = "ok"
    except socket.gaierror as error:
        out[target] = "dns-loi " + str(error)
    except Exception as error:
        out[target] = "chan " + type(error).__name__ + " " + str(error)[:60]
print(json.dumps(out))
"""


def probe(lab, deployment: str, *targets: str) -> dict:
    result = lab.kubectl("exec", f"deployment/{deployment}", "--", "python", "-c", PROBE, *targets, check=False, timeout=150)
    assert result.returncode == 0, f"Không exec được vào {deployment}: {result.stderr[-400:]}"
    return json.loads(result.stdout)


def eventually_ok(lab, deployment: str, target: str, timeout: float = 40) -> str:
    deadline = time.monotonic() + timeout
    answer = ""
    while time.monotonic() < deadline:
        answer = probe(lab, deployment, target)[target]
        if answer.startswith("ok"):
            return answer
        time.sleep(2)
    return answer


def cluster_ip(lab, service: str) -> str:
    return lab.kubectl("get", "service", service, "-o", "jsonpath={.spec.clusterIP}").stdout.strip()


def restart_api(lab):
    lab.kubectl("rollout", "restart", "deployment/api")
    lab.kubectl("rollout", "status", "deployment/api", "--timeout=180s", timeout=200)


def start_stack(lab):
    lab.apply_learner(DEPS)
    lab.apply_learner(APP)
    for target in ("deployment/postgres", "deployment/redis", "deployment/api", "deployment/analytics", "deployment/intruder"):
        lab.kubectl("rollout", "status", target, "--timeout=180s", timeout=200)
    assert eventually_ok(lab, "api", "http:127.0.0.1:8000/readyz", 90).startswith("ok 200"), "Stack chưa sẵn sàng trước khi áp policy"


@pytest.fixture(scope="module")
def guarded():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab() as lab:
        start_stack(lab)
        ips = {name: cluster_ip(lab, name) for name in ("postgres", "redis", "api")}
        ips["kubernetes"] = lab.kubectl("get", "service", "kubernetes", "-n", "default", "-o",
                                        "jsonpath={.spec.clusterIP}", check=False).stdout.strip() or "10.96.0.1"
        before = probe(lab, "analytics", f"tcp:{ips['postgres']}:5432", f"tcp:{ips['kubernetes']}:443")
        lab.apply_learner(TRAP)
        time.sleep(5)
        restart_api(lab)
        trap = {"ip": eventually_ok(lab, "api", f"tcp:{ips['postgres']}:5432")}
        trap.update(probe(lab, "api", "dns:postgres", "http:127.0.0.1:8000/readyz"))
        lab.kubectl("delete", "networkpolicy", "--all", "--wait=true")
        try:
            applied = lab.apply_learner(ex.path("k8s"), check=False)
        except pytest.fail.Exception as error:
            applied = subprocess.CompletedProcess([], 1, "", str(error))
        time.sleep(5)
        restart_api(lab)
        yield lab, applied, ips, before, trap


def test_policies_apply(guarded):
    _, applied, _, before, _ = guarded
    assert applied.returncode == 0, applied.stderr[-1500:]
    assert all(v == "ok" for v in before.values()), f"Trước khi áp policy mọi kết nối phải mở (đối chứng): {before}"


def test_api_ready_through_dns(guarded):
    lab, _, _, _, _ = guarded
    answer = eventually_ok(lab, "api", "http:127.0.0.1:8000/readyz")
    assert answer.startswith("ok 200") and '"db":"ok"' in answer and '"redis":"ok"' in answer, \
        f"/readyz của api sau khi áp policy: {answer}"


def test_api_reaches_postgres_and_redis(guarded):
    lab, _, ips, _, _ = guarded
    for target in (f"tcp:{ips['postgres']}:5432", f"tcp:{ips['redis']}:6379", "tcp:postgres:5432", "tcp:redis:6379"):
        assert eventually_ok(lab, "api", target) == "ok", f"api phải tới được {target}"


def test_analytics_uses_api_only(guarded):
    lab, _, ips, _, _ = guarded
    assert eventually_ok(lab, "analytics", "http:api:8000/healthz").startswith("ok 200"), "analytics gọi được api:8000 qua tên"
    assert eventually_ok(lab, "analytics", "dns:postgres").startswith("ok"), "DNS mở cho mọi pod trong namespace"
    blocked = probe(lab, "analytics", f"tcp:{ips['postgres']}:5432", f"tcp:{ips['redis']}:6379")
    assert all(v.startswith("chan") for v in blocked.values()), f"analytics không được tới Postgres, Redis: {blocked}"


def test_api_ingress_only_from_analytics(guarded):
    lab, _, ips, _, _ = guarded
    blocked = probe(lab, "intruder", f"tcp:{ips['api']}:8000", f"tcp:{ips['postgres']}:5432", f"tcp:{ips['redis']}:6379")
    assert all(v.startswith("chan") for v in blocked.values()), f"Pod khác (intruder) không được tới api, Postgres, Redis: {blocked}"


def test_default_deny_egress(guarded):
    lab, _, ips, _, _ = guarded
    blocked = probe(lab, "api", f"tcp:{ips['kubernetes']}:443")
    assert all(v.startswith("chan") for v in blocked.values()), f"api không cần ra API server hay chỗ khác: {blocked}"
    blocked = probe(lab, "analytics", f"tcp:{ips['kubernetes']}:443")
    assert all(v.startswith("chan") for v in blocked.values()), f"analytics không cần ra API server: {blocked}"


def test_deny_without_dns_breaks_name_lookup(guarded):
    _, _, _, _, trap = guarded
    assert trap["ip"] == "ok", f"Policy mẫu vẫn cho api tới Postgres theo IP: {trap}"
    assert trap["dns:postgres"].startswith("dns-loi"), f"Thiếu luật DNS thì không phân giải được tên: {trap}"
    assert not trap["http:127.0.0.1:8000/readyz"].startswith("ok 200"), trap
