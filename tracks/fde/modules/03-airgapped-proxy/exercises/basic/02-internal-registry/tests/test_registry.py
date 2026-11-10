import json
import secrets
import shlex
import subprocess
import urllib.request

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
RUN_TIMEOUT = 120
EXISTING = {"log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}, "live-restore": True}
ACCEPT = ", ".join([
    "application/vnd.oci.image.index.v1+json", "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])


def sh(m, cmd: str, timeout: float) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s (treo? chờ mạng?): {cmd[:150]}")


def registry_get(site, path: str) -> tuple[dict, dict]:
    request = urllib.request.Request(f"http://{site.registry_host}{path}", headers={"Accept": ACCEPT})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response), dict(response.headers)


def publish(m, registry: str, target: str) -> subprocess.CompletedProcess:
    try:
        return m.ssh(f"sudo -n sh /home/fde/publish.sh /home/fde/hello.tar {registry} {shlex.quote(target)}",
                     timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        pytest.fail(f"publish.sh chạy quá {RUN_TIMEOUT} s")


def test_push_and_run_from_internal_registry():
    repo = f"tools/hello-{secrets.token_hex(2)}"
    tag = f"r{secrets.token_hex(3)}"
    with fdekit.customer_site("lawfirm-staging") as s:
        m = s.vm
        m.put(ex.fixtures / "hello-amd64.tar", "/home/fde/hello.tar")
        m.put(ex.path("publish.sh"), "/home/fde/publish.sh")
        seed = shlex.quote(json.dumps(EXISTING))
        seeded = sh(m, f"echo {seed} | sudo -n tee /etc/docker/daemon.json >/dev/null && sudo -n systemctl restart docker",
                    timeout=90)
        assert seeded.returncode == 0, f"Lab không ghi được daemon.json của IT: {seeded.stderr[-500:]}"

        for attempt in ("lần 1", "lần 2"):
            run = publish(m, s.registry, f"{repo}:{tag}")
            assert run.returncode == 0, (
                f"publish.sh ({attempt}) thoát mã {run.returncode}\nstdout:\n{run.stdout[-1500:]}\n"
                f"stderr:\n{run.stderr[-1500:]}")

        daemon = json.loads(m.ssh("sudo -n cat /etc/docker/daemon.json", timeout=30, check=True).stdout)
        for key, value in EXISTING.items():
            assert daemon.get(key) == value, f"daemon.json mất/sửa cấu hình có sẵn của IT: {key}={daemon.get(key)!r}"
        assert daemon.get("insecure-registries") in (None, [s.registry]), (
            f"insecure-registries chỉ được chứa đúng registry nội bộ {s.registry}, đang là {daemon.get('insecure-registries')}")
        active = sh(m, "systemctl is-active docker", timeout=30).stdout.strip()
        assert active == "active", f"Docker daemon không chạy sau khi cấu hình ({active})"

        tags, _ = registry_get(s, f"/v2/{repo}/tags/list")
        assert tag in (tags.get("tags") or []), f"Registry nội bộ chưa có {repo}:{tag} (có {tags})"
        _, headers = registry_get(s, f"/v2/{repo}/manifests/{tag}")
        digest = headers.get("Docker-Content-Digest", "")

        ref = f"{s.registry}/{repo}:{tag}"
        sh(m, "docker ps -aq | xargs -r docker rm -f >/dev/null; docker image prune -af >/dev/null", timeout=60)
        left = sh(m, "docker images -q", timeout=30).stdout.strip()
        assert not left, "Test không xoá được image cục bộ để kiểm pull lại từ registry"
        ran = sh(m, f"docker run --rm {shlex.quote(ref)}", timeout=120)
        assert ran.returncode == 0 and "Hello from Docker!" in ran.stdout, (
            f"docker run {ref} trên máy staging lỗi:\n{ran.stderr[-1500:]}")
        digests = sh(m, f"docker image inspect --format '{{{{json .RepoDigests}}}}' {shlex.quote(ref)}", timeout=30)
        assert f"{s.registry}/{repo}@{digest}" in digests.stdout, (
            f"Image chạy không lấy từ registry nội bộ ({digests.stdout.strip()}, registry có {digest})")
