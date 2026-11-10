import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

import fdekit
from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
SMI = ex.dir.parent.parent / "basic" / "03-diagnose-gpu" / "tests" / "fixtures"
QUILLO = "/home/fde/quillo-1.0.0"
FILES = {"llm-small": "qwen2.5-0.5b-instruct-q4_k_m.gguf", "llm-medium": "qwen2.5-1.5b-instruct-q4_k_m.gguf"}
KEYS = ("QUILLO_LLM_FILE", "QUILLO_LLM_MODEL", "QUILLO_LLM_THREADS", "QUILLO_EMBED_THREADS")
RUN_TIMEOUT = 240
BROKEN = "#!/bin/sh\ncat <<'EOF'\n{text}EOF\nexit 9\n"
WORKING = ("#!/bin/sh\ncase \"$*\" in\n*--query-gpu*) echo 'NVIDIA GeForce RTX 3060, 12288' ;;\n"
           "*) cat <<'EOF'\n{text}EOF\n;;\nesac\nexit 0\n")


def stub(folder: Path, kind: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    if kind == "broken":
        body = BROKEN.format(text=(SMI / "laptop-driver-not-loaded.txt").read_text())
    else:
        body = WORKING.format(text=(SMI / "idle-rtx3060.txt").read_text())
    path = folder / "nvidia-smi"
    path.write_text(body)
    path.chmod(0o755)
    return folder


def expected(cores: int, mem_mb: int, gpu: dict | None) -> dict:
    budget = gpu["memory_mb"] if gpu else mem_mb
    model = "llm-medium" if budget >= 4096 else "llm-small"
    return {"physical_cores": cores, "mem_total_mb": mem_mb, "gpu": gpu, "backend": "cuda" if gpu else "cpu",
            "n_gpu_layers": 99 if gpu else 0, "model": model, "llm_file": FILES[model], "llm_threads": cores,
            "embed_threads": max(1, cores // 2)}


@pytest.fixture(scope="module")
def mod():
    return ex.module("hw_config.py")


def test_physical_cores_on_recorded_topology(mod, tmp_path):
    laptop = tmp_path / "laptop"
    shutil.copytree(ex.fixtures / "laptop-i7-11800h", laptop)
    assert mod.physical_cores(laptop) == 8, "i7-11800H: 16 CPU logic, 8 core vật lý"
    for online, want in (("0-3,8-11\n", 4), ("0,8\n", 1), ("0-5\n", 6), ("0-15\n", 8)):
        (laptop / "online").write_text(online)
        assert mod.physical_cores(laptop) == want, f"online={online.strip()}: cần {want} core vật lý"


@pytest.mark.parametrize("cores,mem_mb,gpu", [
    (2, 2919, None), (4, 4919, None), (4, 4095, None), (4, 4096, None), (16, 31802, None),
    (8, 31802, {"name": "NVIDIA GeForce RTX 3060", "memory_mb": 12288}),
    (8, 2919, {"name": "NVIDIA GeForce RTX 3060", "memory_mb": 12288}),
    (8, 31802, {"name": "NVIDIA T400", "memory_mb": 2048}), (1, 1024, None),
])
def test_choose_rules(mod, cores, mem_mb, gpu):
    assert mod.choose(cores, mem_mb, gpu) == expected(cores, mem_mb, gpu)


def host_truth() -> tuple[int, int]:
    out = subprocess.run(["lscpu", "-p=CORE,SOCKET"], capture_output=True, text=True, check=True).stdout
    cores = len({line for line in out.splitlines() if line and not line.startswith("#")})
    mem = next(int(line.split()[1]) // 1024 for line in Path("/proc/meminfo").read_text().splitlines()
               if line.startswith("MemTotal:"))
    return cores, mem


@pytest.mark.parametrize("kind", ["broken", "working"])
def test_dry_run_with_nvidia_smi(tmp_path, kind):
    path = f"{stub(tmp_path / 'bin', kind)}:/usr/local/bin:/usr/bin:/bin"
    try:
        done = run_sandboxed([sys.executable, ex.path("hw_config.py"), "--dry-run"], writable=[tmp_path], cwd=tmp_path,
                             env={"PATH": path}, timeout=60)
    except subprocess.TimeoutExpired:
        pytest.fail("hw_config.py --dry-run chạy quá 60 s")
    assert done.returncode == 0, f"--dry-run thoát {done.returncode}\n{done.stderr[-1500:]}"
    cores, mem = host_truth()
    gpu = {"name": "NVIDIA GeForce RTX 3060", "memory_mb": 12288} if kind == "working" else None
    got = json.loads(done.stdout.strip().splitlines()[-1])
    assert got == expected(cores, mem, gpu), f"nvidia-smi {kind}: cấu hình sai\n{got}"


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def wait_quillo(m, name: str) -> None:
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        if sh(m, "curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -m 5 http://127.0.0.1:18080/healthz").stdout == "200":
            return
        time.sleep(2)
    pytest.fail(f"quillo trên {name} không trả /healthz 200 sau khi boot snapshot; dựng lại snapshot bằng "
                "uv run python -m fdekit derive <tên> --force")


def env_file(m) -> dict[str, str]:
    lines = sh(m, f"cat {QUILLO}/.env").stdout.splitlines()
    return {line.split("=", 1)[0]: line.split("=", 1)[1] for line in lines if "=" in line and not line.startswith("#")}


def started(m) -> str:
    return sh(m, "docker ps -q --filter label=com.docker.compose.project=quillo | xargs docker inspect -f "
                 "'{{.Name}} {{.State.StartedAt}}' | sort").stdout


def run_config(m, extra_path: str = "") -> subprocess.CompletedProcess:
    prefix = f"PATH={extra_path}:$PATH " if extra_path else ""
    return sh(m, f"cd /home/fde && {prefix}python3 /home/fde/hw/hw_config.py", timeout=RUN_TIMEOUT)


def check_vm(m, name: str, want: dict) -> None:
    before = env_file(m)
    done = run_config(m, "/home/fde/fakebin" if name == "lab-open" else "")
    assert done.returncode == 0, f"{name}: hw_config.py thoát {done.returncode}\n{done.stdout[-1500:]}\n{done.stderr[-2500:]}"
    got = json.loads(done.stdout.strip().splitlines()[-1])
    assert got == want, f"{name}: cấu hình in ra sai\ncần {want}\nnhận {got}"
    after = env_file(m)
    values = {"QUILLO_LLM_FILE": want["llm_file"], "QUILLO_LLM_MODEL": want["model"],
              "QUILLO_LLM_THREADS": str(want["llm_threads"]), "QUILLO_EMBED_THREADS": str(want["embed_threads"])}
    for key, value in values.items():
        assert after.get(key) == value, f"{name}: .env có {key}={after.get(key)}, cần {value}"
    rest = {k: v for k, v in before.items() if k not in KEYS}
    assert {k: v for k, v in after.items() if k not in KEYS} == rest, f"{name}: hw_config.py đổi cả dòng khác của .env"
    mode = sh(m, f"stat -c %a {QUILLO}/.env").stdout.strip()
    assert mode == "600", f"{name}: .env chứa secret, phải giữ quyền 600 (đang {mode})"
    args = sh(m, "docker inspect -f '{{json .Args}}' quillo-llm-1").stdout
    llm_args = json.loads(args)
    assert f"/models/{want['llm_file']}" in llm_args, f"{name}: container llm chạy {llm_args}, cần model {want['llm_file']}"
    assert llm_args[llm_args.index("-t") + 1] == str(want["llm_threads"]), f"{name}: llm chạy {llm_args}"
    embed = json.loads(sh(m, "docker inspect -f '{{json .Args}}' quillo-embed-1").stdout)
    assert embed[embed.index("-t") + 1] == str(want["embed_threads"]), f"{name}: embed chạy {embed}"
    healthz = sh(m, "curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -m 10 http://127.0.0.1:18080/healthz").stdout
    assert healthz == "200", f"{name}: quillo trả /healthz {healthz} sau khi đổi cấu hình"
    state = started(m)
    again = run_config(m, "/home/fde/fakebin" if name == "lab-open" else "")
    assert again.returncode == 0, f"{name}: chạy lại hw_config.py thoát {again.returncode}\n{again.stderr[-1500:]}"
    assert started(m) == state, f"{name}: chạy lại lần hai (không có gì đổi) vẫn khởi động lại container quillo"


def facts(m) -> tuple[int, int]:
    cores = int(sh(m, "lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l").stdout)
    mem = int(sh(m, "awk '/^MemTotal:/ {print int($2 / 1024)}' /proc/meminfo").stdout)
    return cores, mem


def test_factory_and_lab(tmp_path):
    factory = fdekit.derived("05-gpu-field-factory")
    lab = fdekit.derived("05-gpu-field-lab")
    script = ex.path("hw_config.py")
    with fdekit.vm("factory", base=factory) as m:
        wait_quillo(m, "factory")
        assert sh(m, "mkdir -p /home/fde/hw").returncode == 0
        m.put(script, "/home/fde/hw/hw_config.py")
        cores, mem = facts(m)
        check_vm(m, "factory", expected(cores, mem, None))
    bins = tmp_path / "bins"
    stub(bins / "broken", "broken")
    stub(bins / "working", "working")
    with fdekit.vm("lab-open", base=lab, memory_mb=5120, cpus=4) as m:
        wait_quillo(m, "lab-open")
        assert sh(m, "mkdir -p /home/fde/hw /home/fde/fakebin /home/fde/gpubin").returncode == 0
        m.put(script, "/home/fde/hw/hw_config.py")
        m.put(bins / "broken" / "nvidia-smi", "/home/fde/fakebin/nvidia-smi")
        m.put(bins / "working" / "nvidia-smi", "/home/fde/gpubin/nvidia-smi")
        assert sh(m, "chmod 755 /home/fde/fakebin/nvidia-smi /home/fde/gpubin/nvidia-smi").returncode == 0
        cores, mem = facts(m)
        assert cores == 4
        before, state = env_file(m), started(m)
        gpu = run_config(m, "/home/fde/gpubin")
        assert gpu.returncode == 3, (
            f"lab-open với GPU dùng được nhưng chưa có image CUDA: hw_config.py phải thoát 3, nhận {gpu.returncode}\n"
            f"{gpu.stderr[-1500:]}")
        assert env_file(m) == before and started(m) == state, "Thoát 3 thì không được đổi .env hay container"
        check_vm(m, "lab-open", expected(cores, mem, None))
