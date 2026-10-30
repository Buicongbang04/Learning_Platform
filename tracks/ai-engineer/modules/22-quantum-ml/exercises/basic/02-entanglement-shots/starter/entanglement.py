"""Entanglement và đo bằng shots.

Trạng thái n qubit là vector complex dài 2**n, wire 0 là bit trái nhất (giống bài 01 và PennyLane).
Chia n qubit thành hai nhóm: A là `n_a` wire đầu, B là phần còn lại.

Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import math

import numpy as np


def bell_state(kind: str) -> np.ndarray:
    """Một trong bốn trạng thái Bell, vector complex dài 4.

    phi+ = (|00> + |11>)/√2, phi- = (|00> − |11>)/√2, psi+ = (|01> + |10>)/√2, psi- = (|01> − |10>)/√2.
    Tên khác thì ValueError.
    """
    # TODO
    raise NotImplementedError


def schmidt_coefficients(state: np.ndarray, n_a: int) -> np.ndarray:
    """Hệ số Schmidt của trạng thái theo cách chia A = n_a wire đầu | B = phần còn lại.

    Là các singular value của ma trận hệ số shape (2**n_a, 2**(n − n_a)), giảm dần, bỏ các giá trị < 1e-12.
    """
    # TODO
    raise NotImplementedError


def entanglement_entropy(state: np.ndarray, n_a: int) -> float:
    """Entropy von Neumann của nhóm A (đơn vị bit): −Σ λ² log2 λ², với λ là hệ số Schmidt. Trả float Python."""
    # TODO
    raise NotImplementedError


def marginal_probabilities(probs: np.ndarray, wires: list[int]) -> np.ndarray:
    """Phân phối xác suất của các wire `wires` (theo đúng thứ tự đó), cộng dồn mọi wire khác.

    `probs` dài 2**n; kết quả dài 2**len(wires), wire đầu trong `wires` là bit trái.
    """
    # TODO
    raise NotImplementedError


def expval_from_counts(counts: dict[str, int], wires: list[int]) -> float:
    """Ước lượng <Z_{w1} Z_{w2} ...> từ kết quả đo: trung bình của (−1)^(tổng các bit tại `wires`).

    `counts` là {chuỗi bit: số lần} như bài 01 (wire 0 bên trái). Trả float Python.
    """
    # TODO
    raise NotImplementedError


def shots_for_std(target_std: float, expval: float = 0.0) -> int:
    """Số shots nhỏ nhất để độ lệch chuẩn của ước lượng <P> (P là tích Pauli, giá trị ±1) không vượt target_std.

    Mỗi shot là biến ±1 có phương sai 1 − <P>², nên std = sqrt((1 − <P>²) / shots).
    """
    # TODO
    raise NotImplementedError
