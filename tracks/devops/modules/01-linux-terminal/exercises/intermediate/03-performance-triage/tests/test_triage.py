import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def tr():
    return ex.module("triage.py")


def fixture(name: str) -> str:
    return (ex.fixtures / name).read_text()


def test_parse_vmstat_skips_since_boot_line(tr):
    samples = tr.parse_vmstat(fixture("vmstat_cpu.txt"))
    assert len(samples) == 5
    assert samples[0]["r"] == 9 and samples[0]["us"] == 88 and samples[0]["id"] == 2
    assert samples[-1]["b"] == 1
    assert all(isinstance(v, int) for s in samples for v in s.values())


def test_parse_vmstat_repeated_header_and_old_columns(tr):
    samples = tr.parse_vmstat(fixture("vmstat_memory.txt"))
    assert [s["so"] for s in samples] == [5120, 4890, 5300, 4210]
    assert "gu" not in samples[0]
    assert tr.parse_vmstat("procs\n r  b us sy id wa\n 1 0 5 2 93 0\n") == []


def test_use_summary(tr):
    summary = tr.use_summary(tr.parse_vmstat(fixture("vmstat_cpu.txt")), ncpu=4)
    assert summary["cpu_util"] == pytest.approx(98.6)
    assert summary["run_queue_per_cpu"] == pytest.approx(2.5)
    assert summary["iowait"] == pytest.approx(0.0)
    assert summary["blocked"] == pytest.approx(0.2)
    assert summary["swap_io"] == pytest.approx(0.0)
    memory = tr.use_summary(tr.parse_vmstat(fixture("vmstat_memory.txt")), ncpu=4)
    assert memory["swap_io"] == pytest.approx(8217.5)
    assert memory["iowait"] == pytest.approx(40.5)


def test_use_summary_rejects_empty(tr):
    with pytest.raises(ValueError):
        tr.use_summary([], ncpu=4)
    with pytest.raises(ValueError):
        tr.use_summary(tr.parse_vmstat(fixture("vmstat_cpu.txt")), ncpu=0)


@pytest.mark.parametrize(
    "name,ncpu,verdict",
    [
        ("vmstat_cpu.txt", 4, "cpu"),
        ("vmstat_memory.txt", 4, "memory"),
        ("vmstat_disk.txt", 4, "disk"),
        ("vmstat_ok.txt", 4, "ok"),
    ],
)
def test_diagnose(tr, name, ncpu, verdict):
    assert tr.diagnose(tr.parse_vmstat(fixture(name)), ncpu) == verdict


def test_iostat_uses_last_report(tr):
    devices = tr.parse_iostat(fixture("iostat_x.txt"))
    assert set(devices) == {"nvme0n1", "sdb", "dm-0"}
    assert devices["sdb"]["%util"] == pytest.approx(99.6)
    assert devices["sdb"]["aqu-sz"] == pytest.approx(72.89)
    assert devices["sdb"]["w_await"] == pytest.approx(181.3)


def test_saturated_devices_needs_queue_not_only_util(tr):
    assert tr.saturated_devices(fixture("iostat_x.txt")) == ["sdb"]
    assert tr.saturated_devices(fixture("iostat_x.txt"), util=30.0, queue=0.05) == ["dm-0", "nvme0n1", "sdb"]


def test_iostat_old_sysstat_header(tr):
    old = (
        "Linux 4.15.0 (old-db) \t10/28/2026 \t_x86_64_\t(2 CPU)\n\n"
        "Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util\n"
        "sda               0.00     0.10    0.20    1.00     3.00    20.00    38.00     0.01    1.00    0.50    1.10   0.40   0.05\n\n"
        "Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util\n"
        "sda               0.00    12.00    0.00  350.00     0.00 81000.00   462.86    48.10  140.00    0.00  140.00   2.85  99.80\n"
    )
    assert tr.parse_iostat(old)["sda"]["aqu-sz"] == pytest.approx(48.1)
    assert tr.saturated_devices(old) == ["sda"]


def test_socket_states_by_local_port(tr):
    states = tr.socket_states(fixture("ss_tan.txt"), port=8000)
    assert dict(states) == {"LISTEN": 2, "ESTAB": 12, "CLOSE-WAIT": 43}
    everything = tr.socket_states(fixture("ss_tan.txt"))
    assert everything["TIME-WAIT"] == 25
    assert sum(everything.values()) == 94


def test_listen_overflow(tr):
    assert tr.listen_overflow(fixture("ss_ltn.txt")) == ["0.0.0.0:8000", "127.0.0.1:6379"]
