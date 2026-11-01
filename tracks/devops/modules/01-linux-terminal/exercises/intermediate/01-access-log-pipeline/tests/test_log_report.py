import gzip
import shutil
import subprocess
from pathlib import Path

import pytest

from testkit import Exercise, sandbox_command

ex = Exercise(__file__)
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None or shutil.which("awk") is None, reason="Cần bash và awk")
LOG = ex.fixtures / "access.log"
JSONL = ex.fixtures / "access.jsonl"


def sandboxed(cmd: list, tmp: Path, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    """Như testkit.run_sandboxed nhưng giữ stdin/stdout dạng bytes (log có byte lạ)."""
    argv = sandbox_command(cmd, writable=[tmp], cwd=tmp, env={"LC_ALL": "C"})
    return subprocess.run(argv, input=stdin, capture_output=True, timeout=60, env={})


def run(tmp: Path, *args, stdin: bytes | None = None):
    return sandboxed([BASH, ex.path("log_report.sh"), *map(str, args)], tmp, stdin)


def lines(result) -> list[str]:
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    return result.stdout.decode().splitlines()


@pytest.mark.parametrize("args", [(), ("status",), ("bogus", LOG), ("top-ips", LOG), ("slow", LOG)])
def test_usage(tmp_path, args):
    result = run(tmp_path, *args)
    assert result.returncode == 2
    assert result.stderr.decode().startswith("Usage:")
    assert result.stdout == b""


def test_missing_file(tmp_path):
    result = run(tmp_path, "status", tmp_path / "khong-co.log")
    assert result.returncode == 1
    assert result.stderr.strip()


def test_status_counts(tmp_path):
    assert lines(run(tmp_path, "status", LOG)) == [
        "200 435",
        "201 81",
        "304 37",
        "400 2",
        "404 39",
        "500 1",
        "502 7",
        "504 9",
    ]


def test_top_ips_handles_ipv6_and_ties(tmp_path):
    assert lines(run(tmp_path, "top-ips", 4, LOG)) == [
        "77 113.161.72.9",
        "69 14.226.40.18",
        "68 10.0.0.2",
        "51 2001:db8:4f::1f",
    ]
    tie = b"".join(
        f'{ip} - - [28/Oct/2026:10:00:0{i} +0700] "GET / HTTP/1.1" 200 1 "-" "-" rt=0.001\n'.encode()
        for i, ip in enumerate(["10.0.0.9", "10.0.0.10", "10.0.0.9", "10.0.0.10", "10.0.0.8"])
    )
    assert lines(run(tmp_path, "top-ips", 5, "-", stdin=tie)) == ["2 10.0.0.10", "2 10.0.0.9", "1 10.0.0.8"]


def test_errors_group_by_path_without_query_string(tmp_path):
    assert lines(run(tmp_path, "errors", LOG)) == ["16 /api/checkout", "1 /api/products/search"]


def test_errors_skip_malformed_request_lines(tmp_path):
    junk = (
        b'45.148.10.66 - - [28/Oct/2026:10:07:01 +0700] "-" 400 0 "-" "-" rt=0.000\n'
        b'185.242.226.88 - - [28/Oct/2026:10:07:02 +0700] "\\x16\\x03\\x01" 500 157 "-" "-" rt=0.012\n'
        b'10.0.0.5 - - [28/Oct/2026:10:07:03 +0700] "GET /a?x=1 HTTP/1.1" 503 0 "-" "curl/8.5.0" rt=0.002\n'
    )
    assert lines(run(tmp_path, "errors", "-", stdin=junk)) == ["1 /a"]


def test_slow_requests_sorted_numerically(tmp_path):
    assert lines(run(tmp_path, "slow", "0.85", LOG)) == [
        "30.020 504 /api/checkout",
        "30.018 504 /api/checkout",
        "30.011 504 /api/checkout",
        "30.009 504 /api/checkout",
        "30.009 504 /api/checkout",
        "30.009 504 /api/checkout",
        "30.007 504 /api/checkout",
        "30.007 504 /api/checkout",
        "30.000 504 /api/checkout",
        "1.204 500 /api/products/search",
        "0.857 201 /api/checkout",
    ]
    assert lines(run(tmp_path, "slow", 31, LOG)) == []


def test_slow_parses_fields_when_user_agent_has_escaped_quotes(tmp_path):
    row = (
        b'113.161.72.9 - - [28/Oct/2026:10:14:31 +0700] "GET /s?q=t\\x22enis HTTP/1.1" 500 98 "-" '
        b'"Mozilla/5.0 \\x22QA bot\\x22 rt=99" rt=1.204\n'
    )
    assert lines(run(tmp_path, "slow", 1, "-", stdin=row)) == ["1.204 500 /s"]


def test_per_minute_timeline(tmp_path):
    timeline = lines(run(tmp_path, "per-minute", LOG))
    assert len(timeline) == 30
    assert timeline[0] == "10:00 20 0"
    assert timeline[11:18] == [
        "10:11 20 0",
        "10:12 20 3",
        "10:13 20 5",
        "10:14 21 2",
        "10:15 21 2",
        "10:16 21 2",
        "10:17 20 3",
    ]
    assert timeline[-1] == "10:29 20 0"


def test_rotated_gzip_log_via_stdin(tmp_path):
    rotated = tmp_path / "access.log.2.gz"
    rotated.write_bytes(gzip.compress(LOG.read_bytes()))
    result = sandboxed(
        [BASH, "-c", 'gzip -dc "$1" | "$2" "$3" status -', "_", rotated, BASH, ex.path("log_report.sh")], tmp_path
    )
    assert lines(result)[:2] == ["200 435", "201 81"]


def test_upstream_errors_with_jq(tmp_path):
    ex.require_tool("jq")
    assert lines(run(tmp_path, "upstream-errors", JSONL)) == ["18 10.0.1.12:8000", "10 10.0.1.11:8000"]


def test_upstream_errors_counts_each_retry_attempt(tmp_path):
    ex.require_tool("jq")
    rows = (
        b'{"status": 201, "upstream_addr": "10.0.1.12:8000, 10.0.1.11:8000", "upstream_status": "502, 201"}\n'
        b'{"status": 304, "upstream_addr": "-", "upstream_status": "-"}\n'
        b'{"status": 504, "upstream_addr": "10.0.1.12:8000, 10.0.1.11:8000", "upstream_status": "504, 504"}\n'
        b'{"status": 200, "upstream_addr": "unix:/run/olist.sock", "upstream_status": "200"}\n'
    )
    assert lines(run(tmp_path, "upstream-errors", "-", stdin=rows)) == ["2 10.0.1.12:8000", "1 10.0.1.11:8000"]
