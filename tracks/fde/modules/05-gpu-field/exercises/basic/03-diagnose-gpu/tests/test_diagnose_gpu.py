import json
import random
import re
import subprocess
import sys

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
CODES = {"ok", "gpu_busy", "mig_enabled", "no_gpu", "not_installed", "driver_not_loaded", "driver_mismatch",
         "nvml_unknown", "gpu_lost", "unknown"}
SAMPLES = {
    "laptop-driver-not-loaded.txt": (4096, {"driver_not_loaded"}),
    "factory-not-installed.txt": (4096, {"not_installed"}),
    "factory-not-installed-sh.txt": (4096, {"not_installed"}),
    "driver-library-mismatch.txt": (4096, {"driver_mismatch"}),
    "nvml-unknown-error-in-container.txt": (4096, {"nvml_unknown"}),
    "gpu-fell-off-bus.txt": (4096, {"gpu_lost"}),
    "no-devices.txt": (4096, {"no_gpu"}),
    "idle-rtx3060.txt": (4096, {"ok"}),
    "busy-rtx3060.txt": (4096, {"gpu_busy"}),
    "two-l4-one-busy.txt": (16384, {"ok"}),
    "container-hidden-processes.txt": (8192, {"gpu_busy"}),
    "mig-a100.txt": (4096, {"mig_enabled"}),
}
TABLES = ["idle-rtx3060.txt", "busy-rtx3060.txt", "two-l4-one-busy.txt", "container-hidden-processes.txt"]
MEMORY = re.compile(r"^(\|[^|]*\|)(\s*)(\d+)(MiB\s*/\s*)(\d+)(MiB\s*\|[^|]*\|)$")


@pytest.fixture(scope="module")
def mod():
    return ex.module("diagnose_gpu.py")


def run(mod, text: str, need_mb: int) -> str:
    got = mod.diagnose(text, need_mb)
    assert got in CODES, f"diagnose() trả {got!r}, không thuộc {sorted(CODES)}"
    return got


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_recorded_samples(mod, name):
    need, accepted = SAMPLES[name]
    text = (ex.fixtures / name).read_text(encoding="utf-8")
    got = run(mod, text, need)
    assert got in accepted, f"{name} (need_mb={need}): cần một trong {sorted(accepted)}, nhận {got!r}"


def mutate(text: str, rng: random.Random) -> tuple[str, list[int]]:
    lines, free = text.split("\n"), []
    for number, line in enumerate(lines):
        if line.startswith("| Processes:"):
            break
        match = MEMORY.match(line)
        if not match:
            continue
        total = int(match.group(5))
        used = rng.randrange(0, total + 1)
        width = len(match.group(2)) + len(match.group(3))
        lines[number] = match.group(1) + f"{used}".rjust(width) + match.group(4) + match.group(5) + match.group(6)
        free.append(total - used)
    return "\n".join(lines), free


def test_memory_numbers_are_read(mod):
    rng = random.Random(random.SystemRandom().randrange(1 << 30))
    for _ in range(200):
        name = rng.choice(TABLES)
        text, free = mutate((ex.fixtures / name).read_text(encoding="utf-8"), rng)
        need = rng.choice([max(free) - 1, max(free), max(free) + 1, rng.randrange(1, 24000)])
        need = max(need, 1)
        want = "ok" if max(free) >= need else "gpu_busy"
        got = run(mod, text, need)
        assert got == want, f"{name} với RAM GPU trống {free} MiB và need_mb={need}: cần {want!r}, nhận {got!r}"


def test_mig_wins_over_free_memory(mod):
    text = (ex.fixtures / "mig-a100.txt").read_text(encoding="utf-8")
    assert run(mod, text, 1) == "mig_enabled"


def test_unparseable_is_unknown(mod):
    assert run(mod, "Segmentation fault (core dumped)\n", 4096) == "unknown"
    assert run(mod, "", 4096) == "unknown"


def test_cli(tmp_path):
    sample = tmp_path / "out.txt"
    sample.write_text((ex.fixtures / "busy-rtx3060.txt").read_text(encoding="utf-8"))
    try:
        done = run_sandboxed([sys.executable, ex.path("diagnose_gpu.py"), sample, "4096"], writable=[tmp_path],
                             cwd=tmp_path, env={}, timeout=60)
    except subprocess.TimeoutExpired:
        pytest.fail("diagnose_gpu.py chạy quá 60 s")
    assert done.returncode == 0, done.stderr[-1000:]
    assert json.loads(done.stdout) == {"diagnosis": "gpu_busy"}
