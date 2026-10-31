"""Chọn token tiếp theo từ logits: greedy, temperature, top-k, top-p, repetition penalty.

Chỉ dùng thư viện chuẩn và numpy. `logits` là mảng 1 chiều float (một số cho mỗi token trong vocab).
Token bị lọc có logit `-np.inf` (xác suất 0 sau softmax).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Xác suất softmax(logits / temperature), ổn định số (logit -inf thành xác suất 0).

    temperature <= 0 thì ValueError (greedy xử lý riêng ở sample_next).
    """
    # TODO
    raise NotImplementedError


def greedy(logits: np.ndarray) -> int:
    """Chỉ số (int Python) của logit lớn nhất; bằng nhau thì chỉ số nhỏ nhất."""
    # TODO
    raise NotImplementedError


def top_k_filter(logits: np.ndarray, k: int) -> np.ndarray:
    """Bản sao logits, giữ các logit >= logit lớn thứ k, còn lại -inf.

    Bằng giá trị ở biên thì giữ hết (có thể nhiều hơn k token). k <= 0 hoặc k >= vocab: không lọc.
    """
    # TODO
    raise NotImplementedError


def top_p_filter(logits: np.ndarray, p: float) -> np.ndarray:
    """Bản sao logits, giữ tập nhỏ nhất các token xác suất cao nhất có tổng xác suất >= p, còn lại -inf.

    Xác suất tính bằng softmax(logits) (temperature đã được áp trước đó). Luôn giữ ít nhất 1 token.
    Bằng xác suất thì token chỉ số nhỏ được xét trước. p >= 1: không lọc.
    """
    # TODO
    raise NotImplementedError


def apply_repetition_penalty(logits: np.ndarray, generated: Sequence[int], penalty: float) -> np.ndarray:
    """Repetition penalty kiểu CTRL / Hugging Face, trả bản sao.

    Với mỗi token *khác nhau* đã có trong `generated`: logit > 0 thì chia cho penalty, logit <= 0 thì nhân với
    penalty. Token lặp nhiều lần trong `generated` vẫn chỉ bị phạt một lần. penalty = 1: không đổi.
    """
    # TODO
    raise NotImplementedError


def apply_presence_frequency(logits: np.ndarray, generated: Sequence[int], presence: float = 0.0,
                             frequency: float = 0.0) -> np.ndarray:
    """Penalty kiểu OpenAI API, trả bản sao: logit[j] -= presence * [count_j > 0] + frequency * count_j.

    count_j là số lần token j có trong `generated`.
    """
    # TODO
    raise NotImplementedError


def sample_next(logits: np.ndarray, rng: np.random.Generator, *, temperature: float = 1.0, top_k: int = 0,
                top_p: float = 1.0, repetition_penalty: float = 1.0, generated: Sequence[int] = ()) -> int:
    """Chọn một token (int Python) theo đúng thứ tự xử lý của Hugging Face:

    1. repetition penalty trên `generated`;
    2. temperature == 0: trả greedy (không dùng rng);
    3. chia logits cho temperature;
    4. top-k rồi top-p;
    5. softmax rồi rút một token bằng `rng`.

    Không sửa mảng `logits` đầu vào.
    """
    # TODO
    raise NotImplementedError
