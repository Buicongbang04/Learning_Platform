"""Quantization số nguyên tự cài: absmax (đối xứng) và zero-point (bất đối xứng), per-tensor hoặc per-channel.

Quy ước chung:
- `axis=None`: một scale cho cả tensor (scale là tensor 0 chiều).
- `axis=k`: một scale cho mỗi chỉ số dọc trục `k` (per-channel); scale có cùng số chiều với `x`, kích thước 1 ở mọi trục
  trừ trục `k`, để broadcast thẳng với `x`.
- Làm tròn bằng `torch.round` (làm tròn nửa về số chẵn), rồi kẹp vào khoảng mã hợp lệ.
- Kênh (hoặc tensor) toàn số 0 dùng scale 1.0 để không chia cho 0.
"""

from __future__ import annotations

import math

import torch


def absmax_quantize(x: torch.Tensor, bits: int = 8, axis: int | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Đối xứng: qmax = 2^(bits-1) - 1, scale = max|x| / qmax, q = clamp(round(x / scale), -qmax, qmax).

    Trả `(q, scale)`: `q` kiểu `torch.int8`, `scale` kiểu của `x`.
    """
    # TODO
    raise NotImplementedError


def absmax_dequantize(q: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    # TODO: trả tensor cùng dtype với scale
    raise NotImplementedError


def zeropoint_quantize(
    x: torch.Tensor, bits: int = 8, axis: int | None = None
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Bất đối xứng: mã 0 .. 2^bits - 1, khoảng [lo, hi] luôn chứa 0 (lo = min(x_min, 0), hi = max(x_max, 0)).

    scale = (hi - lo) / (2^bits - 1), zero_point = clamp(round(-lo / scale), 0, 2^bits - 1),
    q = clamp(round(x / scale) + zero_point, 0, 2^bits - 1).
    Trả `(q, scale, zero_point)`: `q` kiểu `torch.uint8`, `zero_point` kiểu `torch.int32` cùng shape với `scale`.
    """
    # TODO
    raise NotImplementedError


def zeropoint_dequantize(q: torch.Tensor, scale: torch.Tensor, zero_point: torch.Tensor) -> torch.Tensor:
    # TODO: cẩn thận phép trừ trên uint8
    raise NotImplementedError


def sqnr_db(x: torch.Tensor, x_hat: torch.Tensor) -> float:
    """Signal-to-quantization-noise ratio: 10 log10(sum x^2 / sum (x - x_hat)^2). Không có sai số thì inf."""
    # TODO
    raise NotImplementedError
