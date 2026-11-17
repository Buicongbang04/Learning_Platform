import json
import subprocess
import time
from pathlib import Path

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
IMAGE = "ghcr.io/ggml-org/llama.cpp:server-b11718"
SMALL = "/home/fde/quillo-1.0.0/models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
MEDIUM = "/home/fde/models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
WORK = "/home/fde/bench"
RESERVE_MB = 128
MIN_TOKENS_PER_S = 10.0
NIGHT_MARGIN_MB = 100
HEAVY_MARGIN_MB = -150
AVAILABLE_SLACK_MB = 150
BENCH_TIMEOUT = 150
TPS_RANGE = (0.5, 2.0)
RSS_RANGE = (0.75, 1.33)
HOG = r'''
import os, sys, time
size = int(sys.argv[1]) * 1048576
block = bytearray(size)
for i in range(0, size, 4096):
    block[i] = 1
open(sys.argv[2], "w").write(str(os.getpid()))
time.sleep(3600)
'''


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def available_mb(m) -> int:
    return int(sh(m, "awk '/^MemAvailable:/ {print int($2 / 1024)}' /proc/meminfo").stdout)


def wait_quillo(m) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if sh(m, "curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -m 5 http://127.0.0.1:18080/healthz").stdout == "200":
            return
        time.sleep(2)
    pytest.fail("quillo của xưởng không trả /healthz 200 sau khi boot snapshot; dựng lại: "
                "uv run python -m fdekit derive 05-gpu-field-factory --force")


def quillo_state(m) -> str:
    return sh(m, "docker ps -a --filter label=com.docker.compose.project=quillo -q | xargs docker inspect -f "
                 "'{{.Name}} {{.State.Status}} {{.RestartCount}} {{.State.StartedAt}} {{.State.OOMKilled}}' | sort").stdout


def other_containers(m) -> list[str]:
    out = sh(m, "docker ps -a --format '{{.Names}} {{.Label \"com.docker.compose.project\"}}'").stdout.split("\n")
    return [line.split()[0] for line in out if line.strip() and not line.strip().endswith(" quillo")]


def run_bench(m, out: str, attempt: str) -> dict:
    cmd = (f"cd {WORK} && python3 bench.py --image {IMAGE} --out {out} "
           f"llm-small={SMALL} llm-medium={MEDIUM}")
    done = sh(m, cmd, timeout=BENCH_TIMEOUT)
    assert done.returncode == 0, (
        f"bench.py ({attempt}) thoát mã {done.returncode}\nstdout:\n{done.stdout[-1500:]}\nstderr:\n{done.stderr[-2500:]}")
    raw = sh(m, f"cat {out}")
    assert raw.returncode == 0, f"{attempt}: không có báo cáo {out}"
    try:
        report = json.loads(raw.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"{attempt}: {out} không phải JSON: {error}")
    for key in ("host", "settings", "models", "recommended"):
        assert key in report, f"{attempt}: báo cáo thiếu khoá {key!r}"
    names = [item.get("name") for item in report["models"]]
    assert names == ["llm-small", "llm-medium"], f"{attempt}: models phải theo đúng thứ tự tham số, nhận {names}"
    return report


def measure(m, path: str, threads: int) -> dict:
    done = sh(m, f"sh /home/fde/.grader/measure.sh {IMAGE} {path} {threads}", timeout=90)
    assert done.returncode == 0, f"Bộ chấm không đo lại được {path}:\n{done.stderr[-1500:]}"
    return json.loads(done.stdout)


def need_mb(size: int) -> int:
    return -(-size * 8 // (10 * 1048576))


def check_entry(entry: dict, size: int, attempt: str, ceiling: int) -> None:
    name = entry["name"]
    need = need_mb(size)
    assert entry.get("need_mb") == need, f"{attempt}/{name}: need_mb phải là {need} (0,8 × MB của tệp GGUF, làm tròn lên)"
    assert isinstance(entry.get("available_mb"), int), f"{attempt}/{name}: thiếu available_mb (số nguyên MB)"
    assert entry["available_mb"] <= ceiling, (
        f"{attempt}/{name}: available_mb {entry['available_mb']} lớn hơn MemAvailable bộ chấm đọc ngay trước khi chạy "
        f"({ceiling - AVAILABLE_SLACK_MB} MB)")
    want = "skipped_memory" if need > entry["available_mb"] - RESERVE_MB else "ok"
    assert entry.get("status") == want, (
        f"{attempt}/{name}: với need_mb {need} và available_mb {entry['available_mb']}, status phải là {want!r}, "
        f"nhận {entry.get('status')!r} {entry.get('detail', '')}")
    if want == "ok":
        for key in ("tokens_per_s", "peak_rss_mb"):
            assert isinstance(entry.get(key), (int, float)) and entry[key] > 0, f"{attempt}/{name}: thiếu {key}"


def compare(entry: dict, truth: dict, attempt: str) -> None:
    name = entry["name"]
    ratio = entry["tokens_per_s"] / truth["tokens_per_s"]
    assert TPS_RANGE[0] <= ratio <= TPS_RANGE[1], (
        f"{attempt}/{name}: báo cáo {entry['tokens_per_s']:.1f} tokens/s, bộ chấm đo lại ngay sau đó trên cùng máy "
        f"được {truth['tokens_per_s']:.1f} tokens/s (cho phép gấp {TPS_RANGE[1]:g} hoặc một nửa)")
    ratio = entry["peak_rss_mb"] / truth["peak_rss_mb"]
    assert RSS_RANGE[0] <= ratio <= RSS_RANGE[1], (
        f"{attempt}/{name}: báo cáo peak_rss_mb {entry['peak_rss_mb']}, đo lại được {truth['peak_rss_mb']:.0f}")


def check_recommended(report: dict, attempt: str) -> None:
    good = [e["name"] for e in report["models"] if e["status"] == "ok" and e["tokens_per_s"] >= MIN_TOKENS_PER_S]
    want = good[-1] if good else None
    assert report["recommended"] == want, f"{attempt}: recommended phải là {want!r}, nhận {report['recommended']!r}"


def start_job(m, mb: int, tag: str) -> str:
    pid_file = f"/home/fde/.grader/{tag}.pid"
    sh(m, f"setsid nohup python3 /home/fde/.grader/hog.py {mb} {pid_file} > /dev/null 2>&1 < /dev/null &")
    deadline = time.monotonic() + 60
    while sh(m, f"test -s {pid_file}").returncode != 0:
        assert time.monotonic() < deadline, f"Bộ chấm không dựng được job {tag} của xưởng"
        time.sleep(1)
    return sh(m, f"cat {pid_file}").stdout.strip()


def shift(m, attempt: str, out: str, sizes: dict[str, int], cores: int, want: list[str | None]) -> dict:
    ceiling = available_mb(m) + AVAILABLE_SLACK_MB
    report = run_bench(m, out, attempt)
    host = report["host"]
    assert host.get("physical_cores") == cores, f"{attempt}: host.physical_cores phải là {cores}, nhận {host.get('physical_cores')}"
    mem_total = int(sh(m, "awk '/^MemTotal:/ {print int($2 / 1024)}' /proc/meminfo").stdout)
    assert abs(host.get("mem_total_mb", 0) - mem_total) <= 2, f"{attempt}: host.mem_total_mb phải là {mem_total}"
    assert host.get("gpu", "thiếu") is None, f"{attempt}: máy xưởng không có GPU dùng được, host.gpu phải là null"
    for entry in report["models"]:
        check_entry(entry, sizes[entry["name"]], attempt, ceiling)
    statuses = [e["status"] for e in report["models"]]
    assert all(w is None or w == got for w, got in zip(want, statuses)), (
        f"{attempt}: status của hai model phải là {want} (None: theo quy tắc), nhận {statuses}")
    assert other_containers(m) == [], f"bench.py để lại container: {other_containers(m)}"
    for entry, path in zip(report["models"], (SMALL, MEDIUM)):
        if entry["status"] == "ok":
            compare(entry, measure(m, path, cores), attempt)
    check_recommended(report, attempt)
    return report


def test_bench_on_factory(tmp_path):
    base = fdekit.derived("05-gpu-field-factory")
    script = ex.path("bench.py")
    with fdekit.vm("factory", base=base) as m:
        wait_quillo(m)
        sizes = {name: int(sh(m, f"stat -c %s {path}").stdout) for name, path in (("llm-small", SMALL), ("llm-medium", MEDIUM))}
        cores = int(sh(m, "lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l").stdout)
        assert sh(m, f"mkdir -p {WORK} /home/fde/.grader").returncode == 0
        m.put(script, f"{WORK}/bench.py")
        (tmp_path / "hog.py").write_text(HOG)
        m.put(Path(__file__).with_name("measure.sh"), "/home/fde/.grader/measure.sh")
        m.put(tmp_path / "hog.py", "/home/fde/.grader/hog.py")
        before = quillo_state(m)
        need_medium = need_mb(sizes["llm-medium"]) + RESERVE_MB
        assert available_mb(m) >= need_medium + 300, "Snapshot của xưởng không còn đủ RAM trống cho ca ngày; dựng lại snapshot"

        shift(m, "ca ngày", f"{WORK}/report-ca-ngay.json", sizes, cores, ["ok", "ok"])

        night = start_job(m, max(available_mb(m) - need_medium - NIGHT_MARGIN_MB, 0), "ca-dem")
        shift(m, "ca đêm", f"{WORK}/report-ca-dem.json", sizes, cores, ["ok", None])
        heavy = start_job(m, max(available_mb(m) - need_medium - HEAVY_MARGIN_MB, 0), "ca-dem-cuoi-thang")
        shift(m, "ca đêm cuối tháng", f"{WORK}/report-ca-dem-cuoi-thang.json", sizes, cores, ["ok", "skipped_memory"])
        for pid in (night, heavy):
            assert sh(m, f"kill -0 {pid}").returncode == 0, "Job của xưởng đã chết trong lúc benchmark"

        assert quillo_state(m) == before, (
            f"Container quillo của xưởng đã bị khởi động lại hoặc bị kill trong lúc benchmark:\n{before}\n→\n{quillo_state(m)}")
        healthz = sh(m, "curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -m 10 http://127.0.0.1:18080/healthz").stdout
        assert healthz == "200", f"quillo của xưởng trả /healthz {healthz} sau benchmark"
