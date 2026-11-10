import json
import random
import subprocess
import tarfile
import time

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
REMOTE = "/home/fde/support_bundle.sh"
OUT = "/tmp/sb-out"
BUDGET_SECONDS = 60
FILES = (
    "summary.json", "os-release.txt", "uname.txt", "meminfo.txt", "disk.txt", "net.txt", "dns.txt", "listening.txt",
    "runtime.txt", "security.txt", "kernel.txt", "time.txt", "limits.txt",
)
TRUTH = r"""
. /etc/os-release
echo "os=$ID-$VERSION_ID"
echo "kernel=$(uname -r)"
echo "mem_kb=$(awk '/^MemTotal/ {print $2}' /proc/meminfo)"
if command -v docker >/dev/null; then
    echo "runtime=docker $(docker version --format '{{.Server.Version}}')"
else
    echo "runtime=podman $(podman version --format '{{.Client.Version}}')"
fi
conf=/run/systemd/resolve/resolv.conf
[ -r "$conf" ] || conf=/etc/resolv.conf
echo "dns=$(awk '$1 == "nameserver" {print $2}' "$conf" | sort -u | tr '\n' ' ')"
"""


def collect(m, tmp_path, name: str) -> tuple[dict, dict]:
    started = time.monotonic()
    try:
        result = m.ssh(f"sh {REMOTE} {OUT}", timeout=BUDGET_SECONDS * 2)
    except subprocess.TimeoutExpired:
        pytest.fail(f"[{name}] support_bundle.sh chạy quá {BUDGET_SECONDS * 2} s mà chưa xong (treo?)")
    elapsed = time.monotonic() - started
    assert result.returncode == 0, (
        f"[{name}] support_bundle.sh thoát mã {result.returncode}. Output khách thấy:\n{result.stdout}{result.stderr}")
    assert elapsed <= BUDGET_SECONDS, f"[{name}] support_bundle.sh chạy {elapsed:.0f} s, quá {BUDGET_SECONDS} s"
    local = tmp_path / f"{name}.tar.gz"
    m.get(f"{OUT}/support-bundle.tar.gz", local)
    truth = m.ssh(TRUTH, timeout=60)
    assert truth.returncode == 0, truth.stderr
    files = {}
    with tarfile.open(local, "r:gz") as tar:
        for member in tar.getmembers():
            assert member.name == "support-bundle" or member.name.startswith("support-bundle/"), (
                f"[{name}] tarball chứa đường dẫn lạ {member.name!r}, mọi thứ phải nằm trong support-bundle/")
            if member.isfile():
                files[member.name.removeprefix("support-bundle/")] = tar.extractfile(member).read().decode("utf-8", "replace")
    return files, dict(line.split("=", 1) for line in truth.stdout.splitlines() if "=" in line)


def check(name: str, files: dict, truth: dict) -> None:
    missing = [f for f in FILES if not files.get(f, "").strip()]
    assert not missing, f"[{name}] thiếu hoặc rỗng trong bundle: {missing}"
    try:
        summary = json.loads(files["summary.json"])
    except json.JSONDecodeError as error:
        pytest.fail(f"[{name}] summary.json không phải JSON hợp lệ: {error}")
    assert set(summary) == {"os", "kernel", "runtime", "dns", "mem_kb"}, f"[{name}] khoá summary.json: {sorted(summary)}"
    for key in ("os", "kernel", "runtime"):
        assert summary[key] == truth[key], f"[{name}] summary {key}={summary[key]!r}, máy là {truth[key]!r}"
    assert summary["mem_kb"] == int(truth["mem_kb"]), f"[{name}] mem_kb={summary['mem_kb']}, MemTotal là {truth['mem_kb']}"
    assert isinstance(summary["dns"], list), f"[{name}] dns phải là danh sách"
    assert "127.0.0.53" not in summary["dns"], f"[{name}] dns là stub resolver 127.0.0.53, cần DNS server thật phía sau"
    assert set(summary["dns"]) == set(truth["dns"].split()), f"[{name}] dns={summary['dns']}, máy dùng {truth['dns'].split()}"


def test_bundle_from_lab_open_and_bank(tmp_path):
    script = ex.path("support_bundle.sh")
    results = []
    for name in ("lab-open", "bank"):
        with fdekit.customer_site(name, memory_mb=random.choice((1024, 1280))) as s:
            s.vm.put(script, REMOTE)
            results.append((name, *collect(s.vm, tmp_path, name)))
    for name, files, truth in results:
        check(name, files, truth)
