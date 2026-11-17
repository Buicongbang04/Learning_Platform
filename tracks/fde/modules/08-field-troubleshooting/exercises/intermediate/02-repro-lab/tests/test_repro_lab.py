"""Tái hiện lỗi của bệnh viện trên máy lab: chạy repro.sh trên `lab-open` (quillo 1.0.0) rồi so chữ ký lỗi với bundle."""

import json
import re
import shlex
import subprocess
import time
from pathlib import Path

import pytest
import requests

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
BUNDLE = Path(__file__).resolve().parents[1] / "customer-bundle"
SNAPSHOT = "07-customer-integration-quillo"
QUILLO = "/home/fde/quillo-1.0.0"
WORK = "/home/fde/repro"
MEMORY_MB = 3072
RUN_TIMEOUT = 150
HEALTH_WAIT = 120
URL = re.compile(r"https?://[^\s'\"]+?(?=:\s|['\"\s]|$)")
LINE = re.compile(r"^api-\d+\s+\|\s?(\{.*\})\s*$")


def normalize(error: str) -> str:
    return URL.sub("<url>", error)


def signatures(log: str) -> dict[tuple[str, str], set[int]]:
    """{(msg, error đã chuẩn hoá): {status HTTP của request cùng path ngay sau đó}} cho các dòng ERROR của api."""
    events = []
    for line in log.splitlines():
        match = LINE.match(line)
        if not match:
            continue
        try:
            events.append(json.loads(match.group(1)))
        except ValueError:
            continue
    found: dict[tuple[str, str], set[int]] = {}
    for i, event in enumerate(events):
        if event.get("level") != "ERROR" or "error" not in event:
            continue
        key = (event.get("msg", ""), normalize(str(event["error"])))
        statuses = found.setdefault(key, set())
        for later in events[i + 1:i + 4]:
            if later.get("msg") == "request" and later.get("path") == event.get("path"):
                statuses.add(later.get("status"))
                break
    return found


def customer_signature() -> tuple[tuple[str, str], str, int]:
    log = (BUNDLE / "quillo" / "logs" / "api.log").read_text()
    found = signatures(log)
    assert len(found) == 1, f"bundle của khách phải có đúng một chữ ký lỗi, có {found}"
    [(key, statuses)] = found.items()
    path = next(json.loads(m.group(1))["path"] for m in map(LINE.match, log.splitlines())
                if m and '"level": "ERROR"' in m.group(1))
    return key, path, min(statuses)


def sh(m: fdekit.VM, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    for attempt in range(3):
        try:
            done = m.ssh(cmd, timeout=timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")
        if done.returncode != 255 or attempt == 2:
            return done
        time.sleep(2)
    return done


def wait_health(api: str, m: fdekit.VM, label: str) -> None:
    deadline = time.monotonic() + HEALTH_WAIT
    last = ""
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{api}/healthz", timeout=5)
            if response.status_code == 200:
                return
            last = f"HTTP {response.status_code} {response.text[:200]}"
        except requests.RequestException as error:
            last = type(error).__name__
        time.sleep(2)
    ps = sh(m, f"cd {QUILLO} && docker compose ps -a").stdout
    pytest.fail(f"{label}: quillo không trả /healthz 200 sau {HEALTH_WAIT} s ({last})\n{ps[-2000:]}")


def run_repro(m: fdekit.VM, attempt: str) -> None:
    done = sh(m, f"cd {WORK} && timeout {RUN_TIMEOUT} sh repro.sh", timeout=RUN_TIMEOUT + 30)
    assert done.returncode != 124, f"repro.sh ({attempt}) chạy quá {RUN_TIMEOUT} s"
    assert done.returncode == 0, (f"repro.sh ({attempt}) thoát {done.returncode}\nstdout:\n{done.stdout[-2000:]}\n"
                                  f"stderr:\n{done.stderr[-2500:]}")


def test_repro_matches_customer_signature():
    key, path, status = customer_signature()
    base = fdekit.derived(SNAPSHOT)
    with fdekit.vm("lab-open", base=base, memory_mb=MEMORY_MB, forwards=(18080,)) as m:
        api = f"http://127.0.0.1:{m.port(18080)}"
        wait_health(api, m, "Sau khi boot snapshot")
        admin = sh(m, f"sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {QUILLO}/.env").stdout.strip()
        assert len(admin) >= 16, "Không đọc được QUILLO_ADMIN_TOKEN của snapshot"
        sh(m, f"mkdir -p {WORK}")
        m.put(ex.path("repro.sh"), f"{WORK}/repro.sh")
        for attempt in ("lần 1", "lần 2 (chạy lại)"):
            run_repro(m, attempt)
            wait_health(api, m, f"Sau repro.sh {attempt}")
        since = sh(m, "date -u +%Y-%m-%dT%H:%M:%SZ").stdout.strip()
        time.sleep(1)
        got = []
        for _ in range(2):
            got.append(requests.get(f"{api}{path}", allow_redirects=False, timeout=60).status_code)
        me = requests.get(f"{api}/api/me", headers={"Authorization": f"Bearer {admin}"}, timeout=30)
        assert me.status_code == 200, f"Token quản trị phải vẫn dùng được như ở bệnh viện (/api/me trả {me.status_code})"
        time.sleep(2)
        log = sh(m, f"cd {QUILLO} && docker compose logs --no-color --since {shlex.quote(since)} api").stdout
        mine = signatures(log)
        assert key in mine, (
            f"Gọi {path} sau repro.sh không sinh ra đúng lỗi của bệnh viện.\n"
            f"Cần (msg, error đã chuẩn hoá): {key}\n"
            f"Có: {sorted(mine) or 'không có dòng ERROR nào của api'}")
        assert got == [status, status], f"{path} phải trả {status} như ở bệnh viện, trả {got}"
