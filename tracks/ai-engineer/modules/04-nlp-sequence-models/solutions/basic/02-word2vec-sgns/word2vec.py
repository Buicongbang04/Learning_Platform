"""word2vec skip-gram + negative sampling (SGNS) bằng numpy."""

from collections import Counter

import numpy as np


def build_vocab(tokens: list[str], min_count: int) -> tuple[dict[str, int], np.ndarray]:
    """Từ điển các từ xuất hiện >= min_count lần, xếp theo tần suất giảm dần (hoà: theo thứ tự chữ cái).

    Trả (word2id, counts) với counts[i] là số lần xuất hiện của từ có id i, dtype int64.
    """
    freq = Counter(tokens)
    words = sorted((w for w, c in freq.items() if c >= min_count), key=lambda w: (-freq[w], w))
    return {w: i for i, w in enumerate(words)}, np.array([freq[w] for w in words], dtype=np.int64)


def keep_probs(counts: np.ndarray, t: float = 1e-4) -> np.ndarray:
    """Xác suất GIỮ mỗi từ khi subsample (công thức trong mã C word2vec): min(1, (sqrt(f/t) + 1) * t/f)."""
    f = counts / counts.sum()
    return np.minimum(1.0, (np.sqrt(f / t) + 1) * t / f)


def noise_distribution(counts: np.ndarray, power: float = 0.75) -> np.ndarray:
    """Phân phối lấy mẫu âm: tần suất mũ `power`, chuẩn hoá tổng 1."""
    p = counts.astype(np.float64) ** power
    return p / p.sum()


def skipgram_pairs(ids: np.ndarray, window: int) -> np.ndarray:
    """Mọi cặp (center, context) với 1 <= |i - j| <= window, trong một câu. Shape (P, 2), int64.

    Thứ tự: theo vị trí center i tăng dần, trong mỗi i theo j tăng dần.
    """
    ids = np.asarray(ids, dtype=np.int64)
    pairs = []
    for i in range(len(ids)):
        for j in range(max(0, i - window), min(len(ids), i + window + 1)):
            if j != i:
                pairs.append((ids[i], ids[j]))
    return np.array(pairs, dtype=np.int64).reshape(-1, 2)


def _log_sigmoid(x: np.ndarray) -> np.ndarray:
    return -np.logaddexp(0.0, -x)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return np.exp(_log_sigmoid(x))


def sgns_step(W_in: np.ndarray, W_out: np.ndarray, centers: np.ndarray, contexts: np.ndarray,
              negatives: np.ndarray, lr: float) -> float:
    """Một bước SGD trên batch, sửa W_in, W_out TẠI CHỖ. Trả loss trung bình trên batch (trước cập nhật).

    centers, contexts: (B,); negatives: (B, K).
    loss_b = -log σ(u_o · v_c) - Σ_k log σ(-u_k · v_c), v = W_in[center], u = W_out[context/negative].
    Gradient lấy theo loss trung bình; chỉ số lặp lại trong batch phải được cộng dồn.
    """
    B = len(centers)
    v = W_in[centers]                                   # (B, D)
    u_pos = W_out[contexts]                             # (B, D)
    u_neg = W_out[negatives]                            # (B, K, D)
    s_pos = np.sum(v * u_pos, axis=1)                   # (B,)
    s_neg = np.einsum("bkd,bd->bk", u_neg, v)           # (B, K)
    loss = -(_log_sigmoid(s_pos).sum() + _log_sigmoid(-s_neg).sum()) / B

    g_pos = (_sigmoid(s_pos) - 1) / B                   # dL/ds_pos
    g_neg = _sigmoid(s_neg) / B                         # dL/ds_neg
    dv = g_pos[:, None] * u_pos + np.einsum("bk,bkd->bd", g_neg, u_neg)
    du_pos = g_pos[:, None] * v
    du_neg = g_neg[:, :, None] * v[:, None, :]

    np.add.at(W_in, centers, -lr * dv)
    np.add.at(W_out, contexts, -lr * du_pos)
    np.add.at(W_out, negatives.reshape(-1), -lr * du_neg.reshape(-1, W_out.shape[1]))
    return float(loss)


def most_similar(W: np.ndarray, word2id: dict[str, int], word: str, k: int) -> list[tuple[str, float]]:
    """k từ có cosine similarity cao nhất với `word` (không tính chính nó), giảm dần."""
    id2word = {i: w for w, i in word2id.items()}
    unit = W / np.maximum(np.linalg.norm(W, axis=1, keepdims=True), 1e-12)
    sims = unit @ unit[word2id[word]]
    sims[word2id[word]] = -np.inf
    top = np.argsort(-sims, kind="stable")[:k]
    return [(id2word[i], float(sims[i])) for i in top]
