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


def quantize_groupwise(
    w: torch.Tensor, bits: int = 4, group_size: int = 128, symmetric: bool = True
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Trả `(codes, scales, zeros)` theo quy ước đầu tệp. `in_features % group_size != 0` thì ValueError."""
    # TODO
    raise NotImplementedError


def dequantize_groupwise(
    codes: torch.Tensor, scales: torch.Tensor, zeros: torch.Tensor, group_size: int
) -> torch.Tensor:
    """(code - zero) * scale cho từng nhóm; trả tensor shape như `codes`, dtype như `scales`."""
    # TODO
    raise NotImplementedError


def pack_int4(codes: torch.Tensor) -> torch.Tensor:
    """codes uint8 trong 0..15, trục cuối có độ dài chẵn -> uint8 shape (..., n // 2).

    Trục cuối lẻ hoặc có code > 15 thì ValueError.
    """
    # TODO
    raise NotImplementedError


def unpack_int4(packed: torch.Tensor) -> torch.Tensor:
    """Ngược của `pack_int4`: uint8 shape (..., m) -> uint8 shape (..., 2m)."""
    # TODO
    raise NotImplementedError


def bits_per_weight(bits: int, group_size: int, scale_bits: int = 16, zero_bits: int = 0) -> float:
    """Số bit trung bình mỗi trọng số khi mỗi nhóm lưu thêm một scale và (tuỳ chọn) một zero."""
    # TODO
    raise NotImplementedError
