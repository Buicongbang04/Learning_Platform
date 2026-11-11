import hashlib
import io
import json
import secrets
import shlex
import subprocess
import tarfile
import time
import urllib.request

import pytest

import fdekit
from testkit import ROOT, Exercise

ex = Exercise(__file__)
TOOLS = ROOT / "data" / "raw" / "fde-tools"
K3S_VERSION = "v1.37.1+k3s1"
K3S_DIR = TOOLS / f"k3s-{K3S_VERSION}"
K3S_RELEASE = f"https://github.com/k3s-io/k3s/releases/download/{K3S_VERSION.replace('+', '%2B')}"
K3S_FILES = {
    "k3s": ("92b94582eb7b34a8cf532e6006842b9ed215a6783cf56a3dd6271fd35243b2c0", f"{K3S_RELEASE}/k3s"),
    "k3s-airgap-images-amd64.tar.zst": ("865b2a63ad7a63fc0db17b7fc2985bf4ae11d5ae93ca1472be6218d20aeb6b23",
                                        f"{K3S_RELEASE}/k3s-airgap-images-amd64.tar.zst"),
    "install.sh": ("ed01f89fd977bf20ac1516bbebf8370bf3ddbaa55dac8aba610956a4c78cc00b",
                   f"https://raw.githubusercontent.com/k3s-io/k3s/{K3S_VERSION}/install.sh"),
}
BUSYBOX = TOOLS / "busybox-1.35.0" / "busybox"
BUSYBOX_SHA256 = "6e123e7f3202a8c1e9b1f94d8941580a25135382b99e8d3e34fb858bba311348"
BUSYBOX_URL = "https://busybox.net/downloads/binaries/1.35.0-x86_64-linux-musl/busybox"
AIRGAP = "/home/fde/k3s-airgap"
IMAGE_REPO, IMAGE_TAG = "lawfirm/hello", "1.0"
IMAGE = f"10.0.2.101:5000/{IMAGE_REPO}:{IMAGE_TAG}"
INSTALL_TIMEOUT = 150
SYSTEM_WAIT = 120
APP_WAIT = 90
SYSTEM = ("coredns", "local-path-provisioner", "metrics-server")
CLIENT = """apiVersion: v1
kind: Pod
metadata: {name: fde-test-client-%(n)s, namespace: default}
spec:
  restartPolicy: Never
  containers:
    - name: client
      image: rancher/mirrored-library-busybox:1.37.0
      imagePullPolicy: IfNotPresent
      command: [wget, -qO-, -T, "5", "http://hello.default.svc.cluster.local/"]
"""


def require_tools() -> None:
    for name, (sha, url) in K3S_FILES.items():
        path = K3S_DIR / name
        how = (f"mkdir -p '{K3S_DIR.relative_to(ROOT)}' && curl -fLo '{path.relative_to(ROOT)}' '{url}' && "
               f"echo '{sha}  {path.relative_to(ROOT)}' | sha256sum -c -")
        if not path.is_file() or _sha(path) != sha:
            pytest.skip(f"Chưa có (hoặc sai sha256) {path.relative_to(ROOT)}; tải bằng: {how}")
    if not BUSYBOX.is_file() or _sha(BUSYBOX) != BUSYBOX_SHA256:
        pytest.skip(f"Chưa có (hoặc sai sha256) {BUSYBOX.relative_to(ROOT)}; tải bằng: mkdir -p "
                    f"{BUSYBOX.parent.relative_to(ROOT)} && curl -fLo {BUSYBOX.relative_to(ROOT)} {BUSYBOX_URL} && "
                    f"echo '{BUSYBOX_SHA256}  {BUSYBOX.relative_to(ROOT)}' | sha256sum -c -")


def _sha(path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _entry(name: str, data: bytes | None = None, mode: int = 0o755, kind: bytes = tarfile.REGTYPE, link: str = ""):
    info = tarfile.TarInfo(name)
    info.mode, info.type, info.linkname, info.mtime = mode, kind, link, 0
    if data is not None:
        info.size = len(data)
    return info, (io.BytesIO(data) if data is not None else None)


def push_hello(registry_host: str, message: str) -> None:
    """Image OCI `lawfirm/hello:1.0` (BusyBox tĩnh, httpd cổng 8080 trả `message`) đẩy thẳng lên registry qua HTTP API."""
    start = (f"#!/bin/sh\n/bin/busybox mkdir -p /tmp/www\necho {message} > /tmp/www/index.html\n"
             f"exec /bin/busybox httpd -f -p 8080 -h /tmp/www\n").encode()
    layer = io.BytesIO()
    with tarfile.open(fileobj=layer, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for info, data in (_entry("bin", kind=tarfile.DIRTYPE), _entry("bin/busybox", BUSYBOX.read_bytes()),
                           _entry("bin/sh", kind=tarfile.SYMTYPE, link="busybox", mode=0o777),
                           _entry("app", kind=tarfile.DIRTYPE), _entry("app/start", start),
                           _entry("tmp", kind=tarfile.DIRTYPE, mode=0o1777)):
            tar.addfile(info, data)
    blob = layer.getvalue()
    layer_digest = "sha256:" + hashlib.sha256(blob).hexdigest()
    config = json.dumps({"architecture": "amd64", "os": "linux",
                         "config": {"Entrypoint": ["/app/start"], "User": "65534", "ExposedPorts": {"8080/tcp": {}}},
                         "rootfs": {"type": "layers", "diff_ids": [layer_digest]}}, sort_keys=True).encode()
    config_digest = "sha256:" + hashlib.sha256(config).hexdigest()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f"http://{registry_host}"
    for digest, data in ((layer_digest, blob), (config_digest, config)):
        started = opener.open(urllib.request.Request(f"{base}/v2/{IMAGE_REPO}/blobs/uploads/", data=b"",
                                                     method="POST"), timeout=30)
        location = started.headers["Location"]
        location = location if location.startswith("http") else base + location
        sep = "&" if "?" in location else "?"
        opener.open(urllib.request.Request(f"{location}{sep}digest={digest}", data=data, method="PUT",
                                           headers={"Content-Type": "application/octet-stream"}), timeout=60)
    manifest = json.dumps({
        "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {"mediaType": "application/vnd.oci.image.config.v1+json", "digest": config_digest,
                   "size": len(config)},
        "layers": [{"mediaType": "application/vnd.oci.image.layer.v1.tar", "digest": layer_digest, "size": len(blob)}],
    }).encode()
    opener.open(urllib.request.Request(f"{base}/v2/{IMAGE_REPO}/manifests/{IMAGE_TAG}", data=manifest, method="PUT",
                                       headers={"Content-Type": "application/vnd.oci.image.manifest.v1+json"}),
                timeout=30)


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def kubectl(m, args: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return sh(m, f"sudo -n k3s kubectl {args}", timeout=timeout)


def diagnostics(m) -> str:
    out = sh(m, "systemctl is-active k3s; sudo -n k3s kubectl get nodes,pods -A -o wide 2>&1 | tail -20; "
                "sudo -n k3s kubectl get events -A --sort-by=.lastTimestamp 2>&1 | tail -8", timeout=60)
    return out.stdout[-3500:]


def install(m, attempt: str) -> None:
    run = sh(m, f"cd /home/fde && sh /home/fde/install_k3s.sh", timeout=INSTALL_TIMEOUT)
    assert run.returncode == 0, (f"install_k3s.sh ({attempt}) thoát mã {run.returncode}\nstdout:\n"
                                 f"{run.stdout[-2000:]}\nstderr:\n{run.stderr[-2000:]}")


def wait_system(m, attempt: str) -> None:
    deadline = time.monotonic() + SYSTEM_WAIT
    pending = list(SYSTEM)
    node_ready = False
    while time.monotonic() < deadline:
        nodes = kubectl(m, "get nodes -o json 2>/dev/null", timeout=30).stdout
        items = json.loads(nodes)["items"] if nodes.strip() else []
        node_ready = bool(items) and all(c["status"] == "True" for n in items for c in n["status"]["conditions"]
                                         if c["type"] == "Ready")
        pending = []
        for name in SYSTEM:
            raw = kubectl(m, f"-n kube-system get deployment {name} -o json 2>/dev/null", timeout=30).stdout
            if not raw.strip() or not json.loads(raw).get("status", {}).get("availableReplicas"):
                pending.append(name)
        if node_ready and not pending:
            return
        time.sleep(3)
    pytest.fail(f"{attempt}: sau {SYSTEM_WAIT} s node Ready={node_ready}, chưa sẵn sàng trong kube-system: "
                f"{pending}\n{diagnostics(m)}")


def check_hello(m, message: str, attempt: str) -> None:
    done = kubectl(m, "rollout status deployment/hello -n default --timeout=%ds" % APP_WAIT, timeout=APP_WAIT + 30)
    assert done.returncode == 0, f"{attempt}: deployment hello chưa sẵn sàng sau {APP_WAIT} s\n{diagnostics(m)}"
    pods = json.loads(kubectl(m, "get pods -n default -l app=hello -o json").stdout)["items"]
    images = {c["image"] for p in pods for c in p["spec"]["containers"]}
    assert images == {IMAGE}, f"{attempt}: pod hello phải chạy image {IMAGE}, đang {images}"
    ip = kubectl(m, "get svc hello -n default -o jsonpath='{.spec.clusterIP}'").stdout.strip()
    host = f"[{ip}]" if ":" in ip else ip
    deadline = time.monotonic() + 30
    while True:
        direct = sh(m, f"curl -s -m 5 http://{host}/", timeout=30)
        if (direct.returncode == 0 and direct.stdout.strip() == message) or time.monotonic() > deadline:
            break
        time.sleep(2)
    assert direct.returncode == 0 and direct.stdout.strip() == message, (
        f"{attempt}: từ chính máy, curl http://{host}/ (ClusterIP của service hello) phải nhận {message!r} "
        f"(curl mã {direct.returncode}, nhận {direct.stdout.strip()[:200]!r})")
    n = secrets.token_hex(3)
    done = sh(m, f"printf %s {shlex.quote(CLIENT % {'n': n})} | sudo -n k3s kubectl apply -f -")
    assert done.returncode == 0, done.stderr
    deadline = time.monotonic() + 60
    phase = ""
    while time.monotonic() < deadline:
        phase = kubectl(m, f"get pod fde-test-client-{n} -n default -o jsonpath='{{.status.phase}}'").stdout.strip()
        if phase in ("Succeeded", "Failed"):
            break
        time.sleep(2)
    body = kubectl(m, f"logs fde-test-client-{n} -n default").stdout.strip()
    assert phase == "Succeeded" and body == message, (
        f"{attempt}: pod trong cluster gọi http://hello.default.svc.cluster.local/ phải nhận {message!r} "
        f"(pod {phase}, nhận {body[:200]!r})\n{diagnostics(m)}")


def test_k3s_airgap_on_lawfirm_staging():
    require_tools()
    message = f"xin-chao-{secrets.token_hex(5)}"
    with fdekit.customer_site("lawfirm-staging") as s:
        m = s.vm
        push_hello(s.registry_host, message)
        assert sh(m, f"mkdir -p {AIRGAP}").returncode == 0
        for name in K3S_FILES:
            m.put(K3S_DIR / name, f"{AIRGAP}/{name}")
        m.put(ex.path("install_k3s.sh"), "/home/fde/install_k3s.sh")
        m.put(ex.dir / "hello.yaml", "/home/fde/hello.yaml")

        install(m, "lần 1")
        wait_system(m, "lần 1")
        version = sh(m, "k3s --version").stdout
        assert K3S_VERSION in version, f"k3s phải là {K3S_VERSION}, đang: {version.strip()[:120]}"
        done = kubectl(m, "apply -f /home/fde/hello.yaml")
        assert done.returncode == 0, f"Áp hello.yaml lỗi: {done.stderr}"
        check_hello(m, message, "lần 1")

        install(m, "lần 2 (chạy lại trên máy đã cài)")
        wait_system(m, "lần 2")
        check_hello(m, message, "lần 2")
