import random
import subprocess
import time
import uuid

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
REMOTE = "/home/fde/check_ports.sh"
BUDGET_SECONDS = 10
UDP_HOLDER = "import socket, time; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(('0.0.0.0', {port})); time.sleep(900)"


def pick_ports() -> dict[str, int]:
    rng = random.Random()
    while True:
        user, root, free, udp = rng.sample(range(21024, 29999), 4)
        suffix = user % 10000
        if suffix >= 1024 and len({user, root, free, udp, suffix}) == 5:
            return {"user": user, "root": root, "free": free, "udp": udp, "suffix": suffix}


def listening(m, proto: str = "t") -> set[int]:
    out = m.ssh(f"sudo -n ss -H -{proto} -l -n", timeout=30)
    assert out.returncode == 0, out.stderr
    return {int(line.split()[3].rsplit(":", 1)[1]) for line in out.stdout.splitlines() if line.strip()}


def wait_for(m, ports: set[int], *, present: bool, proto: str = "t") -> None:
    deadline = time.monotonic() + 30
    while True:
        seen = listening(m, proto)
        if (ports <= seen) if present else not (ports & seen):
            return
        if time.monotonic() > deadline:
            pytest.fail(f"Listener thử nghiệm trên cổng {sorted(ports)} không {'lên' if present else 'tắt'} trong 30 s")
        time.sleep(0.5)


def check_ports(m, ports: list[int]) -> dict[int, str]:
    started = time.monotonic()
    try:
        result = m.ssh(f"sh {REMOTE} " + " ".join(map(str, ports)), timeout=BUDGET_SECONDS * 3)
    except subprocess.TimeoutExpired:
        pytest.fail(f"check_ports.sh chạy quá {BUDGET_SECONDS * 3} s mà chưa xong (treo?)")
    elapsed = time.monotonic() - started
    assert result.returncode == 0, f"check_ports.sh thoát mã {result.returncode}\nstderr:\n{result.stderr}"
    assert elapsed <= BUDGET_SECONDS, f"check_ports.sh chạy {elapsed:.0f} s, quá {BUDGET_SECONDS} s"
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert [line.split()[0] for line in lines] == [str(p) for p in ports], (
        f"Cần đúng một dòng cho mỗi cổng theo thứ tự tham số {ports}, nhận:\n{result.stdout}")
    report = {}
    for port, line in zip(ports, lines):
        parts = line.split()
        assert parts[1:2] in (["free"], ["busy"]), f"Dòng {line!r}: trạng thái phải là free hoặc busy"
        assert len(parts) == (2 if parts[1] == "free" else 3), f"Dòng {line!r} sai dạng '<cổng> free' / '<cổng> busy <tiến trình>'"
        report[port] = " ".join(parts[1:])
    return report


def test_ports_seen_without_root():
    script = ex.path("check_ports.sh")
    ports = pick_ports()
    unit = f"fde-port-{uuid.uuid4().hex[:8]}"
    with fdekit.vm("lab-open", memory_mb=1024) as m:
        m.put(script, REMOTE)
        start = (
            f"setsid nohup python3 -m http.server --bind 127.0.0.1 {ports['user']} </dev/null >/dev/null 2>&1 & "
            f"setsid nohup python3 -c \"{UDP_HOLDER.format(port=ports['udp'])}\" </dev/null >/dev/null 2>&1 & "
            f"sudo -n systemd-run --quiet --unit={unit} python3 -m http.server --bind :: {ports['root']}"
        )
        assert m.ssh(start, timeout=30).returncode == 0
        wait_for(m, {ports["user"], ports["root"]}, present=True)
        wait_for(m, {ports["udp"]}, present=True, proto="u")
        busy = listening(m)
        assert not {ports["free"], ports["suffix"], ports["udp"]} & busy, "Cổng thử nghiệm đã bị dùng sẵn, chạy lại test"
        asked = [ports["suffix"], ports["user"], 22, ports["root"], ports["free"], ports["udp"]]
        random.shuffle(asked)
        first = check_ports(m, asked)
        stop = m.ssh(f"pkill -f 'http[.]server --bind 127.0.0.1 {ports['user']}'", timeout=30)
        assert stop.returncode == 0, stop.stderr
        wait_for(m, {ports["user"]}, present=False)
        second = check_ports(m, asked)
    expected = {
        ports["user"]: "busy python3",
        ports["root"]: "busy unknown",
        22: "busy unknown",
        ports["free"]: "free",
        ports["udp"]: "free",
        ports["suffix"]: "free",
    }
    for port, want in expected.items():
        assert first[port] == want, f"Cổng {port}: nhận {first[port]!r}, cần {want!r}"
    assert second[ports["user"]] == "free", f"Đã tắt listener trên {ports['user']} nhưng script vẫn in {second[ports['user']]!r}"
    assert {p: v for p, v in second.items() if p != ports["user"]} == {p: v for p, v in first.items() if p != ports["user"]}
