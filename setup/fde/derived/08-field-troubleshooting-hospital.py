"""Module 08 (xử lý sự cố tại hiện trường): `hospital` (3072 MB) đang chạy quillo 1.0.0 bằng compose
(`~/quillo-1.0.0`, `llm-small`, `QUILLO_BIND=0.0.0.0` để cổng forward của QEMU tới được api), inbox rỗng. Máy không có
plugin compose: bản cài mang binary compose v5.6.1 đã ghim vào `~/.docker/cli-plugins/` của `fde`.

Dựng từ bundle `tracks/fde/product/dist/quillo-1.0.0.tar` bằng `08-field-troubleshooting-hospital.sh`."""

import hashlib
from pathlib import Path

PROFILE = "hospital"
VERSION = "1.0.0"
BUNDLE = Path("tracks/fde/product/dist/quillo-1.0.0.tar")
SCRIPT = Path("setup/fde/derived/08-field-troubleshooting-hospital.sh")
COMPOSE = Path("data/raw/fde-tools/docker-compose-v5.6.1/docker-compose-linux-x86_64")
COMPOSE_SHA256 = "47737f4236e6d3ccea7291995203f8f018058783b4c3a9469119811a0b5db8c0"
INPUTS = [BUNDLE, SCRIPT, COMPOSE_SHA256]
SITE = False
MEMORY_MB = 3072


def build(target):
    import fdekit

    compose = fdekit.ROOT / COMPOSE
    if not compose.is_file() or hashlib.sha256(compose.read_bytes()).hexdigest() != COMPOSE_SHA256:
        raise RuntimeError(f"Thiếu {COMPOSE} đúng sha256 {COMPOSE_SHA256}; tải theo mục '0. Cài đặt' của module 03")
    target.ssh("mkdir -p ~/.docker/cli-plugins", timeout=60, check=True)
    target.put(compose, "/home/fde/.docker/cli-plugins/docker-compose")
    target.put(fdekit.ROOT / BUNDLE, f"/home/fde/quillo-{VERSION}.tar")
    target.put(fdekit.ROOT / SCRIPT, "/home/fde/quillo-compose.sh")
    done = target.ssh(f"chmod 0755 ~/.docker/cli-plugins/docker-compose && sh /home/fde/quillo-compose.sh {VERSION} "
                      "&& rm /home/fde/quillo-compose.sh", timeout=900)
    if done.returncode != 0:
        raise RuntimeError(f"quillo-compose.sh lỗi ({done.returncode}):\n{done.stdout[-3000:]}\n{done.stderr[-3000:]}")
