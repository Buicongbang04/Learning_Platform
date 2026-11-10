import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MODELS = {"llm-small": "qwen2.5-0.5b-instruct-q4_k_m.gguf", "llm-medium": "qwen2.5-1.5b-instruct-q4_k_m.gguf"}
MEDIUM_FROM_MB = 4096
CUDA_IMAGE = "ghcr.io/ggml-org/llama.cpp:server-cuda-b11718"
KEYS = ("QUILLO_LLM_FILE", "QUILLO_LLM_MODEL", "QUILLO_LLM_THREADS", "QUILLO_EMBED_THREADS")
HEALTH_TIMEOUT = 180
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


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


def mem_total_mb(path: Path = Path("/proc/meminfo")) -> int:
    for line in path.read_text().splitlines():
        if line.startswith("MemTotal:"):
            return int(line.split()[1]) // 1024
    raise RuntimeError("không đọc được MemTotal")


def gpu_info() -> dict | None:
    try:
        done = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    for line in done.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) == 2 and parts[0]:
            try:
                return {"name": parts[0], "memory_mb": int(float(parts[1]))}
            except ValueError:
                continue
    return None


def choose(cores: int, mem_mb: int, gpu: dict | None) -> dict:
    budget = gpu["memory_mb"] if gpu else mem_mb
    model = "llm-medium" if budget >= MEDIUM_FROM_MB else "llm-small"
    return {
        "physical_cores": cores, "mem_total_mb": mem_mb, "gpu": gpu,
        "backend": "cuda" if gpu else "cpu", "n_gpu_layers": 99 if gpu else 0,
        "model": model, "llm_file": MODELS[model],
        "llm_threads": cores, "embed_threads": max(1, cores // 2),
    }


def env_values(config: dict) -> dict[str, str]:
    return {"QUILLO_LLM_FILE": config["llm_file"], "QUILLO_LLM_MODEL": config["model"],
            "QUILLO_LLM_THREADS": str(config["llm_threads"]), "QUILLO_EMBED_THREADS": str(config["embed_threads"])}


def rewrite_env(path: Path, values: dict[str, str]) -> bool:
    old = path.read_text()
    lines, seen = [], set()
    for line in old.splitlines():
        key = line.split("=", 1)[0]
        if key in values and "=" in line and not line.lstrip().startswith("#"):
            lines.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            lines.append(line)
    lines += [f"{key}={value}" for key, value in values.items() if key not in seen]
    new = "\n".join(lines) + "\n"
    if new == old:
        return False
    tmp = path.with_name(path.name + ".hw-config.tmp")
    tmp.unlink(missing_ok=True)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(new)
    os.chmod(tmp, path.stat().st_mode & 0o777)
    os.replace(tmp, path)
    return True


def place_model(quillo: Path, models_dir: Path, filename: str) -> None:
    target = quillo / "models" / filename
    if target.is_file():
        return
    source = models_dir / filename
    if not source.is_file():
        raise SystemExit(f"hw_config: thiếu {source}; chép model vào đó rồi chạy lại")
    tmp = target.with_name(f".{filename}.part")
    tmp.unlink(missing_ok=True)
    try:
        os.link(source, tmp)
    except OSError:
        shutil.copyfile(source, tmp)
    os.chmod(tmp, 0o644)
    os.replace(tmp, target)


def healthy(port: str) -> bool:
    try:
        with DIRECT.open(f"http://127.0.0.1:{port}/healthz", timeout=5) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


def dotenv(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def apply(quillo: Path, models_dir: Path, config: dict) -> None:
    env = quillo / ".env"
    if not env.is_file() or not (quillo / "compose.yaml").is_file():
        raise SystemExit(f"hw_config: {quillo} không phải thư mục cài quillo (thiếu .env hoặc compose.yaml)")
    if config["backend"] == "cuda":
        found = subprocess.run(["docker", "image", "inspect", CUDA_IMAGE], capture_output=True, text=True)
        if found.returncode != 0:
            print(f"hw_config: máy có GPU nhưng chưa có image {CUDA_IMAGE}; nạp image đó rồi chạy lại. "
                  "Không đổi gì.", file=sys.stderr)
            sys.exit(3)
    place_model(quillo, models_dir, config["llm_file"])
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM, signal.SIGHUP})
    try:
        rewrite_env(env, env_values(config))
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
    up = subprocess.run(["docker", "compose", "up", "-d"], cwd=quillo, capture_output=True, text=True, timeout=300)
    if up.returncode != 0:
        raise SystemExit(f"hw_config: docker compose up lỗi:\n{up.stderr[-2000:]}")
    port = dotenv(env).get("QUILLO_PORT", "18080")
    deadline = time.monotonic() + HEALTH_TIMEOUT
    while not healthy(port):
        if time.monotonic() > deadline:
            raise SystemExit(f"hw_config: quillo chưa trả /healthz 200 sau {HEALTH_TIMEOUT} s; xem docker compose logs llm")
        time.sleep(2)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Chọn cấu hình LLM của quillo theo phần cứng")
    parser.add_argument("--quillo", type=Path, default=Path.home() / "quillo-1.0.0")
    parser.add_argument("--models", type=Path, default=Path.home() / "models")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    config = choose(physical_cores(), mem_total_mb(), gpu_info())
    if not args.dry_run:
        apply(args.quillo, args.models, config)
    print(json.dumps(config, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
