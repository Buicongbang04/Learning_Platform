import json
import random
import re
import shlex
import socket
import subprocess
from contextlib import contextmanager

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
FILES = ("Dockerfile", "requirements.txt", "fetch.py", "build.sh", "run.sh")
REQUESTS_PIN = "2.34.2"
BUILD_TIMEOUT = 240
RUN_TIMEOUT = 90
PROXY = "http://10.0.2.100:3128"
TARGETS = [
    ("https://files.pythonhosted.org/packages/58/a2/bb081bab032533a855d44de1d56f8e8426114ff1ba5d1f07a438a0a654f8/"
     "idna-3.20-py3-none-any.whl", "ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c"),
    ("https://files.pythonhosted.org/packages/0b/a7/71ac2cff56fec219ed242bb11b8efb69fcc4bec75db06fb7bfe35de520e6/"
     "certifi-2026.7.22-py3-none-any.whl", "62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775"),
    ("https://files.pythonhosted.org/packages/92/9d/c4e665119135114480843e7ab388fa94d8480650450e6f8e26b70d323a4c/"
     "urllib3-2.8.0-py3-none-any.whl", "0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3"),
    ("https://files.pythonhosted.org/packages/a0/f4/c67b0b3f1b9245e8d266f0f112c500d50e5b4e83cb6f3b71b6528104182a/"
     "requests-2.34.2-py3-none-any.whl", "2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0"),
]
FORBIDDEN = re.compile(r"verify\s*=\s*False|trusted[-_]host|PYTHONHTTPSVERIFY|--insecure|CERT_NONE|"
                       r"check_hostname\s*=\s*False|(?:REQUESTS|CURL)_CA_BUNDLE(?:\s*=\s*|\s+)(?:\"\"|''|(?=\s|$))",
                       re.I | re.M)
IT_SETUP = f"""set -e
sudo -n install -m 0644 /home/fde/proxy-ca.pem /usr/local/share/ca-certificates/benhvien-proxy-ca.crt
sudo -n update-ca-certificates >/dev/null
sudo -n mkdir -p /etc/systemd/system/docker.service.d
printf '[Service]\\nEnvironment="HTTP_PROXY={PROXY}" "HTTPS_PROXY={PROXY}" "NO_PROXY=localhost,127.0.0.1"\\n' \
  | sudo -n tee /etc/systemd/system/docker.service.d/http-proxy.conf >/dev/null
sudo -n systemctl daemon-reload
sudo -n systemctl restart docker
curl -q -fsS -o /dev/null https://pypi.org/simple/requests/
"""
SELF_SIGNED = """cd "$(mktemp -d)"
openssl req -x509 -newkey rsa:2048 -nodes -subj /CN=tu-ky.test -keyout k.pem -out c.pem -days 1 2>/dev/null
openssl s_server -accept 18443 -cert c.pem -key k.pem -www -quiet >/dev/null 2>&1 &
pid=$!
sleep 1
docker run --rm --entrypoint python -e https_proxy= -e HTTPS_PROXY= -e no_proxy='*' -e NO_PROXY='*' fetcher:1 \
  -c "import requests; requests.get('https://10.0.2.15:18443/', timeout=15)"
rc=$?
kill $pid
exit $rc
"""


def sh(m, cmd: str, timeout: float) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s (treo? chờ mạng?): {cmd[:150]}")


def require_internet() -> None:
    for host in ("registry-1.docker.io", "pypi.org", "files.pythonhosted.org"):
        try:
            socket.create_connection((host, 443), timeout=5).close()
        except OSError:
            pytest.skip(f"Bài cần máy bạn ra internet (Docker Hub, PyPI); không tới được {host}")


@contextmanager
def customer(profile: str):
    if profile == "hospital":
        with fdekit.customer_site("hospital") as s:
            s.vm.put(s.proxy_ca, "/home/fde/proxy-ca.pem")
            ready = sh(s.vm, IT_SETUP, timeout=120)
            assert ready.returncode == 0, f"Bước chuẩn bị của IT bệnh viện lỗi (lab):\n{ready.stderr[-1500:]}"
            yield s.vm
    else:
        with fdekit.vm(profile, memory_mb=2048) as m:
            yield m


def test_learner_files_keep_tls_verification():
    for name in FILES:
        text = ex.path(name).read_text(encoding="utf-8")
        found = FORBIDDEN.search(text)
        assert not found, f"{name} tắt kiểm chứng chỉ ({found.group(0)!r}); sửa bằng cách tin đúng CA, không tắt TLS"


@pytest.mark.parametrize("profile", ["lab-open", "hospital"])
def test_build_and_fetch(profile):
    require_internet()
    url, sha256 = random.SystemRandom().choice(TARGETS)
    with customer(profile) as m:
        m.ssh("mkdir -p /home/fde/fetcher", check=True)
        for name in FILES:
            m.put(ex.path(name), f"/home/fde/fetcher/{name}")
        try:
            built = m.ssh("cd /tmp && sh /home/fde/fetcher/build.sh", timeout=BUILD_TIMEOUT)
        except subprocess.TimeoutExpired:
            pytest.fail(f"build.sh chạy quá {BUILD_TIMEOUT} s trên {profile}")
        assert built.returncode == 0, (
            f"build.sh thoát mã {built.returncode} trên {profile}\nstdout:\n{built.stdout[-2500:]}\n"
            f"stderr:\n{built.stderr[-2500:]}")
        try:
            ran = m.ssh(f"cd /tmp && sh /home/fde/fetcher/run.sh {shlex.quote(url)}", timeout=RUN_TIMEOUT)
        except subprocess.TimeoutExpired:
            pytest.fail(f"run.sh chạy quá {RUN_TIMEOUT} s trên {profile}")
        assert ran.returncode == 0, f"run.sh thoát mã {ran.returncode} trên {profile}\nstderr:\n{ran.stderr[-2500:]}"
        lines = [line for line in ran.stdout.splitlines() if line.startswith("{")]
        assert lines, f"run.sh không in JSON kết quả:\n{ran.stdout[-1000:]}"
        result = json.loads(lines[-1])
        assert result.get("sha256") == sha256, f"Nội dung tải về sai sha256: {result}"
        assert result.get("requests") == REQUESTS_PIN, f"Image phải dùng requests {REQUESTS_PIN} đã ghim: {result}"

        strict = sh(m, SELF_SIGNED, timeout=90)
        assert strict.returncode != 0 and "CERTIFICATE_VERIFY_FAILED" in strict.stderr, (
            "Image fetcher:1 chấp nhận cả chứng chỉ tự ký lạ: kiểm chứng chỉ đã bị tắt hoặc tin quá rộng\n"
            f"{strict.stderr[-1000:]}")
