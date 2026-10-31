import re
import shutil
import subprocess
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
UNITS = ["olist-worker.service", "olist-backup.service", "olist-backup.timer"]
MAX_EXPOSURE = 3.0
SECRET = re.compile(r"(PASSWORD|SECRET|TOKEN|DSN|_KEY)\w*=", re.I)
PARSE_WARNING = re.compile(r"Unknown key|Unknown section|Failed to parse|Invalid|ignoring|Missing '='", re.I)
HARDENING = {
    "NoNewPrivileges": {"yes", "true", "1", "on"},
    "ProtectSystem": {"strict"},
    "ProtectHome": {"yes", "true", "read-only", "tmpfs"},
    "PrivateTmp": {"yes", "true", "1", "on"},
}


def parse_unit(text: str) -> dict[str, dict[str, list[str]]]:
    sections: dict[str, dict[str, list[str]]] = {}
    current = None
    for raw in text.replace("\\\n", " ").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], {})
            continue
        if current is None or "=" not in line:
            sections.setdefault("__invalid__", {}).setdefault("lines", []).append(raw)
            continue
        key, value = line.split("=", 1)
        current.setdefault(key.strip(), []).append(value.strip())
    return sections


@pytest.fixture(scope="module")
def units() -> dict[str, dict]:
    return {name: parse_unit(ex.read(name)) for name in UNITS}


def last(unit: dict, section: str, key: str) -> str | None:
    values = unit.get(section, {}).get(key)
    return values[-1] if values else None


def seconds(value: str | None) -> float:
    assert value, "Thiếu giá trị thời gian"
    total = 0.0
    for number, suffix in re.findall(r"(\d+(?:\.\d+)?)\s*(ms|min|s|m|h)?", value):
        total += float(number) * {"ms": 0.001, "min": 60, "m": 60, "h": 3600}.get(suffix, 1)
    return total


def test_no_todo_left(units):
    for name in UNITS:
        assert "TODO" not in ex.read(name), name
        assert "__invalid__" not in units[name], f"{name}: dòng không phải [Section] hay Key=Value: {units[name].get('__invalid__')}"


@pytest.mark.parametrize("name", ["olist-worker.service", "olist-backup.service"])
def test_runs_as_unprivileged_user_with_hardening(units, name):
    unit = units[name]
    assert last(unit, "Service", "User") == "olist", f"{name}: chạy bằng User=olist, không phải root"
    for key, allowed in HARDENING.items():
        assert last(unit, "Service", key) in allowed, f"{name}: thiếu hoặc sai {key}= (chấp nhận {sorted(allowed)})"
    assert last(unit, "Service", "CapabilityBoundingSet") == "", f"{name}: bỏ mọi capability bằng 'CapabilityBoundingSet=' rỗng"
    exec_start = last(unit, "Service", "ExecStart") or ""
    assert exec_start.lstrip("-@:+!").startswith("/"), f"{name}: ExecStart phải dùng đường dẫn tuyệt đối"


@pytest.mark.parametrize("name", ["olist-worker.service", "olist-backup.service"])
def test_secrets_not_inline(units, name):
    unit = units[name]
    env = unit.get("Service", {}).get("Environment", [])
    assert not [e for e in env if SECRET.search(e)], f"{name}: bí mật để trong EnvironmentFile=, không viết vào unit"
    assert last(unit, "Service", "EnvironmentFile"), f"{name}: đọc cấu hình từ EnvironmentFile="


def test_worker_restart_policy(units):
    unit = units["olist-worker.service"]
    assert last(unit, "Service", "Restart") == "on-failure"
    assert seconds(last(unit, "Service", "RestartSec")) >= 1, "RestartSec >= 1 giây để không quay vòng sát nhau"
    assert last(unit, "Unit", "StartLimitIntervalSec"), "Đặt StartLimitIntervalSec trong [Unit]"
    assert last(unit, "Unit", "StartLimitBurst"), "Đặt StartLimitBurst trong [Unit]"
    assert 0 < seconds(last(unit, "Service", "TimeoutStopSec")) <= 60, "TimeoutStopSec trong khoảng (0, 60] giây"


def test_worker_ordering_and_install(units):
    unit = units["olist-worker.service"]
    after = " ".join(unit.get("Unit", {}).get("After", [])).split()
    wants = " ".join(unit.get("Unit", {}).get("Wants", [])).split()
    assert "network-online.target" in after and "network-online.target" in wants, (
        "Worker cần mạng thật: After= và Wants=network-online.target"
    )
    assert last(unit, "Install", "WantedBy") == "multi-user.target"
    assert last(unit, "Service", "MemoryMax"), "Giới hạn bộ nhớ bằng MemoryMax="
    assert last(unit, "Service", "StateDirectory") or last(unit, "Service", "ReadWritePaths"), (
        "ProtectSystem=strict làm mọi thứ chỉ đọc: khai báo StateDirectory= hoặc ReadWritePaths="
    )


def test_backup_is_oneshot_low_priority_without_install(units):
    unit = units["olist-backup.service"]
    assert last(unit, "Service", "Type") == "oneshot"
    assert int(last(unit, "Service", "Nice") or 0) >= 10, "Backup chạy Nice >= 10"
    assert last(unit, "Service", "IOSchedulingClass") in {"idle", "best-effort"}
    assert last(unit, "Service", "Restart") in (None, "no", "on-failure")
    assert "Install" not in unit, "Service do timer kích hoạt không cần [Install]; enable timer chứ không enable service"
    assert last(unit, "Service", "ReadWritePaths"), "Khai báo thư mục ghi bản backup bằng ReadWritePaths="


def test_backup_timer(units):
    timer = units["olist-backup.timer"]
    assert last(timer, "Timer", "OnCalendar"), "Cần OnCalendar="
    assert last(timer, "Timer", "Persistent") in {"yes", "true"}, "Persistent=true để chạy bù khi máy tắt đúng giờ hẹn"
    assert seconds(last(timer, "Timer", "RandomizedDelaySec")) > 0, "Rải giờ chạy bằng RandomizedDelaySec="
    assert last(timer, "Timer", "Unit") in (None, "olist-backup.service")
    assert last(timer, "Install", "WantedBy") == "timers.target"


@pytest.fixture(scope="module")
def staged(tmp_path_factory) -> Path:
    """Chép unit sang thư mục tạm, thay chương trình trong Exec*= bằng một tệp thực thi giả."""
    if not shutil.which("systemd-analyze"):
        pytest.skip("Máy không có systemd-analyze (không phải Linux dùng systemd)")
    root = tmp_path_factory.mktemp("units")
    fake = root / "fake-exec"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    for name in UNITS:
        text = re.sub(
            r"^(Exec\w+=[-@:+!]*)(\S+)", lambda m: m.group(1) + str(fake), ex.read(name), flags=re.M
        )
        (root / name).write_text(text)
    return root


def test_systemd_analyze_verify(staged):
    result = subprocess.run(
        ["systemd-analyze", "verify", "--man=no", *(str(staged / n) for n in UNITS)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=staged,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    warnings = [line for line in output.splitlines() if PARSE_WARNING.search(line)]
    assert not warnings, "systemd bỏ qua dòng sai:\n" + "\n".join(warnings)


@pytest.mark.parametrize("name", ["olist-worker.service", "olist-backup.service"])
def test_security_exposure(staged, name):
    result = subprocess.run(
        ["systemd-analyze", "security", "--offline=yes", "--no-pager", str(staged / name)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=staged,
    )
    match = re.search(r"Overall exposure level for \S+: (\d+(?:\.\d+)?)", result.stdout + result.stderr)
    if not match:
        pytest.skip("systemd-analyze security --offline cần systemd >= 250")
    assert float(match.group(1)) <= MAX_EXPOSURE, (
        f"{name}: exposure {match.group(1)} > {MAX_EXPOSURE}. Xem bảng ✗ của 'systemd-analyze security --offline=yes'"
    )
