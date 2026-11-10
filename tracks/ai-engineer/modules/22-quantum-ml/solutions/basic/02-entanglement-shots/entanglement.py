"""Entanglement và đo bằng shots.

Trạng thái n qubit là vector complex dài 2**n, wire 0 là bit trái nhất (giống bài 01 và PennyLane).
Chia n qubit thành hai nhóm: A là `n_a` wire đầu, B là phần còn lại.

Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import math

import numpy as np

_BELL = {"phi+": [1, 0, 0, 1], "phi-": [1, 0, 0, -1], "psi+": [0, 1, 1, 0], "psi-": [0, 1, -1, 0]}


def bell_state(kind: str) -> np.ndarray:
    """Một trong bốn trạng thái Bell, vector complex dài 4.

    phi+ = (|00> + |11>)/√2, phi- = (|00> − |11>)/√2, psi+ = (|01> + |10>)/√2, psi- = (|01> − |10>)/√2.
    Tên khác thì ValueError.
    """
    if kind not in _BELL:
        raise ValueError(f"không có trạng thái Bell {kind!r}")
    return np.array(_BELL[kind], dtype=complex) / np.sqrt(2)


def schmidt_coefficients(state: np.ndarray, n_a: int) -> np.ndarray:
    """Hệ số Schmidt của trạng thái theo cách chia A = n_a wire đầu | B = phần còn lại.

    Là các singular value của ma trận hệ số shape (2**n_a, 2**(n − n_a)), giảm dần, bỏ các giá trị < 1e-12.
    """
    n = int(round(math.log2(len(state))))
    M = np.asarray(state).reshape(2**n_a, 2 ** (n - n_a))
    s = np.linalg.svd(M, compute_uv=False)
    return s[s > 1e-12]


def entanglement_entropy(state: np.ndarray, n_a: int) -> float:
    """Entropy von Neumann của nhóm A (đơn vị bit): −Σ λ² log2 λ², với λ là hệ số Schmidt. Trả float Python."""
    p = schmidt_coefficients(state, n_a) ** 2
    return float(max(0.0, -(p * np.log2(p)).sum()))


def marginal_probabilities(probs: np.ndarray, wires: list[int]) -> np.ndarray:
    """Phân phối xác suất của các wire `wires` (theo đúng thứ tự đó), cộng dồn mọi wire khác.

    `probs` dài 2**n; kết quả dài 2**len(wires), wire đầu trong `wires` là bit trái.
    """
    n = int(round(math.log2(len(probs))))
    t = np.asarray(probs).reshape((2,) * n)
    others = tuple(w for w in range(n) if w not in wires)
    t = t.sum(axis=others)
    # sau khi cộng, các trục còn lại theo thứ tự tăng dần; sắp lại theo thứ tự trong `wires`
    kept = sorted(wires)
    t = np.transpose(t, [kept.index(w) for w in wires])
    return t.reshape(-1)


def expval_from_counts(counts: dict[str, int], wires: list[int]) -> float:
    """Ước lượng <Z_{w1} Z_{w2} ...> từ kết quả đo: trung bình của (−1)^(tổng các bit tại `wires`).

    `counts` là {chuỗi bit: số lần} như bài 01 (wire 0 bên trái). Trả float Python.
    """
    total = sum(counts.values())
    acc = 0
    for bits, c in counts.items():
        parity = sum(int(bits[w]) for w in wires) % 2
        acc += (-1) ** parity * c
    return float(acc / total)


def shots_for_std(target_std: float, expval: float = 0.0) -> int:
    """Số shots nhỏ nhất để độ lệch chuẩn của ước lượng <P> (P là tích Pauli, giá trị ±1) không vượt target_std.

    Mỗi shot là biến ±1 có phương sai 1 − <P>², nên std = sqrt((1 − <P>²) / shots).
    """
    var = 1.0 - expval**2
    if var <= 0:
        return 1
    return max(1, math.ceil(round(var / target_std**2, 9)))
