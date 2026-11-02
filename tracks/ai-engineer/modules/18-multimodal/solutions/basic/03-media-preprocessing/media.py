"""Tiền xử lý trước khi đưa media vào model: audio về mono float32 16 kHz, chọn frame video,
ước lượng số token ảnh của vision LLM, dựng message đa phương thức của LangChain."""

from __future__ import annotations

import base64
import math
from fractions import Fraction

import numpy as np
from langchain_core.messages import HumanMessage
from scipy.signal import resample_poly


def to_mono_float32(x: np.ndarray) -> np.ndarray:
    """PCM int16/int32/uint8 hoặc float, mono (n,) hoặc nhiều kênh (n, ch) -> float32 (n,) trong [-1, 1]."""
    x = np.asarray(x)
    if x.dtype == np.int16:
        y = x.astype(np.float32) / 32768.0
    elif x.dtype == np.int32:
        y = x.astype(np.float32) / 2147483648.0
    elif x.dtype == np.uint8:
        y = (x.astype(np.float32) - 128.0) / 128.0
    elif np.issubdtype(x.dtype, np.floating):
        y = x.astype(np.float32)
    else:
        raise ValueError(f"không hỗ trợ dtype {x.dtype}")
    if y.ndim == 2:
        y = y.mean(axis=1, dtype=np.float32)
    elif y.ndim != 1:
        raise ValueError("audio phải có dạng (n,) hoặc (n, ch)")
    return y


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Đổi tần số lấy mẫu có lọc chống aliasing; độ dài ceil(len * sr_out / sr_in)."""
    if sr_in <= 0 or sr_out <= 0:
        raise ValueError("tần số lấy mẫu phải dương")
    x = np.asarray(x, dtype=np.float32)
    if sr_in == sr_out:
        return x.copy()
    ratio = Fraction(sr_out, sr_in)
    return resample_poly(x, ratio.numerator, ratio.denominator).astype(np.float32)


def sample_frame_indices(n_frames: int, fps: float, *, num: int | None = None,
                         every_s: float | None = None) -> list[int]:
    """Chỉ số frame: `num` frame ở tâm `num` đoạn bằng nhau, hoặc một frame mỗi `every_s` giây từ t = 0."""
    if (num is None) == (every_s is None):
        raise ValueError("chỉ truyền đúng một trong num, every_s")
    if n_frames <= 0:
        return []
    if num is not None:
        if num < 1:
            raise ValueError("num phải >= 1")
        if num >= n_frames:
            return list(range(n_frames))
        return [int((i + 0.5) * n_frames / num) for i in range(num)]
    if every_s <= 0 or fps <= 0:
        raise ValueError("every_s và fps phải dương")
    duration = n_frames / fps
    out, k = set(), 0
    while k * every_s < duration - 1e-9:
        out.add(min(n_frames - 1, int(math.floor(k * every_s * fps + 1e-9))))
        k += 1
    return sorted(out)


def vlm_image_tokens(width: int, height: int, *, factor: int = 32, min_pixels: int = 64 * 32 * 32,
                     max_pixels: int = 2048 * 32 * 32) -> int:
    """Số token ảnh kiểu Qwen-VL: làm tròn cạnh về bội của `factor`, giữ diện tích trong [min_pixels, max_pixels]."""
    if width <= 0 or height <= 0:
        raise ValueError("kích thước ảnh phải dương")
    if max(width, height) / min(width, height) > 200:
        raise ValueError("tỉ lệ cạnh vượt 200")
    h_bar = max(factor, round(height / factor) * factor)
    w_bar = max(factor, round(width / factor) * factor)
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt(height * width / max_pixels)
        h_bar = max(factor, math.floor(height / beta / factor) * factor)
        w_bar = max(factor, math.floor(width / beta / factor) * factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = math.ceil(height * beta / factor) * factor
        w_bar = math.ceil(width * beta / factor) * factor
    return (h_bar // factor) * (w_bar // factor)


def lc_user_message(text: str, images: list[tuple[bytes, str]] = (),
                    audio: list[tuple[bytes, str]] = ()) -> HumanMessage:
    """HumanMessage với content block chuẩn của langchain-core 1.x: text trước, rồi ảnh, rồi audio (base64)."""
    blocks: list[dict] = [{"type": "text", "text": text}]
    for kind, items in (("image", images), ("audio", audio)):
        for data, mime in items:
            if not mime.startswith(kind + "/"):
                raise ValueError(f"mime {mime!r} không phải {kind}/*")
            blocks.append({"type": kind, "base64": base64.b64encode(data).decode("ascii"), "mime_type": mime})
    return HumanMessage(content=blocks)
