import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROMPT = "Viết một đoạn ngắn hướng dẫn bảo trì máy CNC cho ca đêm."
CTX = 4096
N_PREDICT = 64
RUNS = 3
MIN_TOKENS_PER_S = 10.0
NEED_FACTOR_TENTHS = 17
RESERVE_MB = 128
READY_TIMEOUT = 180
REQUEST_TIMEOUT = 120
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def meminfo() -> dict[str, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, rest = line.split(":", 1)
        values[key] = int(rest.split()[0]) // 1024
    return values


def online_cpus(text: str) -> list[int]:
    cpus = []
    for part in text.strip().split(","):
        if "-" in part:
            low, high = part.split("-")
            cpus.extend(range(int(low), int(high) + 1))
        elif part:
            cpus.append(int(part))
    return cpus


def physical_cores(root: Path = Path("/sys/devices/system/cpu")) -> int:
    cores = set()
    for cpu in online_cpus((root / "online").read_text()):
        topo = root / f"cpu{cpu}" / "topology"
        cores.add(((topo / "physical_package_id").read_text().strip(), (topo / "core_id").read_text().strip()))
    return len(cores)


def gpu_name() -> str | None:
    try:
        done = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                              text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    names = [line.strip() for line in done.stdout.splitlines() if line.strip()]
    return names[0] if done.returncode == 0 and names else None


def docker(*args: str, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def remove(container: str) -> None:
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM, signal.SIGHUP})
    try:
        docker("rm", "-f", container)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def http(url: str, payload: dict | None = None, timeout: float = 10) -> tuple[int, bytes]:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with DIRECT.open(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (urllib.error.URLError, OSError):
        return 0, b""


def running(name: str) -> bool:
    return docker("inspect", "-f", "{{.State.Running}}", name).stdout.strip() == "true"


def wait_ready(name: str, base: str) -> str | None:
    deadline = time.monotonic() + READY_TIMEOUT
    while time.monotonic() < deadline:
        if http(f"{base}/health", timeout=5)[0] == 200:
            return None
        if not running(name):
            tail = docker("logs", "--tail", "20", name).stderr.strip().splitlines()[-3:]
            return "server thoát trước khi sẵn sàng: " + " | ".join(tail)
        time.sleep(0.5)
    return f"server chưa sẵn sàng sau {READY_TIMEOUT} s"


def complete(base: str, n_predict: int) -> dict:
    payload = {"prompt": PROMPT, "n_predict": n_predict, "ignore_eos": True, "cache_prompt": False,
               "temperature": 0}
    status, body = http(f"{base}/completion", payload, timeout=REQUEST_TIMEOUT)
    if status != 200:
        raise RuntimeError(f"/completion trả {status}: {body[:200]!r}")
    return json.loads(body)["timings"]


def peak_rss_mb(name: str) -> int:
    pid = docker("inspect", "-f", "{{.State.Pid}}", name).stdout.strip()
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return round(int(line.split()[1]) / 1024)
    raise RuntimeError(f"không đọc được VmHWM của pid {pid}")


def bench_model(image: str, name: str, path: Path, threads: int, label: str) -> dict:
    need = -(-path.stat().st_size * NEED_FACTOR_TENTHS // (10 * 1048576))
    available = meminfo()["MemAvailable"]
    entry = {"name": name, "file": str(path), "need_mb": need, "available_mb": available}
    if need > available - RESERVE_MB:
        return {**entry, "status": "skipped_memory"}
    port = free_port()
    container = f"{label}-{name}"
    try:
        started = docker("run", "-d", "--name", container, "-p", f"127.0.0.1:{port}:8080",
                         "-v", f"{path.parent}:/models:ro", image, "-m", f"/models/{path.name}",
                         "-c", str(CTX), "-np", "1", "-t", str(threads), "--host", "0.0.0.0", "--port", "8080")
        if started.returncode != 0:
            return {**entry, "status": "failed", "detail": started.stderr.strip()[-300:]}
        base = f"http://127.0.0.1:{port}"
        problem = wait_ready(container, base)
        if problem:
            return {**entry, "status": "failed", "detail": problem}
        complete(base, 8)
        timings = [complete(base, N_PREDICT) for _ in range(RUNS)]
        tokens = sum(t["predicted_n"] for t in timings)
        seconds = sum(t["predicted_ms"] for t in timings) / 1000
        return {**entry, "status": "ok", "tokens_per_s": round(tokens / seconds, 2),
                "peak_rss_mb": peak_rss_mb(container)}
    except (RuntimeError, ValueError, KeyError) as error:
        return {**entry, "status": "failed", "detail": str(error)[:300]}
    finally:
        remove(container)


def recommend(models: list[dict]) -> str | None:
    good = [m["name"] for m in models if m["status"] == "ok" and m["tokens_per_s"] >= MIN_TOKENS_PER_S]
    return good[-1] if good else None


def parse_models(items: list[str]) -> list[tuple[str, Path]]:
    models = []
    for item in items:
        name, sep, path = item.partition("=")
        if not sep or not name or not Path(path).is_file():
            raise SystemExit(f"bench: '{item}' phải có dạng tên=đường_dẫn_gguf và tệp phải tồn tại")
        models.append((name, Path(path).resolve()))
    return models


def stop(signum, frame):
    raise KeyboardInterrupt


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Benchmark llama.cpp server trên máy khách")
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("models", nargs="+", help="tên=đường_dẫn_gguf, theo thứ tự từ nhỏ tới lớn")
    args = parser.parse_args(argv)
    models = parse_models(args.models)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    cores = physical_cores()
    label = f"bench-{os.getpid()}"
    memory = meminfo()
    results = []
    for name, path in models:
        print(f"bench: {name} ...", file=sys.stderr, flush=True)
        results.append(bench_model(args.image, name, path, cores, label))
        print(f"bench: {name} {results[-1]['status']}", file=sys.stderr, flush=True)
    report = {
        "host": {"physical_cores": cores, "mem_total_mb": memory["MemTotal"], "gpu": gpu_name()},
        "settings": {"ctx": CTX, "threads": cores, "n_predict": N_PREDICT, "runs": RUNS},
        "models": results,
        "recommended": recommend(results),
    }
    out = Path(args.out)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
