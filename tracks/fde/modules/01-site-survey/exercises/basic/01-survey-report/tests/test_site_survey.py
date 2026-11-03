import json
import subprocess
import time

import jsonschema
import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
REMOTE = "/home/fde/site_survey.sh"
BUDGET_SECONDS = 30
HOSPITAL_MEMORY_MB = 1536
SCHEMA = json.loads((ex.dir / "schema.json").read_text(encoding="utf-8"))
TRUTH = r"""
. /etc/os-release
echo "os_id=$ID"
echo "os_version=$VERSION_ID"
echo "kernel=$(uname -r)"
echo "glibc=$(getconf GNU_LIBC_VERSION | awk '{print $2}')"
echo "cpus=$(nproc)"
echo "mem_kb=$(awk '/^MemTotal/ {print $2}' /proc/meminfo)"
echo "avail_kb=$(df -P -k / | awk 'NR==2 {print $4}')"
echo "proxy=$(grep -h '^https_proxy=' /etc/environment 2>/dev/null | cut -d= -f2 | tr -d '\"')"
"""


def survey(m) -> dict:
    started = time.monotonic()
    try:
        result = m.ssh(f"sh {REMOTE}", timeout=BUDGET_SECONDS * 2)
    except subprocess.TimeoutExpired:
        pytest.fail(f"site_survey.sh chạy quá {BUDGET_SECONDS * 2} s mà chưa xong (treo?); đặt timeout cho mọi lệnh mạng")
    elapsed = time.monotonic() - started
    assert result.returncode == 0, f"site_survey.sh thoát mã {result.returncode}\nstderr:\n{result.stderr}"
    assert elapsed <= BUDGET_SECONDS, f"site_survey.sh chạy {elapsed:.0f} s, quá {BUDGET_SECONDS} s"
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"stdout không phải JSON hợp lệ ({error}):\n{result.stdout}")
    try:
        jsonschema.validate(report, SCHEMA)
    except jsonschema.ValidationError as error:
        pytest.fail(f"JSON không khớp schema.json: {error.message} (ở {list(error.absolute_path)})")
    return report


def measure(m) -> dict:
    result = m.ssh(TRUTH, timeout=60)
    assert result.returncode == 0, result.stderr
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def check(report: dict, truth: dict, facts: dict, *, proxy: str | None, egress: str) -> None:
    for key in ("os_id", "os_version", "glibc"):
        assert report[key] == truth[key] == facts[key], f"{key}={report[key]!r}, máy là {truth[key]!r}"
    assert report["kernel_major"] == ".".join(truth["kernel"].split(".")[:2]) == facts["kernel_major"], (
        f"kernel_major={report['kernel_major']!r}, uname -r là {truth['kernel']!r}")
    assert report["cpus"] == int(truth["cpus"])
    mem_mb = int(truth["mem_kb"]) // 1024
    assert abs(report["mem_mb"] - mem_mb) <= 1, f"mem_mb={report['mem_mb']}, MemTotal là {mem_mb} MB"
    free_gb = int(truth["avail_kb"]) / 1024 / 1024
    assert abs(report["disk_free_gb_max"] - free_gb) <= 0.15, (
        f"disk_free_gb_max={report['disk_free_gb_max']}, df / còn trống {free_gb:.2f} GiB")
    assert report["disk_free_gb_max"] <= facts["disk_free_gb_max"] + 0.05
    assert report["gpu"] is None and facts["gpu"] is None, f"VM không có GPU, nhận gpu={report['gpu']!r}"
    assert report["proxy_url"] == proxy, f"proxy_url={report['proxy_url']!r}, cần {proxy!r}"
    for key in ("sudo", "selinux", "runtime"):
        assert report[key] == facts[key], f"{key}={report[key]!r}, cần {facts[key]!r}"
    assert report["egress"] == egress, f"egress={report['egress']!r}, cần {egress!r}"


def test_survey_on_hospital_before_and_after_it_changes():
    script = ex.path("site_survey.sh")
    facts = fdekit.PROFILES["hospital"].facts
    with fdekit.customer_site("hospital", memory_mb=HOSPITAL_MEMORY_MB) as s:
        s.vm.put(script, REMOTE)
        first, first_truth = survey(s.vm), measure(s.vm)
        change = s.vm.ssh("sudo -n sed -i '/_proxy=/d' /etc/environment && fallocate -l 1G /home/fde/backup.img")
        assert change.returncode == 0, f"Không đổi được cấu hình VM: {change.stderr}"
        second, second_truth = survey(s.vm), measure(s.vm)
    check(first, first_truth, facts, proxy=facts["proxy_url"], egress=facts["egress"])
    assert first_truth["proxy"] == facts["proxy_url"]
    check(second, second_truth, facts, proxy=None, egress="none")
    assert first["disk_free_gb_max"] - second["disk_free_gb_max"] >= 0.8, "Đã ghi 1 GiB nhưng disk_free_gb_max không giảm"


def test_survey_on_bank():
    script = ex.path("site_survey.sh")
    facts = fdekit.PROFILES["bank"].facts
    with fdekit.customer_site("bank") as s:
        s.vm.put(script, REMOTE)
        report, truth = survey(s.vm), measure(s.vm)
    check(report, truth, facts, proxy=None, egress=facts["egress"])
    assert 0.8 * facts["mem_mb"] <= report["mem_mb"] <= facts["mem_mb"]
