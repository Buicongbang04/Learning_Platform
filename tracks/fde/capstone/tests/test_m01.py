import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

import fdekit
from capstonekit import MEMORY_MB, REQUIREMENTS, frontmatter, need_files, output, vm_sh
from testkit import run_sandboxed

PROFILE = "lawfirm-staging"
SURVEY = "survey/site_survey.sh"
PREFLIGHT = "survey/preflight.py"
REPORT = "reports/site-survey.md"
REMOTE = "/home/fde/site_survey.sh"
BUDGET_SECONDS = 30
KEYS = ("os_id", "os_version", "kernel_major", "glibc", "cpus", "mem_mb", "disk_free_gb_max", "gpu", "proxy_url",
        "sudo", "selinux", "runtime", "egress")
PLANTED_PROXY = "http://10.0.2.100:3128"
TRUTH = r"""
. /etc/os-release
echo "os_id=$ID"
echo "os_version=$VERSION_ID"
echo "kernel=$(uname -r)"
echo "glibc=$(getconf GNU_LIBC_VERSION | awk '{print $2}')"
echo "cpus=$(nproc)"
echo "mem_kb=$(awk '/^MemTotal/ {print $2}' /proc/meminfo)"
echo "avail_kb=$(df -P -k / | awk 'NR==2 {print $4}')"
"""


def staging_facts(mem_mb: int) -> dict:
    """Sự thật của máy staging khi IT cấp `mem_mb` RAM (mặc định của hồ sơ là 2048)."""
    return fdekit.PROFILES[PROFILE].facts | {"mem_mb": mem_mb}


def run_survey(m, env: str = "") -> tuple[dict, str]:
    started = time.monotonic()
    result = vm_sh(m, f"{env}sh {REMOTE}", BUDGET_SECONDS * 2)
    elapsed = time.monotonic() - started
    assert result.returncode == 0, f"{SURVEY} thoát mã {result.returncode}\nstderr:\n{result.stderr[-2000:]}"
    assert elapsed <= BUDGET_SECONDS, f"{SURVEY} chạy {elapsed:.0f} s, quá {BUDGET_SECONDS} s"
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"stdout của {SURVEY} không phải JSON hợp lệ ({error}):\n{result.stdout[:2000]}")
    assert isinstance(report, dict), "Survey phải in một object JSON"
    missing = [key for key in KEYS if key not in report]
    assert not missing, f"Survey thiếu khoá {missing}"
    return report, result.stdout


def measure(m) -> dict:
    result = vm_sh(m, TRUTH, 60)
    assert result.returncode == 0, result.stderr
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def check(report: dict, truth: dict, facts: dict, *, proxy: str | None) -> None:
    for key in ("os_id", "os_version", "glibc"):
        assert report[key] == truth[key] == facts[key], f"{key}={report[key]!r}, máy là {truth[key]!r}"
    assert report["kernel_major"] == ".".join(truth["kernel"].split(".")[:2]) == facts["kernel_major"], (
        f"kernel_major={report['kernel_major']!r}, uname -r là {truth['kernel']!r}")
    assert report["cpus"] == int(truth["cpus"]) == facts["cpus"], f"cpus={report['cpus']!r}"
    mem_mb = int(truth["mem_kb"]) // 1024
    assert isinstance(report["mem_mb"], int) and abs(report["mem_mb"] - mem_mb) <= 1, (
        f"mem_mb={report['mem_mb']!r}, MemTotal là {mem_mb} MB")
    assert 0.8 * facts["mem_mb"] <= report["mem_mb"] <= facts["mem_mb"]
    free_gb = int(truth["avail_kb"]) / 1024 / 1024
    assert abs(report["disk_free_gb_max"] - free_gb) <= 0.15, (
        f"disk_free_gb_max={report['disk_free_gb_max']!r}, df / còn trống {free_gb:.2f} GiB")
    assert report["disk_free_gb_max"] <= facts["disk_free_gb_max"] + 0.05
    assert report["gpu"] is None, f"VM không có GPU, nhận gpu={report['gpu']!r}"
    assert report["proxy_url"] == proxy, f"proxy_url={report['proxy_url']!r}, cần {proxy!r}"
    for key in ("sudo", "selinux", "runtime", "egress"):
        assert report[key] == facts[key], f"{key}={report[key]!r}, cần {facts[key]!r}"


def preflight(capstone: Path, survey: dict, tmp: Path) -> tuple[int, list[dict]]:
    tmp.mkdir(parents=True, exist_ok=True)
    data = tmp / f"survey-{uuid.uuid4().hex[:6]}.json"
    data.write_text(json.dumps(survey), encoding="utf-8")
    try:
        result = run_sandboxed([sys.executable, capstone / PREFLIGHT, data, REQUIREMENTS], writable=[tmp], cwd=tmp,
                               env={}, timeout=30)
    except subprocess.TimeoutExpired:
        pytest.fail(f"{PREFLIGHT} chạy quá 30 s")
    assert result.returncode in (0, 1), f"{PREFLIGHT} thoát mã {result.returncode}\n{output(result)}"
    try:
        findings = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"stdout của {PREFLIGHT} không phải JSON ({error}):\n{result.stdout[:1500]}")
    assert isinstance(findings, list), f"{PREFLIGHT} phải in một danh sách JSON"
    for item in findings:
        assert isinstance(item, dict) and {"check", "severity", "detail"} <= set(item), (
            f"Mỗi phát hiện cần check, severity, detail: {item!r}")
        assert item["severity"] in ("blocker", "warning"), f"severity phải là blocker hoặc warning: {item!r}"
    return result.returncode, findings


def checks(findings: list[dict], severity: str) -> set[str]:
    return {item["check"] for item in findings if item["severity"] == severity}


def test_m01_survey_matches_lawfirm(capstone, tmp_path):
    need_files(capstone, SURVEY, PREFLIGHT)
    facts = staging_facts(MEMORY_MB)
    secret, password = uuid.uuid4().hex, uuid.uuid4().hex
    with fdekit.customer_site(PROFILE, memory_mb=MEMORY_MB) as s:
        s.vm.put(capstone / SURVEY, REMOTE)
        (first, _), first_truth = run_survey(s.vm), measure(s.vm)
        change = vm_sh(s.vm, f"echo 'https_proxy=http://svc:{secret}@10.0.2.100:3128' | sudo -n tee -a /etc/environment")
        assert change.returncode == 0, f"Không đổi được cấu hình VM: {change.stderr}"
        (second, raw), second_truth = run_survey(s.vm, f"QUILLO_DB_PASSWORD={password} "), measure(s.vm)
    check(first, first_truth, facts, proxy=None)
    assert secret not in raw, "Mật khẩu proxy lọt vào output survey; bỏ phần user:pass@ khỏi URL"
    assert password not in raw, "Biến môi trường bí mật lọt vào output survey; không dump môi trường"
    check(second, second_truth, facts, proxy=PLANTED_PROXY)
    code, findings = preflight(capstone, first, tmp_path)
    assert code == 0 and not checks(findings, "blocker"), (
        f"Survey thật của máy staging ({MEMORY_MB} MB) không có blocker, preflight trả: {findings}")
    assert "egress" in checks(findings, "warning"), f"Máy không ra internet mà preflight không cảnh báo egress: {findings}"


def test_m01_preflight_report(capstone, tmp_path):
    need_files(capstone, PREFLIGHT, REPORT)
    code, findings = preflight(capstone, staging_facts(MEMORY_MB), tmp_path)
    assert code == 0, f"Máy staging {MEMORY_MB} MB không có blocker, preflight thoát {code}: {findings}"
    assert not checks(findings, "blocker"), f"Không được có blocker: {findings}"
    assert "egress" in checks(findings, "warning"), f"Thiếu warning egress: {findings}"
    code, findings = preflight(capstone, staging_facts(fdekit.SITE_MEMORY_MB), tmp_path)
    assert code == 1 and "mem" in checks(findings, "blocker"), (
        f"Máy {fdekit.SITE_MEMORY_MB} MB dưới min_mem_mb: cần blocker 'mem' và mã thoát 1, nhận {code}: {findings}")
    data = frontmatter(capstone / REPORT)
    for key in ("blockers", "warnings"):
        assert isinstance(data.get(key), list), f"Frontmatter của {REPORT} cần '{key}' là danh sách"
        for item in data[key]:
            assert isinstance(item, dict) and item.get("check") and item.get("detail"), (
                f"Mỗi mục trong '{key}' cần check và detail: {item!r}")
    assert data["blockers"] == [], f"Máy staging {MEMORY_MB} MB không có blocker, báo cáo ghi: {data['blockers']}"
    assert "egress" in {item["check"] for item in data["warnings"]}, "Báo cáo thiếu warning 'egress'"
