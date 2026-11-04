import json
import shlex
import socket
import subprocess

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
PROXY = "http://10.0.2.100:3128"
IMAGE = "hello-world@sha256:c567b231f65614688711a75f31518a064258a51d442117a3e771a3a8fdba78ef"
RUN_TIMEOUT = 120
LOCAL_PORT = 18099
NO_PROXY_NEEDED = {"localhost", "127.0.0.1", ".benhvien.internal"}
KEYS = ("http_proxy", "https_proxy", "no_proxy", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY")


def sh(m, cmd: str, timeout: float) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s (treo? chờ mạng?): {cmd[:150]}")


def require_internet() -> None:
    for host in ("archive.ubuntu.com", "registry-1.docker.io", "pypi.org"):
        try:
            socket.create_connection((host, 443), timeout=5).close()
        except OSError:
            pytest.skip(f"Proxy của lab (mitmproxy trên máy bạn) cần máy bạn ra được internet; không tới được {host}")


def configure(m) -> subprocess.CompletedProcess:
    try:
        return m.ssh(f"sudo -n sh /home/fde/configure_proxy.sh {PROXY} /home/fde/proxy-ca.pem", timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        pytest.fail(f"configure_proxy.sh chạy quá {RUN_TIMEOUT} s")


def login_env(m) -> dict[str, str]:
    out = sh(m, "env", timeout=30).stdout
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def test_proxy_for_shell_apt_docker():
    require_internet()
    with fdekit.customer_site("hospital") as s:
        m = s.vm
        m.put(s.proxy_ca, "/home/fde/proxy-ca.pem")
        m.put(ex.path("configure_proxy.sh"), "/home/fde/configure_proxy.sh")
        for attempt in ("lần 1", "lần 2"):
            run = configure(m)
            assert run.returncode == 0, (
                f"configure_proxy.sh ({attempt}) thoát mã {run.returncode}\nstdout:\n{run.stdout[-1500:]}\n"
                f"stderr:\n{run.stderr[-1500:]}")

        environment = sh(m, "cat /etc/environment", timeout=30).stdout.splitlines()
        for key in KEYS:
            count = sum(1 for line in environment if line.startswith(f"{key}="))
            assert count == 1, f"/etc/environment có {count} dòng {key}= sau hai lần chạy (cần đúng 1)"
        env = login_env(m)
        for key in KEYS[:2] + KEYS[3:5]:
            assert env.get(key, "").strip('"') == PROXY, f"Shell đăng nhập mới có {key}={env.get(key)!r}, cần {PROXY}"
        for key in ("no_proxy", "NO_PROXY"):
            entries = {e.strip() for e in env.get(key, "").strip('"').split(",")}
            missing = NO_PROXY_NEEDED - entries
            assert not missing, f"{key} của shell thiếu {sorted(missing)}"
        assert "PYTHONHTTPSVERIFY" not in env, "Không được tắt kiểm chứng chỉ (PYTHONHTTPSVERIFY)"

        curl = sh(m, "curl -q -fsS -o /dev/null -w '%{http_code}' https://pypi.org/simple/pip/", timeout=60)
        assert curl.returncode == 0, f"curl https://pypi.org trong shell lỗi:\n{curl.stderr[-800:]}"
        py = sh(m, "python3 -c \"import urllib.request; print(urllib.request.urlopen("
                   "'https://pypi.org/simple/pip/', timeout=30).status)\"", timeout=60)
        assert py.returncode == 0 and py.stdout.strip() == "200", f"Python (urllib) tới https://pypi.org lỗi:\n{py.stderr[-800:]}"

        local = sh(m, f"cd /etc && (python3 -m http.server {LOCAL_PORT} --bind 10.0.2.15 >/dev/null 2>&1 & "
                      f"pid=$!; rc=1; for i in 1 2 3 4 5 6 7 8 9 10; do sleep 1; "
                      f"curl -q -fsS -o /dev/null http://10.0.2.15:{LOCAL_PORT}/hostname && {{ rc=0; break; }}; done; "
                      f"kill $pid; exit $rc)", timeout=60)
        assert local.returncode == 0, (
            f"curl http://10.0.2.15:{LOCAL_PORT} (dịch vụ nội bộ trên chính máy này) không tới được:\n"
            f"{local.stderr[-800:]}")

        apt = sh(m, "sudo -n apt-get update", timeout=240)
        bad = [line for line in (apt.stdout + apt.stderr).splitlines() if line.startswith(("Err:", "W:", "E:"))]
        assert apt.returncode == 0 and not bad, (
            f"sudo apt-get update chưa sạch (mã {apt.returncode}):\n" + "\n".join(bad[:15] or [apt.stderr[-800:]]))

        pull = sh(m, f"docker pull {shlex.quote(IMAGE)} && docker run --rm {shlex.quote(IMAGE)}", timeout=180)
        assert pull.returncode == 0 and "Hello from Docker!" in pull.stdout, (
            f"docker pull/run {IMAGE} lỗi:\n{pull.stderr[-1500:]}")
        info = sh(m, "docker info --format '{{json .RegistryConfig}}'", timeout=30)
        registry = json.loads(info.stdout or "{}")
        cidrs = set(registry.get("InsecureRegistryCIDRs") or []) - {"127.0.0.0/8", "::1/128"}
        insecure = sorted(name for name, conf in (registry.get("IndexConfigs") or {}).items() if not conf.get("Secure"))
        assert not cidrs and not insecure, (
            f"Không được tắt TLS của registry (insecure-registries: {sorted(cidrs) + insecure})")
