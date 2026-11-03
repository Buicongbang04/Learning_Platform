import subprocess
import time

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
PROFILE = "lab-open"
KEYS = ["os", "user", "docker", "compose", "egress"]
BUDGET_SECONDS = 30


def parse(stdout: str) -> dict[str, str]:
    report = {}
    for line in stdout.splitlines():
        if not line.strip():
            continue
        assert "=" in line, f"Dòng không theo dạng khoá=giá_trị: {line!r}"
        key, value = line.split("=", 1)
        assert key not in report, f"Khoá {key!r} xuất hiện hai lần"
        report[key] = value
    return report


def test_golden_image_is_prepared():
    golden = fdekit.require_golden(PROFILE)
    assert golden.stat().st_size > 100 * 1024 ** 2, f"Golden {golden} quá nhỏ, dựng lại bằng --force"


def run_script(m) -> dict[str, str]:
    started = time.monotonic()
    try:
        result = m.ssh("sh /home/fde/lab_ready.sh", timeout=BUDGET_SECONDS * 2)
    except subprocess.TimeoutExpired:
        pytest.fail(f"lab_ready.sh chạy quá {BUDGET_SECONDS * 2} s mà chưa xong (treo?); đặt timeout cho mọi lệnh mạng")
    elapsed = time.monotonic() - started
    assert result.returncode == 0, f"Script thoát mã {result.returncode}\nstderr:\n{result.stderr}"
    assert elapsed <= BUDGET_SECONDS, f"Script chạy {elapsed:.0f} s, quá {BUDGET_SECONDS} s"
    report = parse(result.stdout)
    assert list(report) == KEYS, f"Cần đúng các khoá theo thứ tự {KEYS}, nhận {list(report)}"
    return report


def test_lab_ready_reports_the_customer_machine():
    script = ex.path("lab_ready.sh")
    facts = fdekit.PROFILES[PROFILE].facts
    with fdekit.vm(PROFILE, memory_mb=1024) as m:
        m.put(script, "/home/fde/lab_ready.sh")
        report = run_script(m)
        server = m.ssh("docker version --format '{{.Server.Version}}'", timeout=30).stdout.strip()
        compose = m.ssh("docker compose version", timeout=30).returncode == 0
        stop = m.ssh("sudo -n systemctl stop docker.socket docker.service", timeout=60)
        assert stop.returncode == 0, f"Không dừng được Docker daemon trong VM: {stop.stderr}"
        stopped = run_script(m)
    assert report["os"] == f"{facts['os_id']}-{facts['os_version']}"
    assert report["user"] == "fde"
    assert server, "Không đọc được phiên bản Docker server trong VM"
    assert report["docker"] == server, f"docker={report['docker']!r}, Docker server trong VM là {server!r}"
    assert report["compose"] == ("yes" if compose else "no")
    assert report["egress"] == facts["egress"]
    assert stopped["docker"] == "missing", f"Daemon đã dừng nhưng script vẫn in docker={stopped['docker']!r}"
    assert stopped["compose"] == "yes", f"Plugin compose vẫn còn khi daemon dừng, script in compose={stopped['compose']!r}"
    assert {k: stopped[k] for k in ("os", "user", "egress")} == {k: report[k] for k in ("os", "user", "egress")}
