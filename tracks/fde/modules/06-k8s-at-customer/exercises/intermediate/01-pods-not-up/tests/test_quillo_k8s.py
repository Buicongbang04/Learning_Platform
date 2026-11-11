import json
import secrets
import shlex
import subprocess
import time

import pytest

import fdekit
from testkit import ROOT, Exercise

ex = Exercise(__file__)
BUNDLE = ROOT / "tracks" / "fde" / "product" / "dist" / "quillo-1.0.0.tar"
BUILD = "nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist"
DEPLOY_DIR = "/home/fde/deploy"
DEPLOY_TIMEOUT = 180
READY_WAIT = 90
INGEST_WAIT = 60
PF_PORT = 18080
REGISTRY = "10.0.2.101:5000/"
WORKLOADS = [("deployment", "quillo-api"), ("deployment", "quillo-worker"), ("deployment", "quillo-llm"),
             ("deployment", "quillo-embed"), ("statefulset", "quillo-db")]
PROBE = """apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: fde-test-probe-egress}
spec:
  podSelector: {matchLabels: {app.kubernetes.io/name: fde-test-probe}}
  policyTypes: [Egress]
  egress: [{to: [{podSelector: {}}]}]
---
apiVersion: v1
kind: Pod
metadata:
  name: fde-test-probe
  labels: {app.kubernetes.io/name: fde-test-probe}
spec:
  automountServiceAccountToken: false
  terminationGracePeriodSeconds: 0
  securityContext: {runAsNonRoot: true, runAsUser: 65534, runAsGroup: 65534, seccompProfile: {type: RuntimeDefault}}
  containers:
    - name: probe
      image: rancher/mirrored-library-busybox:1.37.0
      imagePullPolicy: IfNotPresent
      command: [sleep, "3600"]
      securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: [ALL]}}
      resources: {requests: {cpu: 10m, memory: 16Mi}, limits: {cpu: 100m, memory: 32Mi}}
"""


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def diagnostics(m) -> str:
    out = sh(m, "kubectl get pods -o wide; kubectl get events --sort-by=.lastTimestamp | tail -15", timeout=60)
    return f"{out.stdout[-3000:]}{out.stderr[-500:]}"


def deploy(m) -> None:
    run = sh(m, f"cd /home/fde && sh {DEPLOY_DIR}/deploy.sh", timeout=DEPLOY_TIMEOUT)
    assert run.returncode == 0, (f"deploy.sh thoát mã {run.returncode}\nstdout:\n{run.stdout[-2000:]}\n"
                                 f"stderr:\n{run.stderr[-2000:]}\n--- namespace quillo ---\n{diagnostics(m)}")


def wait_ready(m) -> None:
    releases = json.loads(sh(m, "helm list -n quillo -o json").stdout or "[]")
    release = next((r for r in releases if r.get("name") == "quillo"), {})
    assert release.get("status") == "deployed", f"Cần release Helm 'quillo' ở trạng thái deployed, có: {releases}"
    assert release.get("chart") == "quillo-1.0.0", (
        f"Release quillo phải từ chart quillo 1.0.0 của bundle, đang {release.get('chart')}")
    deadline = time.monotonic() + READY_WAIT
    pending = list(WORKLOADS)
    while pending and time.monotonic() < deadline:
        still = []
        for kind, name in pending:
            raw = sh(m, f"kubectl get {kind} {name} -o json 2>/dev/null").stdout
            state = json.loads(raw).get("status", {}) if raw else {}
            key = "availableReplicas" if kind == "deployment" else "readyReplicas"
            if not state.get(key):
                still.append((kind, name))
        pending = still
        if pending:
            time.sleep(3)
    assert not pending, (f"Sau {READY_WAIT} s vẫn chưa sẵn sàng: {pending}\n{diagnostics(m)}")


def check_images(m) -> None:
    pods = json.loads(sh(m, "kubectl get pods -l app.kubernetes.io/instance=quillo -o json").stdout)["items"]
    images = {c["image"] for p in pods for c in [*p["spec"]["containers"], *(p["spec"].get("initContainers") or [])]}
    outside = sorted(i for i in images if not i.startswith(REGISTRY))
    assert images and not outside, f"Mọi image phải kéo từ registry nội bộ {REGISTRY}, có: {outside}"


def admin_token(m) -> str:
    api = json.loads(sh(m, "kubectl get deployment quillo-api -o json").stdout)
    env = api["spec"]["template"]["spec"]["containers"][0].get("env", [])
    ref = next((e["valueFrom"]["secretKeyRef"] for e in env if e["name"] == "QUILLO_ADMIN_TOKEN"
                and "secretKeyRef" in e.get("valueFrom", {})), None)
    assert ref, "Deployment quillo-api phải lấy QUILLO_ADMIN_TOKEN từ một Secret"
    out = sh(m, f"kubectl get secret {shlex.quote(ref['name'])} -o json").stdout
    data = json.loads(out)["data"][ref["key"]]
    return sh(m, f"printf %s {shlex.quote(data)} | base64 -d").stdout


def curl(m, args: str, timeout: float = 60) -> tuple[int, str]:
    out = sh(m, f"curl -s -m {int(timeout)} -o /tmp/body -w '%{{http_code}}' {args}; echo; cat /tmp/body",
             timeout=timeout + 15).stdout
    code, _, body = out.partition("\n")
    return int(code or 0), body


def check_app(m, token: str) -> None:
    base = f"http://127.0.0.1:{PF_PORT}"
    auth = f"-H {shlex.quote('Authorization: Bearer ' + token)}"
    code, body = curl(m, f"{base}/healthz")
    assert code == 200, f"/healthz qua kubectl port-forward trả {code}: {body[:300]}\n{diagnostics(m)}"
    assert json.loads(body).get("version") == "1.0.0", f"/healthz phải báo version 1.0.0: {body[:200]}"

    fee = secrets.token_hex(3)
    text = f"Hop dong dich vu phap ly so {fee}: phi tu van {int(fee, 16) % 900 + 100} trieu dong moi quy."
    assert sh(m, f"printf %s {shlex.quote(text)} > /tmp/contract-{fee}.txt").returncode == 0
    code, body = curl(m, f"{auth} -F file=@/tmp/contract-{fee}.txt {base}/api/documents")
    assert code == 201, f"Tải tài liệu qua /api/documents trả {code}: {body[:300]}"
    uploaded = json.loads(body)["doc_id"]

    note = f"inbox-{secrets.token_hex(4)}.txt"
    worker = sh(m, "kubectl get pod -l app.kubernetes.io/component=worker,app.kubernetes.io/instance=quillo "
                   "-o jsonpath='{.items[0].metadata.name}'").stdout.strip()
    assert worker, "Không thấy pod worker của quillo"
    assert sh(m, f"printf %s {shlex.quote('Phu luc ' + fee + ': gia han hop dong 12 thang.')} > /tmp/{note}"
                 f" && kubectl cp /tmp/{note} {worker}:/data/inbox/{note}", timeout=60).returncode == 0
    deadline = time.monotonic() + INGEST_WAIT
    names = []
    while time.monotonic() < deadline:
        code, body = curl(m, f"{auth} {base}/api/documents")
        names = [d["filename"] for d in json.loads(body)] if code == 200 else []
        if note in names:
            break
        time.sleep(3)
    assert note in names, f"Worker không nạp tệp đặt vào /data/inbox sau {INGEST_WAIT} s (thấy {names})"

    question = json.dumps({"question": f"Phi tu van cua hop dong so {fee} la bao nhieu?"})
    code, body = curl(m, f"{auth} -H 'Content-Type: application/json' -d {shlex.quote(question)} {base}/api/ask",
                      timeout=120)
    assert code == 200, f"/api/ask trả {code}: {body[:300]}"
    cited = {c["doc_id"] for c in json.loads(body).get("citations", [])}
    assert uploaded in cited, f"/api/ask phải trích dẫn tài liệu vừa tải ({uploaded}), trích: {sorted(cited)}"


def check_isolation(m, tmp_path) -> None:
    (tmp_path / "probe.yaml").write_text(PROBE)
    m.put(tmp_path / "probe.yaml", "/tmp/probe.yaml")
    done = sh(m, "kubectl apply -f /tmp/probe.yaml && kubectl wait --for=condition=Ready pod/fde-test-probe "
                 "--timeout=60s", timeout=90)
    assert done.returncode == 0, f"Test không tạo được pod thử: {done.stderr}"
    for service, port in (("quillo-db", 5432), ("quillo-llm", 8080)):
        ip = sh(m, f"kubectl get svc {service} -o jsonpath='{{.spec.clusterIP}}'").stdout.strip()
        probe = sh(m, f"kubectl exec fde-test-probe -- nc -z -w 3 {ip} {port}", timeout=30)
        assert probe.returncode != 0, f"Một pod khác trong namespace kết nối được tới {service}:{port}"
    out = sh(m, "kubectl exec quillo-db-0 -- timeout 5 bash -c 'exec 3<>/dev/tcp/10.0.2.101/5000' "
                "&& echo open || echo closed", timeout=30).stdout
    assert "closed" in out, "Pod db mở được kết nối ra ngoài namespace (10.0.2.101:5000)"


def test_quillo_up_in_namespace(tmp_path):
    if not BUNDLE.is_file():
        pytest.skip(f"Chưa có {BUNDLE.relative_to(ROOT)}; dựng bằng: {BUILD}")
    files = [p for p in sorted(ex.target.iterdir()) if p.is_file() and p.name != "SOLUTION.md"]
    with fdekit.customer_site("lawfirm-prod") as s:
        m = s.vm
        before = sh(m, "kubectl get networkpolicy default-deny -o jsonpath='{.spec}'").stdout
        assert before, "Không đọc được NetworkPolicy default-deny của khách"
        m.put(BUNDLE, "/home/fde/quillo-1.0.0.tar")
        assert sh(m, f"mkdir -p {DEPLOY_DIR}").returncode == 0
        for path in files:
            m.put(path, f"{DEPLOY_DIR}/{path.name}")

        deploy(m)
        wait_ready(m)
        check_images(m)
        token = admin_token(m)
        pf = sh(m, f"setsid nohup kubectl port-forward svc/quillo-api {PF_PORT}:8080 >/tmp/pf.log 2>&1 "
                   f"</dev/null & sleep 3; cat /tmp/pf.log")
        assert "Forwarding" in pf.stdout, f"kubectl port-forward svc/quillo-api không chạy: {pf.stdout}{pf.stderr}"
        check_app(m, token)
        check_isolation(m, tmp_path)
        after = sh(m, "kubectl get networkpolicy default-deny -o jsonpath='{.spec}'").stdout
        assert after == before, "NetworkPolicy default-deny của khách đã bị đổi"
