import argparse
import json
import sys
from pathlib import Path

MODELS = {"llm-small": "qwen2.5-0.5b-instruct-q4_k_m.gguf", "llm-medium": "qwen2.5-1.5b-instruct-q4_k_m.gguf"}


def physical_cores(root: Path = Path("/sys/devices/system/cpu")) -> int:
    """Số core vật lý trong các CPU đang online, đọc từ cây sysfs `root`."""
    raise NotImplementedError("TODO")


def mem_total_mb(path: Path = Path("/proc/meminfo")) -> int:
    raise NotImplementedError("TODO")


def gpu_info() -> dict | None:
    """{"name", "memory_mb"} của GPU đầu tiên dùng được, hoặc None."""
    raise NotImplementedError("TODO")


def choose(cores: int, mem_mb: int, gpu: dict | None) -> dict:
    raise NotImplementedError("TODO: bảng quy tắc trong README")


def rewrite_env(path: Path, values: dict[str, str]) -> bool:
    raise NotImplementedError("TODO: đặt các khoá, giữ nguyên mọi byte khác")


def apply(quillo: Path, models_dir: Path, config: dict) -> None:
    raise NotImplementedError("TODO: đặt model, sửa .env, docker compose up -d, chờ /healthz")


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
