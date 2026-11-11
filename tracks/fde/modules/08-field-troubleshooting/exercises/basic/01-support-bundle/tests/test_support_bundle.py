import hashlib
import io
import json
import secrets
import shlex
import string
import subprocess
import tarfile
import time
from pathlib import Path

import pytest

import fdekit
from testkit import ROOT, Exercise

ex = Exercise(__file__)
TOOLS = ROOT / "data" / "raw" / "fde-tools"
BUSYBOX = TOOLS / "busybox-1.35.0" / "busybox"
BUSYBOX_SHA256 = "6e123e7f3202a8c1e9b1f94d8941580a25135382b99e8d3e34fb858bba311348"
BUSYBOX_URL = "https://busybox.net/downloads/binaries/1.35.0-x86_64-linux-musl/busybox"
IMAGE_TAG = "localhost/docbridge-cache:1.0"
RUN_TIMEOUT = 60
MAX_BUNDLE = 5 * 1024 * 1024
MAX_APP_LOG = 2 * 1024 * 1024
MIN_APP_LOG_LINES = 1000
LEAK_WINDOW = 10
REQUIRED = ["system/os-release", "system/uname.txt", "system/df.txt", "system/memory.txt", "system/uptime.txt",
            "network/listen.txt", "network/ip.txt", "docbridge/status.txt", "docbridge/journal.txt",
            "docbridge/docbridge.conf", "docbridge/docbridge.log", "errors.txt"]
DOCKER_ITEMS = ["docker/ps.txt", "docker/docbridge-cache.log", "docker/docbridge-cache.json"]
CACHE_START = b"""#!/bin/sh
/bin/busybox echo "docbridge-cache 1.0 khoi dong, size=${CACHE_SIZE_MB}MB"
/bin/busybox echo "upstream redis://:${CACHE_UPSTREAM_PASSWORD}@10.20.0.7:6379/0"
/bin/busybox echo "marker ${CACHE_MARKER}"
/bin/busybox mkdir -p /tmp/www
exec /bin/busybox httpd -f -p 8080 -h /tmp/www
"""
SERVICE = """import http.server, os, sys
port = int(open("/etc/docbridge/docbridge.conf").read().split("listen_port=")[1].split()[0])
print("docbridge khoi dong, ERP dsn=" + os.environ["DOCBRIDGE_ERP_DSN"], flush=True)
print("marker " + os.environ["DOCBRIDGE_MARKER"], flush=True)
http.server.HTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
"""


def secret(prefix: str) -> str:
    alphabet = string.ascii_letters + string.digits
    return prefix + "".join(secrets.choice(alphabet) for _ in range(22))


def require_busybox() -> None:
    how = (f"mkdir -p {BUSYBOX.parent.relative_to(ROOT)} && curl -fLo {BUSYBOX.relative_to(ROOT)} {BUSYBOX_URL} "
           f"&& echo '{BUSYBOX_SHA256}  {BUSYBOX.relative_to(ROOT)}' | sha256sum -c -")
    if not BUSYBOX.is_file():
        pytest.skip(f"Chưa có {BUSYBOX.relative_to(ROOT)}; {how}")
    if hashlib.sha256(BUSYBOX.read_bytes()).hexdigest() != BUSYBOX_SHA256:
        pytest.skip(f"{BUSYBOX.relative_to(ROOT)} sai sha256; xoá rồi tải lại: {how}")


def _entry(name: str, *, data: bytes | None = None, mode: int = 0o755, kind: bytes = tarfile.REGTYPE,
           link: str = "") -> tuple[tarfile.TarInfo, io.BytesIO | None]:
    info = tarfile.TarInfo(name)
    info.mode, info.type, info.linkname, info.mtime = mode, kind, link, 0
    if data is not None:
        info.size = len(data)
    return info, (io.BytesIO(data) if data is not None else None)


def build_image(out: Path) -> None:
    layer = io.BytesIO()
    with tarfile.open(fileobj=layer, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for info, data in (_entry("bin", kind=tarfile.DIRTYPE), _entry("bin/busybox", data=BUSYBOX.read_bytes()),
                           _entry("bin/sh", kind=tarfile.SYMTYPE, link="busybox", mode=0o777),
                           _entry("app", kind=tarfile.DIRTYPE), _entry("app/start", data=CACHE_START),
                           _entry("tmp", kind=tarfile.DIRTYPE, mode=0o1777)):
            tar.addfile(info, data)
    blob = layer.getvalue()
    diff = hashlib.sha256(blob).hexdigest()
    config = json.dumps({
        "architecture": "amd64", "os": "linux", "created": "2026-01-01T00:00:00Z",
        "config": {"Entrypoint": ["/app/start"], "WorkingDir": "/"},
        "rootfs": {"type": "layers", "diff_ids": [f"sha256:{diff}"]},
        "history": [{"created": "2026-01-01T00:00:00Z", "created_by": "fde module 08"}],
    }, sort_keys=True).encode()
    name = hashlib.sha256(config).hexdigest()
    manifest = json.dumps([{"Config": f"{name}.json", "RepoTags": [IMAGE_TAG], "Layers": [f"{diff}/layer.tar"]}])
    with tarfile.open(out, "w", format=tarfile.USTAR_FORMAT) as tar:
        for path, data in ((f"{diff}/layer.tar", blob), (f"{name}.json", config), ("manifest.json", manifest.encode())):
            info, handle = _entry(path, data=data, mode=0o644)
            tar.addfile(info, handle)


def sh(m: fdekit.VM, cmd: str, timeout: float = 60, *, user: str = "fde") -> subprocess.CompletedProcess:
    if user != "fde":
        cmd = f"sudo -n -u {user} -H sh -c {shlex.quote(cmd)}"
    for attempt in range(3):
        try:
            done = m.ssh(cmd, timeout=timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")
        if done.returncode != 255 or attempt == 2:
            return done
        time.sleep(2)
    return done


def must(m: fdekit.VM, cmd: str, what: str, timeout: float = 120) -> str:
    done = sh(m, cmd, timeout=timeout)
    assert done.returncode == 0, f"Test không dựng được {what}:\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}"
    return done.stdout


class Customer:
    """Máy khách lab-open đang chạy docbridge (service systemd) và docbridge-cache (container), secret mới mỗi lượt."""

    def __init__(self, m: fdekit.VM, work: Path) -> None:
        self.m = m
        self.work = work
        self.secrets: dict[str, str] = {}
        self.seen: dict[str, str] = {}
        self.values: dict[str, str] = {}

    def install(self) -> None:
        build_image(self.work / "cache-image.tar")
        self.m.put(self.work / "cache-image.tar", "/home/fde/cache-image.tar")
        (self.work / "docbridge.py").write_text(SERVICE)
        self.m.put(self.work / "docbridge.py", "/home/fde/docbridge.py")
        must(self.m, "set -e; docker load -q -i ~/cache-image.tar >/dev/null; rm ~/cache-image.tar; "
                     "sudo -n useradd --system --user-group --home-dir /var/lib/docbridge --shell /usr/sbin/nologin "
                     "docbridge; sudo -n useradd --create-home --shell /bin/sh support; "
                     "sudo -n usermod -aG docker,adm,systemd-journal,docbridge support; "
                     "sudo -n install -d -o root -g docbridge -m 0750 /etc/docbridge /etc/docbridge/tls; "
                     "sudo -n install -d -o docbridge -g docbridge -m 0750 /var/log/docbridge /var/lib/docbridge "
                     "/var/lib/docbridge/data; "
                     "sudo -n install -o root -g root -m 0755 ~/docbridge.py /opt/docbridge.py; rm ~/docbridge.py",
             "user/thư mục của docbridge")

    def write_root(self, path: str, content: str, *, owner: str, mode: str) -> None:
        local = self.work / "payload"
        local.write_text(content)
        self.m.put(local, "/home/fde/payload")
        must(self.m, f"sudo -n install -o {owner} -m {mode} /home/fde/payload {shlex.quote(path)} && rm ~/payload",
             path)

    def round(self, *, docker_access: bool) -> None:
        s = {name: secret(prefix) for name, prefix in (
            ("conf_password", "Pw"), ("conf_token", "Tk"), ("conf_proxy", "Px"), ("unit_env", "Sm"),
            ("journal_dsn", "Dj"), ("log_url", "Ul"), ("log_bearer", "Br"), ("log_basic", "Bs"), ("tls_key", "Ky"),
            ("docker_env", "Ca"), ("docker_log", "Rd"), ("data", "Hs"))}
        self.secrets = s
        self.seen.update({f"{name} ({len(self.seen) // len(s) + 1})": value for name, value in s.items()})
        port = str(20000 + secrets.randbelow(9000))
        self.values = {"port": port, "batch": str(10 + secrets.randbelow(490)), "cache_size": str(secrets.randbelow(900) + 64),
                       "journal_marker": secrets.token_hex(8), "log_marker": secrets.token_hex(8),
                       "docker_marker": secrets.token_hex(8), "log_tail_marker": secrets.token_hex(8)}
        v = self.values
        conf = (f"# docbridge: đồng bộ hồ sơ ERP -> quillo\nerp_host=10.20.0.5\nlisten_port={port}\nbatch_size={v['batch']}\n"
                f"erp_password={s['conf_password']}\nquillo_url=https://quillo.nhamay.local\n"
                f"quillo_token={s['conf_token']}\nproxy=http://proxyuser:{s['conf_proxy']}@10.20.0.1:3128\n")
        self.conf = conf
        self.write_root("/etc/docbridge/docbridge.conf", conf, owner="root -g docbridge", mode="0640")
        self.write_root("/etc/docbridge/tls/client.key",
                        f"-----BEGIN PRIVATE KEY-----\n{s['tls_key']}\n-----END PRIVATE KEY-----\n",
                        owner="root -g docbridge", mode="0640")
        unit = ("[Unit]\nDescription=docbridge ERP -> quillo\n\n[Service]\nUser=docbridge\n"
                f"Environment=DOCBRIDGE_SMTP_PASSWORD={s['unit_env']}\n"
                f"Environment=DOCBRIDGE_ERP_DSN=postgresql://erp_reader:{s['journal_dsn']}@10.20.0.5:5432/erp\n"
                f"Environment=DOCBRIDGE_MARKER={v['journal_marker']}\n"
                "ExecStart=/usr/bin/python3 /opt/docbridge.py\nRestart=on-failure\n\n[Install]\nWantedBy=multi-user.target\n")
        self.write_root("/etc/systemd/system/docbridge.service", unit, owner="root -g root", mode="0644")
        self.write_root(f"/var/lib/docbridge/data/HS-{secrets.token_hex(3)}.txt",
                        f"Hồ sơ nhân sự (dữ liệu nghiệp vụ, không được rời máy): {s['data']}\n",
                        owner="docbridge -g docbridge", mode="0640")
        generator = (
            "import random, sys\n"
            "r = random.Random()\n"
            "w = sys.stdout.write\n"
            "for i in range(260000):\n"
            "    w(f'2026-11-10T{(i // 10800) % 24:02d}:{(i // 180) % 60:02d}:{(i // 3) % 60:02d} INFO sync batch={i} "
            "records={r.randint(1, 500)} ms={r.randint(5, 900)}\\n')\n"
            f"    if i == 120000: w('2026-11-10T11:06:40 WARN upstream https://svc-sync:{s['log_url']}@files.nhamay.local/api "
            "tra 503, thu lai\\n')\n"
            f"w('2026-11-10T23:59:58 WARN upstream https://svc-sync:{s['log_url']}@files.nhamay.local/api tra 503\\n')\n"
            f"w('2026-11-10T23:59:59 ERROR quillo tu choi: Authorization: Bearer {s['log_bearer']} (401)\\n')\n"
            f"w('2026-11-10T23:59:59 WARN erp gateway: Authorization: Basic {s['log_basic']} (403)\\n')\n"
            f"w('2026-11-11T00:00:00 INFO marker {v['log_tail_marker']}\\n')\n")
        (self.work / "gen.py").write_text(generator)
        self.m.put(self.work / "gen.py", "/home/fde/gen.py")
        must(self.m, "python3 ~/gen.py > ~/docbridge.log && sudo -n install -o docbridge -g docbridge -m 0640 "
                     "~/docbridge.log /var/log/docbridge/docbridge.log && rm ~/gen.py ~/docbridge.log",
             "log của docbridge")
        must(self.m, "sudo -n systemctl daemon-reload && sudo -n systemctl restart docbridge && "
                     f"for i in $(seq 30); do ss -ltn | grep -q ':{port} ' && break; sleep 1; done; "
                     f"ss -ltn | grep -q ':{port} '", "service docbridge")
        must(self.m, "docker rm -f docbridge-cache >/dev/null 2>&1; docker run -d --name docbridge-cache "
                     f"--restart unless-stopped -e CACHE_SIZE_MB={v['cache_size']} "
                     f"-e CACHE_ADMIN_PASSWORD={s['docker_env']} -e CACHE_UPSTREAM_PASSWORD={s['docker_log']} "
                     f"-e CACHE_MARKER={v['docker_marker']} {IMAGE_TAG} >/dev/null && sleep 2 && "
                     "docker logs docbridge-cache 2>&1 | grep -q marker", "container docbridge-cache")
        group = "docker" if docker_access else ""
        must(self.m, f"sudo -n usermod -G adm,systemd-journal,docbridge{',' + group if group else ''} support",
             "nhóm của support")
        done = sh(self.m, "sudo -n true", user="support")
        assert done.returncode != 0, "support không được có sudo"

    def run_bundle(self, label: str) -> tuple[dict[str, bytes], int]:
        self.m.put(ex.path("support_bundle.sh"), "/home/fde/support_bundle.sh")
        must(self.m, "sudo -n rm -rf /home/support/out /home/support/support_bundle.sh && "
                     "sudo -n install -d -o support -g support -m 0700 /home/support/out && "
                     "sudo -n install -o support -g support -m 0644 ~/support_bundle.sh /home/support/ && "
                     "rm ~/support_bundle.sh && sleep 1 && sudo -n -u support touch /home/support/.stamp", "script")
        run = sh(self.m, f"cd /home/support && timeout {RUN_TIMEOUT} sh support_bundle.sh /home/support/out/bundle.tar.gz",
                 timeout=RUN_TIMEOUT + 30, user="support")
        assert run.returncode != 124, f"{label}: support_bundle.sh chạy quá {RUN_TIMEOUT} s"
        assert run.returncode == 0, (f"{label}: support_bundle.sh phải thoát 0, thoát {run.returncode}\n"
                                     f"stdout:\n{run.stdout[-1500:]}\nstderr:\n{run.stderr[-2000:]}")
        extra = sh(self.m, "find /tmp /var/tmp /dev/shm /home/support -mindepth 1 -user support -newer /home/support/.stamp "
                           "! -path /home/support/out ! -path /home/support/out/bundle.tar.gz 2>/dev/null",
                   user="support").stdout.split()
        assert not extra, f"{label}: script để lại tệp/thư mục ngoài bundle: {extra[:10]}"
        listing = sh(self.m, "ls -A /home/support/out", user="support").stdout.split()
        assert listing == ["bundle.tar.gz"], f"{label}: thư mục ra chỉ được có bundle.tar.gz, có {listing}"
        local = self.work / f"bundle-{len(list(self.work.glob('bundle-*')))}.tar.gz"
        must(self.m, "sudo -n install -o fde -m 0600 /home/support/out/bundle.tar.gz ~/bundle.tar.gz", "bản sao bundle")
        self.m.get("/home/fde/bundle.tar.gz", local)
        sh(self.m, "rm -f ~/bundle.tar.gz")
        size = local.stat().st_size
        assert size <= MAX_BUNDLE, f"{label}: bundle {size} byte, vượt giới hạn {MAX_BUNDLE}"
        return read_bundle(local, label), size


def read_bundle(path: Path, label: str) -> dict[str, bytes]:
    try:
        tar = tarfile.open(path, "r:gz")
    except (tarfile.TarError, OSError) as error:
        pytest.fail(f"{label}: bundle không phải tar.gz đọc được: {error}")
    files: dict[str, bytes] = {}
    roots = set()
    with tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts
            assert parts and not Path(member.name).is_absolute() and ".." not in parts, \
                f"{label}: đường dẫn lạ trong bundle: {member.name}"
            roots.add(parts[0])
            assert member.isfile() or member.isdir(), f"{label}: bundle chỉ chứa tệp thường và thư mục: {member.name}"
            if member.isfile():
                assert len(parts) >= 2, f"{label}: mọi tệp phải nằm dưới một thư mục gốc: {member.name}"
                files["/".join(parts[1:])] = tar.extractfile(member).read()
    assert len(roots) == 1, f"{label}: bundle phải có đúng một thư mục gốc, có {sorted(roots)}"
    return files


def text(files: dict[str, bytes], name: str, label: str) -> str:
    assert name in files, f"{label}: thiếu {name} trong bundle (có {sorted(files)})"
    return files[name].decode("utf-8", errors="replace")


def check_no_leak(files: dict[str, bytes], customer: Customer, label: str) -> None:
    for name, data in files.items():
        assert b"\0" not in data, f"{label}: {name} không phải tệp văn bản (có byte NUL / archive lồng)"
        assert not data.startswith((b"\x1f\x8b", b"PK\x03\x04", b"\xfd7zXZ", b"BZh")), f"{label}: {name} là archive lồng"
        assert b"PRIVATE KEY" not in data, f"{label}: {name} chứa private key"
        for kind, value in customer.seen.items():
            for start in range(len(value) - LEAK_WINDOW + 1):
                piece = value[start:start + LEAK_WINDOW].encode()
                assert piece not in data, (f"{label}: secret gieo ngẫu nhiên ({kind}) lộ trong {name} "
                                           f"(đoạn {LEAK_WINDOW} ký tự liên tiếp)")


def check_required(files: dict[str, bytes], customer: Customer, label: str, *, docker_access: bool) -> None:
    m, v, s = customer.m, customer.values, customer.secrets
    for name in REQUIRED:
        text(files, name, label)
    assert text(files, "system/os-release", label) == must(m, "cat /etc/os-release", "os-release"), \
        f"{label}: system/os-release phải là nguyên nội dung /etc/os-release"
    assert must(m, "uname -r", "uname").strip() in text(files, "system/uname.txt", label), \
        f"{label}: system/uname.txt thiếu phiên bản kernel"
    assert any(line.rstrip().endswith(" /") for line in text(files, "system/df.txt", label).splitlines()), \
        f"{label}: system/df.txt thiếu dòng của filesystem gốc /"
    assert "Mem:" in text(files, "system/memory.txt", label), f"{label}: system/memory.txt không phải output free"
    assert "load average" in text(files, "system/uptime.txt", label), f"{label}: system/uptime.txt không phải uptime"
    assert f":{v['port']} " in text(files, "network/listen.txt", label), \
        f"{label}: network/listen.txt không có cổng docbridge đang nghe ({v['port']})"
    assert "10.0.2.15" in text(files, "network/ip.txt", label), f"{label}: network/ip.txt thiếu địa chỉ của máy"
    status = text(files, "docbridge/status.txt", label)
    assert "docbridge.service" in status and "active (running)" in status, \
        f"{label}: docbridge/status.txt phải là trạng thái systemd của docbridge (đang chạy)"
    journal = text(files, "docbridge/journal.txt", label)
    assert v["journal_marker"] in journal, f"{label}: docbridge/journal.txt thiếu các dòng journal mới nhất của unit"
    assert "@10.20.0.5:5432/erp" in journal, \
        f"{label}: docbridge/journal.txt phải giữ dòng có DSN (che mật khẩu, giữ phần host), không xoá cả dòng"
    conf = text(files, "docbridge/docbridge.conf", label).splitlines()
    for line in customer.conf.splitlines():
        key = line.split("=", 1)[0]
        if line.startswith("#") or key in ("erp_host", "listen_port", "batch_size", "quillo_url"):
            assert line in conf, f"{label}: docbridge/docbridge.conf phải giữ nguyên dòng không chứa secret: {line!r}"
        elif key in ("erp_password", "quillo_token"):
            assert any(c.startswith(key + "=") for c in conf), \
                f"{label}: docbridge/docbridge.conf phải giữ khoá {key} (che giá trị), không xoá dòng"
    assert any(c.startswith("proxy=") and "@10.20.0.1:3128" in c for c in conf), \
        f"{label}: docbridge/docbridge.conf phải giữ dòng proxy= với phần host (che userinfo)"
    app = files["docbridge/docbridge.log"]
    assert len(app) <= MAX_APP_LOG, f"{label}: docbridge/docbridge.log {len(app)} byte, vượt {MAX_APP_LOG}"
    app_text = app.decode("utf-8", errors="replace")
    assert len(app_text.splitlines()) >= MIN_APP_LOG_LINES, \
        f"{label}: docbridge/docbridge.log cần ít nhất {MIN_APP_LOG_LINES} dòng cuối của log"
    assert app_text.rstrip().endswith(f"marker {v['log_tail_marker']}"), \
        f"{label}: docbridge/docbridge.log phải kết thúc bằng dòng cuối cùng hiện tại của log ứng dụng"
    assert "@files.nhamay.local/api tra 503" in app_text, \
        f"{label}: docbridge/docbridge.log phải giữ dòng có URL upstream (che userinfo), không xoá dòng"
    assert "Authorization: Basic" in app_text and "(403)" in app_text, \
        f"{label}: docbridge/docbridge.log phải giữ dòng Authorization Basic (che credential), không xoá dòng"
    assert "Authorization: Bearer" in app_text and "(401)" in app_text, \
        f"{label}: docbridge/docbridge.log phải giữ dòng Authorization (che token), không xoá dòng"
    if not docker_access:
        assert "docker" in text(files, "errors.txt", label).lower(), \
            f"{label}: user không vào được Docker thì errors.txt phải ghi lệnh docker nào đã lỗi"
        return
    for name in DOCKER_ITEMS:
        text(files, name, label)
    assert "docbridge-cache" in text(files, "docker/ps.txt", label), f"{label}: docker/ps.txt thiếu docbridge-cache"
    cache_log = text(files, "docker/docbridge-cache.log", label)
    assert f"marker {v['docker_marker']}" in cache_log and "@10.20.0.7:6379/0" in cache_log, \
        f"{label}: docker/docbridge-cache.log phải có log của container (giữ dòng upstream, che mật khẩu)"
    try:
        inspected = json.loads(text(files, "docker/docbridge-cache.json", label))
    except json.JSONDecodeError as error:
        pytest.fail(f"{label}: docker/docbridge-cache.json không phải JSON hợp lệ: {error}")
    item = inspected[0] if isinstance(inspected, list) and inspected else inspected
    env = (item.get("Config") or {}).get("Env") if isinstance(item, dict) else None
    assert isinstance(env, list), f"{label}: docker/docbridge-cache.json phải là output docker inspect (có Config.Env)"
    assert f"CACHE_SIZE_MB={v['cache_size']}" in env, f"{label}: Config.Env phải giữ nguyên biến không phải secret"
    assert any(e.startswith("CACHE_ADMIN_PASSWORD=") for e in env), \
        f"{label}: Config.Env phải giữ tên biến chứa secret (che giá trị), không xoá biến"


def test_support_bundle_no_planted_secret(tmp_path):
    require_busybox()
    with fdekit.vm("lab-open") as m:
        customer = Customer(m, tmp_path)
        customer.install()
        for label, docker_access in (("lượt 1", True), ("lượt 2 (support không vào được Docker)", False)):
            customer.round(docker_access=docker_access)
            files, _ = customer.run_bundle(label)
            check_no_leak(files, customer, label)
            check_required(files, customer, label, docker_access=docker_access)
