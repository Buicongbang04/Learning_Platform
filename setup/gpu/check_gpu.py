"""Kiểm tra môi trường GPU: in tên GPU, VRAM, phiên bản CUDA/torch và chạy thử matmul fp16.

Chạy: uv run --project setup/gpu python setup/gpu/check_gpu.py
Thoát mã 1 nếu torch không thấy GPU.
"""
import sys

import torch


def main() -> int:
    print(f"torch {torch.__version__} | CUDA build {torch.version.cuda}")
    if not torch.cuda.is_available():
        print(
            "LỖI: torch.cuda.is_available() = False. Kiểm tra `nvidia-smi`, driver NVIDIA, "
            "và chắc chắn đang chạy bằng env setup/gpu (không phải env gốc dùng torch CPU).",
            file=sys.stderr,
        )
        return 1
    props = torch.cuda.get_device_properties(0)
    print(f"GPU: {props.name} | VRAM {props.total_memory / 1024**3:.1f} GB | sm_{props.major}{props.minor}")
    a = torch.randn(2048, 2048, device="cuda", dtype=torch.float16)
    b = torch.randn(2048, 2048, device="cuda", dtype=torch.float16)
    c = a @ b
    torch.cuda.synchronize()
    print(f"matmul fp16 2048x2048 OK, tổng = {c.float().sum().item():.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
