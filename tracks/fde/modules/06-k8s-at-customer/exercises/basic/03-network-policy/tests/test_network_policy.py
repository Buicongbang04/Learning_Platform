import json
import shlex
import subprocess
import time
from pathlib import Path

import pytest
import yaml

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
WORK = "/home/fde/netpol"
READY_WAIT = 90
ROUNDS = 4
REGISTRY = ("10.0.2.101", 5000)
QUILLO = ("api", "worker", "db", "llm", "embed")
ALLOWED = [("api", "db", 5432), ("api", "llm", 8080), ("api", "embed", 8080), ("worker", "db", 5432),
           ("worker", "embed", 8080), ("gateway", "api", 8080)]
DENIED = [("worker", "llm", 8080), ("worker", "api", 8080), ("api", "db", 8080), ("gateway", "db", 5432),
          ("gateway", "llm", 8080), ("gateway", "worker", 8080), ("other", "api", 8080), ("other", "db", 5432),
          ("other", "embed", 8080), ("db", "api", 8080), ("llm", "db", 5432), ("embed", "db", 5432),
          ("api", "gateway", 8080), ("api", "other", 8080), ("api", "registry", 5000), ("llm", "registry", 5000),
          ("db", "registry", 5000), ("worker", "registry", 5000)]


IT_POLICIES = ("default-deny", "reporting-egress", "fde-test-control-egress")
REPORTING_EGRESS = {
    "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
    "metadata": {"name": "reporting-egress"},
    "spec": {"podSelector": {"matchLabels": {"app.kubernetes.io/name": "reporting"}}, "policyTypes": ["Egress"],
             "egress": [{"to": [{"podSelector": {}}]}]},
}

CONTROL_EGRESS = {
    "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
    "metadata": {"name": "fde-test-control-egress"},
    "spec": {"podSelector": {"matchLabels": {"app.kubernetes.io/name": "fde-test-control"}}, "policyTypes": ["Egress"],
             "egress": [{"to": [{"ipBlock": {"cidr": f"{REGISTRY[0]}/32"}}], "ports": [{"port": REGISTRY[1]}]}]},
}
CONTROL_WAIT = 30


def labels(role: str) -> dict:
    if role in QUILLO:
        return {"app.kubernetes.io/name": "quillo", "app.kubernetes.io/instance": "quillo",
                "app.kubernetes.io/component": role}
    names = {"gateway": "lawfirm-gateway", "other": "reporting", "control": "fde-test-control"}
    return {"app.kubernetes.io/name": names[role]}


def probe_pod(role: str) -> dict:
    return {
        "apiVersion": "v1", "kind": "Pod",
        "metadata": {"name": f"np-{role}", "labels": labels(role)},
        "spec": {
            "automountServiceAccountToken": False,
            "terminationGracePeriodSeconds": 0,
            "securityContext": {"runAsNonRoot": True, "runAsUser": 65534, "runAsGroup": 65534,
                                "seccompProfile": {"type": "RuntimeDefault"}},
            "containers": [{
                "name": "probe", "image": "rancher/mirrored-library-busybox:1.37.0", "imagePullPolicy": "IfNotPresent",
                "command": ["sh", "-c", "httpd -f -p 8080 -h /tmp & httpd -f -p 5432 -h /tmp & exec sleep 86400"],
                "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
                "resources": {"requests": {"cpu": "10m", "memory": "16Mi"}, "limits": {"cpu": "100m", "memory": "32Mi"}},
            }],
        },
    }


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def check_file(path: Path) -> None:
    try:
        docs = [d for d in yaml.safe_load_all(path.read_text()) if d]
    except yaml.YAMLError as error:
        pytest.fail(f"networkpolicy.yaml không phải YAML hợp lệ: {error}")
    assert docs, "networkpolicy.yaml chưa có object nào"
    for doc in docs:
        assert doc.get("kind") == "NetworkPolicy", f"Chỉ được có NetworkPolicy, gặp {doc.get('kind')!r}"
        name = (doc.get("metadata") or {}).get("name")
        assert name and name not in IT_POLICIES, f"Tên NetworkPolicy không hợp lệ hoặc trùng policy của IT: {name!r}"
        namespace = doc["metadata"].get("namespace", "quillo")
        assert namespace == "quillo", f"NetworkPolicy {name} phải ở namespace quillo, đang {namespace!r}"


def addresses(m) -> dict:
    pods = json.loads(sh(m, "kubectl get pods -l '!job' -o json").stdout)["items"]
    found = {p["metadata"]["name"][3:]: p["status"].get("podIP") for p in pods if p["metadata"]["name"].startswith("np-")}
    found["registry"] = REGISTRY[0]
    return found


def probe(m, src: str, flows: list[tuple[str, int]], ips: dict) -> dict:
    script = " ".join(f"(nc -z -w 2 {ips[dst]} {port} && echo {dst}:{port}=ok || echo {dst}:{port}=no) &"
                      for dst, port in flows) + " wait"
    run = None
    for _ in range(3):
        run = sh(m, f"kubectl exec np-{src} -- sh -c {shlex.quote(script)}", timeout=120)
        results = {}
        for line in run.stdout.split():
            key, _, value = line.partition("=")
            dst, _, port = key.partition(":")
            if value in ("ok", "no") and port.isdigit():
                results[(src, dst, int(port))] = value == "ok"
        if run.returncode == 0 and len(results) == len(flows):
            return results
        time.sleep(2)
    pytest.fail(f"Test không chạy được nc trong pod np-{src} (kubectl exec mã {run.returncode}): {run.stderr[-500:]}")


def matrix(m, ips: dict) -> dict:
    results = {}
    for src in sorted({src for src, _, _ in ALLOWED + DENIED}):
        results.update(probe(m, src, [(dst, port) for s, dst, port in ALLOWED + DENIED if s == src], ips))
    return results


def check_control(m, ips: dict) -> None:
    deadline = time.monotonic() + CONTROL_WAIT
    while True:
        if probe(m, "control", [("registry", REGISTRY[1])], ips)[("control", "registry", REGISTRY[1])]:
            return
        if time.monotonic() > deadline:
            pytest.fail("Lỗi môi trường test: pod đối chứng có egress tường minh vẫn không tới được "
                        f"{REGISTRY[0]}:{REGISTRY[1]}, nên không kiểm được các luồng ra ngoài namespace")
        time.sleep(3)


def name(flow: tuple) -> str:
    return f"{flow[0]} → {flow[1]}:{flow[2]}"


def test_network_policy_matches_flow_table(tmp_path):
    policy = ex.path("networkpolicy.yaml")
    check_file(policy)
    with fdekit.customer_site("lawfirm-prod") as site:
        m = site.vm
        before = sh(m, "kubectl get networkpolicy default-deny -o jsonpath='{.spec}'").stdout
        assert before, "Không đọc được NetworkPolicy default-deny của khách"
        assert sh(m, f"mkdir -p {WORK}").returncode == 0
        (tmp_path / "probes.yaml").write_text(yaml.safe_dump_all([REPORTING_EGRESS, CONTROL_EGRESS, *(
            probe_pod(r) for r in (*QUILLO, "gateway", "other", "control"))]))
        m.put(tmp_path / "probes.yaml", f"{WORK}/probes.yaml")
        m.put(policy, f"{WORK}/networkpolicy.yaml")
        done = sh(m, f"kubectl apply -f {WORK}/probes.yaml")
        assert done.returncode == 0, f"Test không tạo được pod thử: {done.stderr}"
        ready = sh(m, f"kubectl wait --for=condition=Ready pod -l 'app.kubernetes.io/name' --timeout={READY_WAIT}s",
                   timeout=READY_WAIT + 30)
        assert ready.returncode == 0, f"Pod thử chưa Ready: {ready.stderr}"
        ips = addresses(m)
        check_control(m, ips)
        done = sh(m, f"kubectl apply -n quillo -f {WORK}/networkpolicy.yaml")
        assert done.returncode == 0, f"kubectl apply networkpolicy.yaml bị từ chối:\n{done.stderr[-2000:]}"
        assert all(ips.get(r) for r in (*QUILLO, "gateway", "other")), f"Thiếu IP pod thử: {ips}"

        opened: set = set()
        leaked: set = set()
        for attempt in range(ROUNDS):
            results = matrix(m, ips)
            opened |= {f for f in ALLOWED if results.get(f)}
            leaked |= {f for f in DENIED if results[f]}
            if attempt >= 1 and opened == set(ALLOWED):
                break
            time.sleep(3)
        assert not leaked, "Luồng phải bị chặn nhưng vẫn kết nối được: " + ", ".join(sorted(map(name, leaked)))
        closed = set(ALLOWED) - opened
        assert not closed, "Luồng phải mở nhưng không kết nối được: " + ", ".join(sorted(map(name, closed)))
        after = sh(m, "kubectl get networkpolicy default-deny -o jsonpath='{.spec}'").stdout
        assert after == before, "NetworkPolicy default-deny của khách đã bị đổi"
        reporting = json.loads(sh(m, "kubectl get networkpolicy reporting-egress -o json").stdout or "{}")
        assert reporting.get("spec") == REPORTING_EGRESS["spec"], (
            "NetworkPolicy reporting-egress của IT đã bị đổi")
