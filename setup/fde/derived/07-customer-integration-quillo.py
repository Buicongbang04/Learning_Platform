"""Module 07 (tích hợp với hệ thống của khách): lab-open đang chạy quillo 1.0.0 (compose, llm-small), chưa bật SSO,
inbox rỗng, api publish trên 0.0.0.0:18080 của VM (để cổng forward của QEMU tới được).

Dựng từ bundle `tracks/fde/product/dist/quillo-1.0.0.tar` bằng `07-customer-integration-quillo.sh`."""

from pathlib import Path

PROFILE = "lab-open"
VERSION = "1.0.0"
BUNDLE = Path("tracks/fde/product/dist/quillo-1.0.0.tar")
SCRIPT = Path("setup/fde/derived/07-customer-integration-quillo.sh")
INPUTS = [BUNDLE, SCRIPT]
SITE = False
MEMORY_MB = 3072


def build(target):
    import fdekit

    target.put(fdekit.ROOT / BUNDLE, f"/home/fde/quillo-{VERSION}.tar")
    target.put(fdekit.ROOT / SCRIPT, "/home/fde/quillo-compose.sh")
    done = target.ssh(f"sh /home/fde/quillo-compose.sh {VERSION} && rm /home/fde/quillo-compose.sh", timeout=600)
    if done.returncode != 0:
        raise RuntimeError(f"quillo-compose.sh lỗi ({done.returncode}):\n{done.stdout[-3000:]}\n{done.stderr[-3000:]}")
