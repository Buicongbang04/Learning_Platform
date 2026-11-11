import json
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
HERE = Path(__file__).resolve().parent
LOGS = sorted((HERE / "logs").glob("*.log"))
TS = re.compile(r'"ts": "(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d{4})"')
LINE = re.compile(r"^([A-Za-z0-9_.-]+?)-\d+\s+\|")
FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def triage(path: Path, tmp_path: Path) -> dict:
    try:
        done = run_sandboxed([sys.executable, str(ex.path("triage_logs.py")), str(path)], writable=[tmp_path],
                             cwd=tmp_path, env={}, timeout=30)
    except subprocess.TimeoutExpired:
        pytest.fail(f"triage_logs.py chạy quá 30 s với {path.name}")
    assert done.returncode == 0, f"triage_logs.py thoát {done.returncode}\n{done.stderr[-2000:]}"
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"stdout của triage_logs.py không phải JSON: {error}\n{done.stdout[:500]}")


def compare(got: dict, want: dict, label: str) -> None:
    for key in ("services", "window", "groups", "http_5xx", "incidents"):
        assert key in got, f"{label}: thiếu khoá {key!r} trong output"
        assert got[key] == want[key], (f"{label}: {key} sai\ncần: {json.dumps(want[key], ensure_ascii=False)[:1500]}\n"
                                       f"có:  {json.dumps(got[key], ensure_ascii=False)[:1500]}")


def shift_ts(value: str, delta: timedelta) -> str:
    return (datetime.strptime(value, FORMAT) + delta).strftime(FORMAT)


def shift_expected(want: dict, delta: timedelta) -> dict:
    out = json.loads(json.dumps(want))
    if out["window"]:
        out["window"] = {k: shift_ts(v, delta) for k, v in out["window"].items()}
    for key in ("groups", "http_5xx"):
        for row in out[key]:
            row["first"], row["last"] = shift_ts(row["first"], delta), shift_ts(row["last"], delta)
    for row in out["incidents"]:
        row["start"], row["end"] = shift_ts(row["start"], delta), shift_ts(row["end"], delta)
    return out


def reinterleave(lines: list[str], rng: random.Random) -> list[str]:
    """Trộn lại thứ tự giữa các dịch vụ như `docker compose logs` có thể in, giữ thứ tự trong từng dịch vụ."""
    queues: dict[str, list[str]] = {}
    for line in lines:
        match = LINE.match(line)
        queues.setdefault(match.group(1) if match else "", []).append(line)
    out = []
    while queues:
        name = rng.choice(sorted(queues))
        take = rng.randint(1, 6)
        out.extend(queues[name][:take])
        del queues[name][:take]
        if not queues[name]:
            del queues[name]
    return out


@pytest.mark.parametrize("log", LOGS, ids=lambda p: p.stem)
def test_recorded_logs(log, tmp_path):
    want = json.loads((HERE / "expected" / f"{log.stem}.json").read_text())
    compare(triage(log, tmp_path), want, log.name)


@pytest.mark.parametrize("log", LOGS, ids=lambda p: p.stem)
def test_same_incident_other_day(log, tmp_path):
    rng = random.Random()
    want = json.loads((HERE / "expected" / f"{log.stem}.json").read_text())
    delta = timedelta(days=rng.randint(-400, 400), hours=rng.randint(0, 23), minutes=rng.randint(0, 59),
                      seconds=rng.randint(0, 59))
    lines = [TS.sub(lambda m: f'"ts": "{shift_ts(m.group(1), delta)}"', line)
             for line in log.read_text().splitlines(keepends=True)]
    lines = reinterleave(lines, rng)
    want = shift_expected(want, delta)
    service = rng.choice(sorted(want["services"]))
    broken = [f'{service}-1  | {{"ts": "{shift_ts("2026-11-11T05:00:00+0000", delta)}", "level": "ERR\n',
              f"{service}-1  | {{not json at all}}\n", f"{service}-1  | []\n"]
    for extra in broken:
        lines.insert(rng.randint(0, len(lines)), extra)
    want["services"][service]["unparsed"] += len(broken)
    lines.insert(rng.randint(0, len(lines)), "\n")
    path = tmp_path / f"{rng.randint(1000, 9999)}.log"
    path.write_text("".join(lines))
    compare(triage(path, tmp_path), want, f"{log.name} (dời {delta}, trộn thứ tự dịch vụ, thêm dòng hỏng)")
