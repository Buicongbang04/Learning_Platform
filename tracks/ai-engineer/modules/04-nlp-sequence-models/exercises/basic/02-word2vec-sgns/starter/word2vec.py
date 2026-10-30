"""word2vec skip-gram + negative sampling (SGNS) bằng numpy."""

from collections import Counter

import numpy as np


def build_vocab(tokens: list[str], min_count: int) -> tuple[dict[str, int], np.ndarray]:
    """Từ điển các từ xuất hiện >= min_count lần, xếp theo tần suất giảm dần (hoà: theo thứ tự chữ cái).

    Trả (word2id, counts) với counts[i] là số lần xuất hiện của từ có id i, dtype int64.
    """
    # TODO
    raise NotImplementedError


def keep_probs(counts: np.ndarray, t: float = 1e-4) -> np.ndarray:
    """Xác suất GIỮ mỗi từ khi subsample (công thức trong mã C word2vec): min(1, (sqrt(f/t) + 1) * t/f)."""
    # TODO: f là tần suất tương đối của từ
    raise NotImplementedError


def noise_distribution(counts: np.ndarray, power: float = 0.75) -> np.ndarray:
    """Phân phối lấy mẫu âm: tần suất mũ `power`, chuẩn hoá tổng 1."""
    # TODO
    raise NotImplementedError


def skipgram_pairs(ids: np.ndarray, window: int) -> np.ndarray:
    """Mọi cặp (center, context) với 1 <= |i - j| <= window, trong một câu. Shape (P, 2), int64.

    Thứ tự: theo vị trí center i tăng dần, trong mỗi i theo j tăng dần.
    """
    # TODO
    raise NotImplementedError


def sgns_step(W_in: np.ndarray, W_out: np.ndarray, centers: np.ndarray, contexts: np.ndarray,
              negatives: np.ndarray, lr: float) -> float:
    """Một bước SGD trên batch, sửa W_in, W_out TẠI CHỖ. Trả loss trung bình trên batch (trước cập nhật).

    centers, contexts: (B,); negatives: (B, K).
    loss_b = -log σ(u_o · v_c) - Σ_k log σ(-u_k · v_c), v = W_in[center], u = W_out[context/negative].
    Gradient lấy theo loss trung bình; chỉ số lặp lại trong batch phải được cộng dồn.
    """
    # TODO: forward (điểm dương, điểm âm, loss ổn định số), gradient theo v, u_o, u_k, cập nhật bằng np.add.at
    raise NotImplementedError


def most_similar(W: np.ndarray, word2id: dict[str, int], word: str, k: int) -> list[tuple[str, float]]:
    """k từ có cosine similarity cao nhất với `word` (không tính chính nó), giảm dần."""
    # TODO
    raise NotImplementedError
