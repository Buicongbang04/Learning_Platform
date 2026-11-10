import argparse
import json
import os
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
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def meminfo() -> dict[str, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, rest = line.split(":", 1)
        values[key] = int(rest.split()[0]) // 1024
    return values


def physical_cores() -> int:
    out = subprocess.run(["lscpu", "-p=CORE,SOCKET"], capture_output=True, text=True, check=True).stdout
    return len({line for line in out.splitlines() if line and not line.startswith("#")})


def gpu_name() -> str | None:
    try:
        done = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                              text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    names = [line.strip() for line in done.stdout.splitlines() if line.strip()]
    return names[0] if done.returncode == 0 and names else None


def docker(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def post(url: str, payload: dict) -> dict:
    request = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with DIRECT.open(request, timeout=120) as response:
        return json.load(response)


def wait_ready(base: str) -> None:
    for _ in range(360):
        try:
            with DIRECT.open(f"{base}/health", timeout=5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{base} chưa sẵn sàng")


def bench(base: str) -> float:
    body = {"prompt": PROMPT, "ignore_eos": True, "cache_prompt": False, "temperature": 0}
    post(f"{base}/completion", dict(body, n_predict=8))
    runs = [post(f"{base}/completion", dict(body, n_predict=N_PREDICT))["timings"] for _ in range(RUNS)]
    return round(sum(r["predicted_n"] for r in runs) / (sum(r["predicted_ms"] for r in runs) / 1000), 2)


def peak_rss_mb(name: str) -> int:
    pid = docker("inspect", "-f", "{{.State.Pid}}", name).stdout.strip()
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return round(int(line.split()[1]) / 1024)
    raise RuntimeError(f"không đọc được VmHWM của pid {pid}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Benchmark llama.cpp server")
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("models", nargs="+", help="tên=đường_dẫn_gguf, theo thứ tự từ nhỏ tới lớn")
    args = parser.parse_args(argv)
    cores = physical_cores()
    servers = []
    try:
        for item in args.models:
            name, _, path = item.partition("=")
            path = Path(path).resolve()
            port = free_port()
            container = f"bench-{os.getpid()}-{name}"
            docker("run", "-d", "--name", container, "-p", f"127.0.0.1:{port}:8080", "-v", f"{path.parent}:/models:ro",
                   args.image, "-m", f"/models/{path.name}", "-c", str(CTX), "-np", "1", "-t", str(cores),
                   "--host", "0.0.0.0", "--port", "8080")
            servers.append((name, path, container, f"http://127.0.0.1:{port}"))
        for _, _, _, base in servers:
            wait_ready(base)
        results = []
        for name, path, container, base in servers:
            results.append({"name": name, "file": str(path), "status": "ok", "tokens_per_s": bench(base),
                            "peak_rss_mb": peak_rss_mb(container)})
    finally:
        for _, _, container, _ in servers:
            docker("rm", "-f", container)
    good = [r["name"] for r in results if r["tokens_per_s"] >= MIN_TOKENS_PER_S]
    report = {
        "host": {"physical_cores": cores, "mem_total_mb": meminfo()["MemTotal"], "gpu": gpu_name()},
        "settings": {"ctx": CTX, "threads": cores, "n_predict": N_PREDICT, "runs": RUNS},
        "models": results,
        "recommended": good[-1] if good else None,
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
