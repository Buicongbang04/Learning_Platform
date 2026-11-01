"""Tiền xử lý trước khi đưa media vào model: audio về mono float32 16 kHz, chọn frame video,
ước lượng số token ảnh của vision LLM, dựng message đa phương thức của LangChain."""

from __future__ import annotations

import base64
import math

import numpy as np
from langchain_core.messages import HumanMessage


def to_mono_float32(x: np.ndarray) -> np.ndarray:
    """PCM int16/int32/uint8 hoặc float, mono (n,) hoặc nhiều kênh (n, ch) -> float32 (n,) trong [-1, 1]."""
    # TODO
    raise NotImplementedError


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Đổi tần số lấy mẫu có lọc chống aliasing; độ dài ceil(len * sr_out / sr_in)."""
    # TODO
    raise NotImplementedError


def sample_frame_indices(n_frames: int, fps: float, *, num: int | None = None,
                         every_s: float | None = None) -> list[int]:
    """Chỉ số frame: `num` frame ở tâm `num` đoạn bằng nhau, hoặc một frame mỗi `every_s` giây từ t = 0."""
    # TODO
    raise NotImplementedError


def vlm_image_tokens(width: int, height: int, *, factor: int = 32, min_pixels: int = 64 * 32 * 32,
                     max_pixels: int = 2048 * 32 * 32) -> int:
    """Số token ảnh kiểu Qwen-VL: làm tròn cạnh về bội của `factor`, giữ diện tích trong [min_pixels, max_pixels]."""
    # TODO
    raise NotImplementedError


def lc_user_message(text: str, images: list[tuple[bytes, str]] = (),
                    audio: list[tuple[bytes, str]] = ()) -> HumanMessage:
    """HumanMessage với content block chuẩn của langchain-core 1.x: text trước, rồi ảnh, rồi audio (base64)."""
    # TODO
    raise NotImplementedError
