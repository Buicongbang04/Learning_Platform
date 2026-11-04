import json
import shlex
import subprocess
import time
import uuid

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
REMOTE = "/home/fde/storage_report.sh"
BUDGET_SECONDS = 30
KEYS = ["runtime", "data_root", "data_mount", "data_free_gb", "inodes_free_pct"]
MOVE_DOCKER = """
set -e
truncate -s 2G /var/lib/appdata.img
mkfs.ext4 -q /var/lib/appdata.img
mkdir -p /srv/appdata
mount -o loop /var/lib/appdata.img /srv/appdata
printf '{"data-root": "/srv/appdata/docker"}\\n' > /etc/docker/daemon.json
systemctl restart docker
"""


def report(m) -> dict:
    started = time.monotonic()
    try:
        result = m.ssh(f"sh {REMOTE}", timeout=BUDGET_SECONDS * 2)
    except subprocess.TimeoutExpired:
        pytest.fail(f"storage_report.sh chạy quá {BUDGET_SECONDS * 2} s mà chưa xong (treo?)")
    elapsed = time.monotonic() - started
    assert result.returncode == 0, f"storage_report.sh thoát mã {result.returncode}\nstderr:\n{result.stderr}"
    assert elapsed <= BUDGET_SECONDS, f"storage_report.sh chạy {elapsed:.0f} s, quá {BUDGET_SECONDS} s"
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"stdout không phải JSON hợp lệ ({error}):\n{result.stdout}")
    assert isinstance(data, dict) and list(data) == KEYS, f"Cần object JSON đúng các khoá theo thứ tự {KEYS}"
    return data


def truth(m, runtime: str) -> dict:
    query = ("docker info --format '{{.DockerRootDir}}'" if runtime == "docker"
             else "podman info --format '{{.Store.GraphRoot}}'")
    root = m.ssh(query, timeout=60).stdout.strip()
    assert root, f"Không đọc được thư mục dữ liệu của {runtime} trong VM"
    quoted = shlex.quote(root)
    out = m.ssh(f"df -P -k {quoted} | awk 'NR==2 {{print $4, $6}}'; df -P -i {quoted} | awk 'NR==2 {{print $2, $4}}'",
                timeout=30).stdout.split()
    avail_kb, mount, inodes, ifree = out
    return {"runtime": runtime, "data_root": root, "data_mount": mount, "free_gb": int(avail_kb) / 1024 / 1024,
            "ifree_pct": 100 * int(ifree) / int(inodes)}


def check(got: dict, want: dict, label: str) -> None:
    for key in ("runtime", "data_root", "data_mount"):
        assert got[key] == want[key], f"[{label}] {key}={got[key]!r}, máy là {want[key]!r}"
    assert isinstance(got["data_free_gb"], (int, float)), f"[{label}] data_free_gb phải là số"
    assert abs(got["data_free_gb"] - want["free_gb"]) <= 0.05, (
        f"[{label}] data_free_gb={got['data_free_gb']}, chỗ trống thật ở {want['data_root']} là {want['free_gb']:.2f} GiB")
    assert isinstance(got["inodes_free_pct"], int), f"[{label}] inodes_free_pct phải là số nguyên"
    assert abs(got["inodes_free_pct"] - want["ifree_pct"]) <= 1, (
        f"[{label}] inodes_free_pct={got['inodes_free_pct']}, thật là {want['ifree_pct']:.1f}")


def test_docker_data_root_moved_by_it():
    script = ex.path("storage_report.sh")
    with fdekit.vm("lab-open", memory_mb=1024) as m:
        m.put(script, REMOTE)
        before, before_truth = report(m), truth(m, "docker")
        moved = m.ssh(f"sudo -n sh -c {shlex.quote(MOVE_DOCKER)}", timeout=120)
        assert moved.returncode == 0, f"Không chuyển được data-root của Docker trong VM: {moved.stderr}"
        after, after_truth = report(m), truth(m, "docker")
    check(before, before_truth, "trước")
    assert after_truth["data_mount"] == "/srv/appdata"
    check(after, after_truth, "sau khi IT chuyển data-root")


def test_rootless_podman_storage():
    script = ex.path("storage_report.sh")
    store = f"/dev/shm/store-{uuid.uuid4().hex[:8]}"
    conf = f'[storage]\ndriver = "overlay"\ngraphroot = "{store}"\n'
    with fdekit.customer_site("bank", memory_mb=1024) as s:
        s.vm.put(script, REMOTE)
        before, before_truth = report(s.vm), truth(s.vm, "podman")
        moved = s.vm.ssh(f"mkdir -p ~/.config/containers {store} && printf %s {shlex.quote(conf)} > "
                         "~/.config/containers/storage.conf", timeout=30)
        assert moved.returncode == 0, moved.stderr
        after, after_truth = report(s.vm), truth(s.vm, "podman")
    check(before, before_truth, "mặc định")
    assert after_truth["data_root"] == store
    check(after, after_truth, "sau khi đổi graphroot")
