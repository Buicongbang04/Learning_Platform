"""Module 05 (GPU ở máy khách): factory đang chạy quillo 1.0.0 (compose, llm-small) và có sẵn llm-medium ở ~/models.

Dựng từ bundle `tracks/fde/product/dist/quillo-1.0.0.tar` bằng `05-gpu-field-quillo.sh`. netem của xưởng bị tắt trong
lúc chép bundle và model (dịch vụ `fde-netem` bật lại ở lần boot sau)."""

from pathlib import Path

PROFILE = "factory"
VERSION = "1.0.0"
BUNDLE = Path("tracks/fde/product/dist/quillo-1.0.0.tar")
SCRIPT = Path("setup/fde/derived/05-gpu-field-quillo.sh")
MEDIUM_SHA256 = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
INPUTS = [BUNDLE, SCRIPT, MEDIUM_SHA256]
SITE = False
MEMORY_MB = None


def build(target):
    import fdekit

    root = fdekit.ROOT
    if fdekit.MODELS["llm-medium"].sha256 != MEDIUM_SHA256:
        raise RuntimeError("fdekit.MODELS['llm-medium'] đã đổi; cập nhật MEDIUM_SHA256 trong " + __file__)
    target.ssh("dev=$(ip -o route get 10.0.2.2 | sed -n 's/.* dev \\([^ ]*\\).*/\\1/p'); "
               "sudo -n systemctl stop fde-netem; sudo -n /usr/sbin/tc qdisc del dev \"$dev\" root || true",
               timeout=60, check=True)
    target.put(root / BUNDLE, f"/home/fde/quillo-{VERSION}.tar")
    target.put(root / SCRIPT, "/home/fde/quillo-compose.sh")
    done = target.ssh(f"sh /home/fde/quillo-compose.sh {VERSION} && rm /home/fde/quillo-compose.sh", timeout=600)
    if done.returncode != 0:
        raise RuntimeError(f"quillo-compose.sh lỗi ({done.returncode}):\n{done.stdout[-3000:]}\n{done.stderr[-3000:]}")
    medium = fdekit.fetch_model("llm-medium")
    target.put(medium, f"/home/fde/models/{medium.name}")
