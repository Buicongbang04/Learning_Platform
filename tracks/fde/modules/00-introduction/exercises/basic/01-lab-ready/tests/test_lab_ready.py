import time

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


def test_lab_ready_reports_the_customer_machine():
    script = ex.path("lab_ready.sh")
    facts = fdekit.PROFILES[PROFILE].facts
    with fdekit.vm(PROFILE, memory_mb=1024) as m:
        m.put(script, "/home/fde/lab_ready.sh")
        started = time.monotonic()
        result = m.ssh("sh /home/fde/lab_ready.sh", timeout=BUDGET_SECONDS * 2)
        elapsed = time.monotonic() - started
        server = m.ssh("docker version --format '{{.Server.Version}}'", timeout=30).stdout.strip()
        compose = m.ssh("docker compose version", timeout=30).returncode == 0
    assert result.returncode == 0, f"Script thoát mã {result.returncode}\nstderr:\n{result.stderr}"
    assert elapsed <= BUDGET_SECONDS, f"Script chạy {elapsed:.0f} s, quá {BUDGET_SECONDS} s"
    report = parse(result.stdout)
    assert list(report) == KEYS, f"Cần đúng các khoá theo thứ tự {KEYS}, nhận {list(report)}"
    assert report["os"] == f"{facts['os_id']}-{facts['os_version']}"
    assert report["user"] == "fde"
    assert server, "Không đọc được phiên bản Docker server trong VM"
    assert report["docker"] == server, f"docker={report['docker']!r}, Docker server trong VM là {server!r}"
    assert report["compose"] == ("yes" if compose else "no")
    assert report["egress"] == facts["egress"]
