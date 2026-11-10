"""int4 group-wise và đóng gói 2 giá trị 4 bit vào một byte.

Quy ước:
- Trọng số `w` shape `(out_features, in_features)` như `nn.Linear.weight`. Nhóm (group) là `group_size` cột liền nhau
  trên **cùng một hàng**: nhóm g của hàng r là `w[r, g*group_size:(g+1)*group_size]`. `in_features` không chia hết
  cho `group_size` thì `ValueError`.
- Mã (code) luôn là số không dấu 0 .. 2^bits - 1, kiểu `torch.uint8`; giải lượng tử: `(code - zero) * scale`.
  - Đối xứng: qmax = 2^(bits-1) - 1, scale = max|w| của nhóm / qmax, zero = 2^(bits-1) (hằng),
    code = clamp(round(w / scale), -qmax, qmax) + zero.
  - Bất đối xứng: như zero-point của bài Basic 01 trên từng nhóm (khoảng [lo, hi] chứa 0, zero làm tròn và kẹp).
  - Nhóm toàn 0 dùng scale 1.0.
- `scales` và `zeros` shape `(out_features, in_features // group_size)`; `scales` cùng dtype với `w`, `zeros` kiểu
  `torch.int32`.
- Đóng gói: byte thứ i của một hàng chứa code `2i` ở 4 bit thấp và code `2i + 1` ở 4 bit cao.
"""

from __future__ import annotations

import torch


def _grouped(w: torch.Tensor, group_size: int) -> torch.Tensor:
    out_f, in_f = w.shape
    if in_f % group_size:
        raise ValueError(f"in_features {in_f} không chia hết cho group_size {group_size}")
    return w.reshape(out_f, in_f // group_size, group_size)


def quantize_groupwise(
    w: torch.Tensor, bits: int = 4, group_size: int = 128, symmetric: bool = True
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    g = _grouped(w, group_size)
    if symmetric:
        qmax = 2 ** (bits - 1) - 1
        scales = g.abs().amax(dim=-1) / qmax
        scales = torch.where(scales == 0, torch.ones_like(scales), scales)
        zeros = torch.full_like(scales, 2 ** (bits - 1), dtype=torch.int32)
        codes = torch.clamp(torch.round(g / scales[..., None]), -qmax, qmax) + zeros[..., None]
    else:
        qmax = 2**bits - 1
        lo = torch.clamp(g.amin(dim=-1), max=0)
        hi = torch.clamp(g.amax(dim=-1), min=0)
        scales = (hi - lo) / qmax
        scales = torch.where(scales == 0, torch.ones_like(scales), scales)
        zeros = torch.clamp(torch.round(-lo / scales), 0, qmax)
        codes = torch.clamp(torch.round(g / scales[..., None]) + zeros[..., None], 0, qmax)
        zeros = zeros.to(torch.int32)
    return codes.reshape(w.shape).to(torch.uint8), scales, zeros


def dequantize_groupwise(
    codes: torch.Tensor, scales: torch.Tensor, zeros: torch.Tensor, group_size: int
) -> torch.Tensor:
    g = _grouped(codes.to(torch.int32), group_size)
    return ((g - zeros[..., None]).to(scales.dtype) * scales[..., None]).reshape(codes.shape)


def pack_int4(codes: torch.Tensor) -> torch.Tensor:
    """codes uint8 trong 0..15, trục cuối có độ dài chẵn -> uint8 shape (..., n // 2)."""
    if codes.shape[-1] % 2:
        raise ValueError("trục cuối phải có độ dài chẵn")
    if codes.numel() and int(codes.max()) > 15:
        raise ValueError("code int4 phải nằm trong 0..15")
    c = codes.to(torch.uint8)
    return c[..., 0::2] | (c[..., 1::2] << 4)


def unpack_int4(packed: torch.Tensor) -> torch.Tensor:
    """Ngược của `pack_int4`: uint8 shape (..., m) -> uint8 shape (..., 2m)."""
    low = packed & 0x0F
    high = packed >> 4
    return torch.stack([low, high], dim=-1).reshape(*packed.shape[:-1], 2 * packed.shape[-1])


def bits_per_weight(bits: int, group_size: int, scale_bits: int = 16, zero_bits: int = 0) -> float:
    """Số bit trung bình mỗi trọng số khi mỗi nhóm lưu thêm một scale và (tuỳ chọn) một zero."""
    return bits + (scale_bits + zero_bits) / group_size
