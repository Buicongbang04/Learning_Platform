"""Simulator statevector nhỏ bằng numpy.

Quy ước thứ tự qubit giống PennyLane: wire 0 là bit **trái nhất** (quan trọng nhất) của chỉ số trạng thái.
Với n = 3, chỉ số 0b100 = 4 là trạng thái |100>: wire 0 ở |1>, wire 1 và 2 ở |0>.

Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np

# ---------- Gate một qubit cố định ----------

I = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

# CNOT trên hai wire (control, target), cơ sở |00>, |01>, |10>, |11> với control là bit trái
CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex)


# ---------- Gate quay ----------

def _rotation(pauli: np.ndarray, theta: float) -> np.ndarray:
    # exp(-i θ P / 2) = cos(θ/2) I − i sin(θ/2) P, vì P² = I
    return np.cos(theta / 2) * I - 1j * np.sin(theta / 2) * pauli


def rx(theta: float) -> np.ndarray:
    """RX(θ) = exp(−iθX/2)."""
    return _rotation(X, theta)


def ry(theta: float) -> np.ndarray:
    """RY(θ) = exp(−iθY/2)."""
    return _rotation(Y, theta)


def rz(theta: float) -> np.ndarray:
    """RZ(θ) = exp(−iθZ/2)."""
    return _rotation(Z, theta)


# ---------- Trạng thái và áp gate ----------

def zero_state(n: int) -> np.ndarray:
    """|0...0> của n qubit: vector complex dài 2**n, phần tử đầu bằng 1."""
    state = np.zeros(2**n, dtype=complex)
    state[0] = 1.0
    return state


def apply_gate(state: np.ndarray, U: np.ndarray, wires: list[int], n: int) -> np.ndarray:
    """Áp gate k qubit U (ma trận 2**k x 2**k) lên các wire `wires` (theo đúng thứ tự đó), trả trạng thái mới.

    Không tạo ma trận 2**n x 2**n: reshape trạng thái thành tensor (2,)*n, nhân U vào đúng các trục.
    Không sửa `state` truyền vào.
    """
    wires = list(wires)
    k = len(wires)
    psi = np.asarray(state, dtype=complex).reshape((2,) * n)
    # đưa các trục của `wires` lên đầu, theo đúng thứ tự trong `wires`
    psi = np.moveaxis(psi, wires, list(range(k)))
    shape = psi.shape
    psi = U.reshape(2**k, 2**k) @ psi.reshape(2**k, -1)
    psi = np.moveaxis(psi.reshape(shape), list(range(k)), wires)
    return psi.reshape(-1)


# ---------- Đo ----------

def probabilities(state: np.ndarray) -> np.ndarray:
    """Xác suất đo được từng chuỗi bit (Born rule), mảng thực dài 2**n, tổng bằng 1."""
    return np.abs(state) ** 2


def sample_counts(state: np.ndarray, shots: int, rng: np.random.Generator) -> dict[str, int]:
    """Đo `shots` lần trong cơ sở tính toán. Trả {chuỗi bit: số lần}, chỉ các chuỗi xuất hiện, wire 0 bên trái.

    Số ngẫu nhiên chỉ lấy từ `rng`.
    """
    probs = probabilities(state)
    n = int(np.log2(len(probs)))
    outcomes = rng.choice(len(probs), size=shots, p=probs / probs.sum())
    values, counts = np.unique(outcomes, return_counts=True)
    return {format(int(v), f"0{n}b"): int(c) for v, c in zip(values, counts)}


def expval_z(state: np.ndarray, wire: int, n: int) -> float:
    """<Z_wire> = P(wire đo ra 0) − P(wire đo ra 1), trả float Python."""
    probs = probabilities(state).reshape((2,) * n)
    p = np.moveaxis(probs, wire, 0).reshape(2, -1).sum(axis=1)
    return float(p[0] - p[1])
