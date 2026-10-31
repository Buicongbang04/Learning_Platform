import os
import shutil
import subprocess
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Cần bash")
FAKE_SLEEP = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$SLEEP_LOG"
"""
FLAKY = """#!/usr/bin/env bash
n=$(( $(cat "$COUNTER" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$COUNTER"
read -r -a codes <<< "$FLAKY_CODES"
idx=$(( n <= ${#codes[@]} ? n - 1 : ${#codes[@]} - 1 ))
echo "run $n"
exit "${codes[$idx]}"
"""


class Harness:
    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.sleep_log = tmp_path / "sleeps"
        self.counter = tmp_path / "counter"
        self.sleep = tmp_path / "fake_sleep"
        self.sleep.write_text(FAKE_SLEEP)
        self.sleep.chmod(0o755)
        self.flaky = tmp_path / "flaky"
        self.flaky.write_text(FLAKY)
        self.flaky.chmod(0o755)

    def run(self, *args, codes="0"):
        env = {
            **os.environ,
            "RETRY_SLEEP_CMD": str(self.sleep),
            "SLEEP_LOG": str(self.sleep_log),
            "COUNTER": str(self.counter),
            "FLAKY_CODES": codes,
        }
        for path in (self.sleep_log, self.counter):
            path.unlink(missing_ok=True)
        return subprocess.run(
            [BASH, str(ex.path("retry.sh")), *map(str, args)], capture_output=True, text=True, timeout=60, env=env
        )

    def sleeps(self) -> list[str]:
        return self.sleep_log.read_text().split() if self.sleep_log.exists() else []

    def runs(self) -> int:
        return int(self.counter.read_text()) if self.counter.exists() else 0


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


def test_success_first_try(h):
    result = h.run("--", h.flaky, codes="0")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "run 1\n"
    assert h.sleeps() == []
    assert result.stderr == ""


def test_transient_then_success(h):
    result = h.run("--", h.flaky, codes="7 7 0")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "run 1\nrun 2\nrun 3\n"
    assert h.sleeps() == ["1", "2"]
    assert result.stderr.splitlines() == [
        "retry: attempt 1/5 exited 7; sleeping 1s",
        "retry: attempt 2/5 exited 7; sleeping 2s",
    ]


def test_gives_up_after_max_attempts(h):
    result = h.run("-n", 4, "--", h.flaky, codes="75")
    assert result.returncode == 75
    assert h.runs() == 4
    assert h.sleeps() == ["1", "2", "4"]
    assert result.stderr.splitlines()[-1] == "retry: giving up after 4 attempts (exit 75)"


def test_delay_is_capped(h):
    result = h.run("-n", 6, "-d", 2, "-m", 5, "--", h.flaky, codes="28")
    assert result.returncode == 28
    assert h.sleeps() == ["2", "4", "5", "5", "5"]


def test_permanent_failure_is_not_retried(h):
    result = h.run("--", h.flaky, codes="1 0")
    assert result.returncode == 1
    assert h.runs() == 1
    assert h.sleeps() == []
    assert result.stderr.splitlines() == ["retry: exit 1 is not retryable"]


def test_custom_retryable_codes(h):
    result = h.run("-r", "3,9", "--", h.flaky, codes="9 3 0")
    assert result.returncode == 0, result.stderr
    assert h.sleeps() == ["1", "2"]
    result = h.run("-r", "3,9", "--", h.flaky, codes="7 0")
    assert result.returncode == 7
    assert h.runs() == 1


def test_default_codes(h):
    for code in (6, 7, 28, 75):
        result = h.run("-n", 2, "--", h.flaky, codes=f"{code} 0")
        assert result.returncode == 0, f"exit {code} phải được retry mặc định"
    for code in (2, 22, 126):
        result = h.run("-n", 2, "--", h.flaky, codes=f"{code} 0")
        assert result.returncode == code, f"exit {code} không được retry mặc định"


def test_command_not_found_is_not_retried(h):
    result = h.run("--", h.tmp / "khong-co-lenh")
    assert result.returncode == 127
    assert h.sleeps() == []


def test_single_attempt(h):
    result = h.run("-n", 1, "--", h.flaky, codes="7 0")
    assert result.returncode == 7
    assert h.runs() == 1
    assert h.sleeps() == []


def test_arguments_are_preserved(h):
    result = h.run("--", "printf", "[%s]\n", "a b", "", "*", "-n")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "[a b]\n[]\n[*]\n[-n]\n"


def test_works_without_double_dash(h):
    result = h.run("-n", 2, h.flaky, codes="7 0")
    assert result.returncode == 0, result.stderr
    assert h.runs() == 2


def test_full_jitter(h):
    observed = []
    for _ in range(3):
        result = h.run("-j", "-n", 6, "--", h.flaky, codes="7")
        assert result.returncode == 7
        delays = [int(s) for s in h.sleeps()]
        assert len(delays) == 5
        assert all(0 <= d <= cap for d, cap in zip(delays, [1, 2, 4, 8, 16])), delays
        observed.append(delays)
    assert any(d != [1, 2, 4, 8, 16] for d in observed), "Với -j, thời gian chờ phải là số ngẫu nhiên trong [0, mức backoff]"


@pytest.mark.parametrize(
    "args",
    [(), ("-n", 0, "true"), ("-n", "x", "true"), ("-d", "-1", "true"), ("-m", "a", "true"), ("-r", "7,x", "true"), ("-z", "true"), ("-n", 3, "--")],
)
def test_usage_errors(h, args):
    result = h.run(*args)
    assert result.returncode == 64
    assert result.stderr.startswith("Usage:")
    assert result.stdout == ""


def test_shellcheck_clean():
    ex.require_tool("shellcheck", min_version="0.9.0")
    result = subprocess.run(["shellcheck", "-S", "style", str(ex.path("retry.sh"))], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
