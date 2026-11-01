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


def _amax(t: torch.Tensor, axis: int | None) -> torch.Tensor:
    if axis is None:
        return t.amax()
    axis = axis % t.dim()
    dims = [d for d in range(t.dim()) if d != axis]
    return t.amax(dim=dims, keepdim=True) if dims else t


def _amin(t: torch.Tensor, axis: int | None) -> torch.Tensor:
    return -_amax(-t, axis)


def absmax_quantize(x: torch.Tensor, bits: int = 8, axis: int | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Đối xứng: qmax = 2^(bits-1) - 1, scale = max|x| / qmax, q = clamp(round(x / scale), -qmax, qmax).

    Trả `(q, scale)`: `q` kiểu `torch.int8`, `scale` kiểu của `x`.
    """
    qmax = 2 ** (bits - 1) - 1
    scale = _amax(x.abs(), axis) / qmax
    scale = torch.where(scale == 0, torch.ones_like(scale), scale)
    q = torch.clamp(torch.round(x / scale), -qmax, qmax).to(torch.int8)
    return q, scale


def absmax_dequantize(q: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    return q.to(scale.dtype) * scale


def zeropoint_quantize(
    x: torch.Tensor, bits: int = 8, axis: int | None = None
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Bất đối xứng: mã 0 .. 2^bits - 1, khoảng [lo, hi] luôn chứa 0 (lo = min(x_min, 0), hi = max(x_max, 0)).

    scale = (hi - lo) / (2^bits - 1), zero_point = clamp(round(-lo / scale), 0, 2^bits - 1),
    q = clamp(round(x / scale) + zero_point, 0, 2^bits - 1).
    Trả `(q, scale, zero_point)`: `q` kiểu `torch.uint8`, `zero_point` kiểu `torch.int32` cùng shape với `scale`.
    """
    qmax = 2**bits - 1
    lo = torch.clamp(_amin(x, axis), max=0)
    hi = torch.clamp(_amax(x, axis), min=0)
    scale = (hi - lo) / qmax
    scale = torch.where(scale == 0, torch.ones_like(scale), scale)
    zero_point = torch.clamp(torch.round(-lo / scale), 0, qmax)
    q = torch.clamp(torch.round(x / scale) + zero_point, 0, qmax).to(torch.uint8)
    return q, scale, zero_point.to(torch.int32)


def zeropoint_dequantize(q: torch.Tensor, scale: torch.Tensor, zero_point: torch.Tensor) -> torch.Tensor:
    return (q.to(torch.int32) - zero_point).to(scale.dtype) * scale


def sqnr_db(x: torch.Tensor, x_hat: torch.Tensor) -> float:
    """Signal-to-quantization-noise ratio: 10 log10(sum x^2 / sum (x - x_hat)^2). Không có sai số thì inf."""
    noise = float(((x - x_hat) ** 2).sum())
    if noise == 0:
        return math.inf
    return 10 * math.log10(float((x**2).sum()) / noise)
