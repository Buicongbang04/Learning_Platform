import json
import shlex


import fdekit
from testkit import Exercise

ex = Exercise(__file__)
MIN_SPEEDUP = 3.0
TIMEOUT = 240


def test_gpu_beats_cpu_on_pc():
    with fdekit.require_pc() as pc:
        script = ex.path("bench_pc.sh").read_text()
        info = pc.gpu()
        work = f"~/{pc.workdir}"
        put = pc.ssh(f"mkdir -p {work} && printf %s {shlex.quote(script)} > {work}/bench_pc.sh")
        assert put.returncode == 0, f"Không chép được bench_pc.sh lên PC:\n{put.stderr[-1000:]}"
        done = pc.ssh(f"cd {work} && sh bench_pc.sh \"$PWD\"", timeout=TIMEOUT)
        left = pc.ssh(f"docker ps -aq --filter name={pc.workdir}").stdout.strip()
        assert done.returncode == 0, f"bench_pc.sh thoát {done.returncode}\n{done.stderr[-2500:]}"
        assert not left, f"bench_pc.sh để lại container trên PC: {left}"
        report = json.loads(done.stdout.strip().splitlines()[-1])
        assert report["gpu"]["name"] == info["name"], f"gpu.name phải là {info['name']}, nhận {report['gpu']['name']}"
        assert report["gpu"]["memory_mb"] == info["memory_mb"]
        cpu, gpu = report["cpu_tokens_per_s"], report["gpu_tokens_per_s"]
        assert cpu > 0 and gpu >= MIN_SPEEDUP * cpu, (
            f"GPU {gpu} tokens/s, CPU {cpu} tokens/s: cần GPU ≥ {MIN_SPEEDUP:g}× CPU (llm-medium, -ngl 99). "
            "Kiểm container có thật sự thấy GPU (log 'offloaded ... layers to GPU')")
