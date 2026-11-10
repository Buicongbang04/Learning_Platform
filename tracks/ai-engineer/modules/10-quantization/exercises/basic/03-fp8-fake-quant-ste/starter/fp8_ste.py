"""Mô phỏng fp8 (E4M3, E5M2) và fake quantization có straight-through estimator (STE).

Không ép kiểu sang các dtype fp8 có sẵn của PyTorch trong tệp này: mục đích là tự dựng lưới số fp8.

fp8 theo chuẩn OCP: E4M3 (4 bit mũ, 3 bit mantissa, bias 7, lớn nhất 448), E5M2 (5 bit mũ, 2 bit mantissa, bias 15,
lớn nhất 57344). Có số subnormal. `fp8_round` làm tròn tới số fp8 gần nhất (hoà thì về mantissa chẵn) và **bão hoà**:
giá trị vượt quá số lớn nhất thành ±số lớn nhất (không ra inf).
"""

from __future__ import annotations

import torch

FP8_FORMATS = {
    "e4m3": {"exp_bits": 4, "man_bits": 3, "bias": 7, "max": 448.0},
    "e5m2": {"exp_bits": 5, "man_bits": 2, "bias": 15, "max": 57344.0},
}


def fp8_round(x: torch.Tensor, fmt: str = "e4m3") -> torch.Tensor:
    """Trả tensor float32 cùng shape, mỗi phần tử là số fp8 gần nhất của `x` (bão hoà, giữ dấu, 0 vẫn là 0)."""
    # TODO: dùng FP8_FORMATS[fmt]
    raise NotImplementedError


class FakeQuantSTE(torch.autograd.Function):
    """Forward: dequantize(quantize(x)) đối xứng `bits` bit với `scale` cho trước (broadcast được với x).

    Backward (clipped STE): gradient theo x đi thẳng qua ở chỗ |x / scale| <= qmax, bằng 0 ở chỗ bị kẹp; không có
    gradient cho scale và bits.
    """

    @staticmethod
    def forward(ctx, x: torch.Tensor, scale: torch.Tensor, bits: int) -> torch.Tensor:
        # TODO: lưu những gì backward cần bằng ctx.save_for_backward
        raise NotImplementedError

    @staticmethod
    def backward(ctx, grad: torch.Tensor):
        # TODO: trả một giá trị cho mỗi input của forward (x, scale, bits)
        raise NotImplementedError


def fake_quant(x: torch.Tensor, scale: torch.Tensor, bits: int) -> torch.Tensor:
    return FakeQuantSTE.apply(x, scale, bits)


def absmax_scale_per_channel(w: torch.Tensor, bits: int) -> torch.Tensor:
    """Scale absmax cho mỗi hàng của `w` (shape (out, 1)), tách khỏi graph; hàng toàn 0 dùng 1.0."""
    # TODO
    raise NotImplementedError
