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
    if temperature <= 0:
        raise ValueError("temperature phải > 0; temperature = 0 nghĩa là greedy")
    z = np.asarray(logits, dtype=np.float64) / temperature
    z = z - np.max(z)                      # trừ max: exp không tràn, kết quả không đổi
    e = np.exp(z)                          # exp(-inf) = 0
    return e / e.sum()


def greedy(logits: np.ndarray) -> int:
    """Chỉ số (int Python) của logit lớn nhất; bằng nhau thì chỉ số nhỏ nhất."""
    return int(np.argmax(logits))          # argmax trả chỉ số đầu tiên khi bằng nhau


def top_k_filter(logits: np.ndarray, k: int) -> np.ndarray:
    """Bản sao logits, giữ các logit >= logit lớn thứ k, còn lại -inf.

    Bằng giá trị ở biên thì giữ hết (có thể nhiều hơn k token). k <= 0 hoặc k >= vocab: không lọc.
    """
    out = np.array(logits, dtype=np.float64, copy=True)
    if k <= 0 or k >= out.size:
        return out
    kth = np.sort(out)[-k]                 # logit lớn thứ k
    out[out < kth] = -np.inf               # bằng kth vẫn giữ
    return out


def top_p_filter(logits: np.ndarray, p: float) -> np.ndarray:
    """Bản sao logits, giữ tập nhỏ nhất các token xác suất cao nhất có tổng xác suất >= p, còn lại -inf.

    Xác suất tính bằng softmax(logits) (temperature đã được áp trước đó). Luôn giữ ít nhất 1 token.
    Bằng xác suất thì token chỉ số nhỏ được xét trước. p >= 1: không lọc.
    """
    out = np.array(logits, dtype=np.float64, copy=True)
    if p >= 1.0:
        return out
    probs = softmax(out)
    order = np.argsort(-probs, kind="stable")          # giảm dần, bằng nhau thì chỉ số nhỏ trước
    cum = np.cumsum(probs[order])
    n_keep = int(np.searchsorted(cum, p) + 1)          # token đầu tiên làm tổng chạm p cũng được giữ
    n_keep = min(max(n_keep, 1), out.size)
    out[order[n_keep:]] = -np.inf
    return out


def apply_repetition_penalty(logits: np.ndarray, generated: Sequence[int], penalty: float) -> np.ndarray:
    """Repetition penalty kiểu CTRL / Hugging Face, trả bản sao.

    Với mỗi token *khác nhau* đã có trong `generated`: logit > 0 thì chia cho penalty, logit <= 0 thì nhân với
    penalty. Token lặp nhiều lần trong `generated` vẫn chỉ bị phạt một lần. penalty = 1: không đổi.
    """
    out = np.array(logits, dtype=np.float64, copy=True)
    if penalty == 1.0 or len(generated) == 0:
        return out
    ids = np.unique(np.asarray(generated, dtype=np.int64))   # mỗi token phạt một lần
    vals = out[ids]
    out[ids] = np.where(vals > 0, vals / penalty, vals * penalty)
    return out


def apply_presence_frequency(logits: np.ndarray, generated: Sequence[int], presence: float = 0.0,
                             frequency: float = 0.0) -> np.ndarray:
    """Penalty kiểu OpenAI API, trả bản sao: logit[j] -= presence * [count_j > 0] + frequency * count_j.

    count_j là số lần token j có trong `generated`.
    """
    out = np.array(logits, dtype=np.float64, copy=True)
    if len(generated) == 0:
        return out
    counts = np.bincount(np.asarray(generated, dtype=np.int64), minlength=out.size)[: out.size]
    out -= presence * (counts > 0) + frequency * counts
    return out


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
    z = apply_repetition_penalty(logits, generated, repetition_penalty)
    if temperature == 0:
        return greedy(z)
    z = z / temperature
    z = top_k_filter(z, top_k)
    z = top_p_filter(z, top_p)
    probs = softmax(z)
    return int(rng.choice(probs.size, p=probs))
