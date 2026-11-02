"""Simulator statevector nhỏ bằng numpy.

Quy ước thứ tự qubit giống PennyLane: wire 0 là bit **trái nhất** (quan trọng nhất) của chỉ số trạng thái.
Với n = 3, chỉ số 0b100 = 4 là trạng thái |100>: wire 0 ở |1>, wire 1 và 2 ở |0>.

Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np

# ---------- Gate một qubit cố định ----------
# Ma trận 2x2 dtype complex, theo cơ sở (|0>, |1>).

I = np.eye(2, dtype=complex)
X = None  # TODO: Pauli X (NOT)
Y = None  # TODO: Pauli Y
Z = None  # TODO: Pauli Z
H = None  # TODO: Hadamard

# TODO: CNOT 4x4 trên hai wire (control, target), cơ sở |00>, |01>, |10>, |11> với control là bit trái
CNOT = None


# ---------- Gate quay ----------

def rx(theta: float) -> np.ndarray:
    """RX(θ) = exp(−iθX/2)."""
    # TODO
    raise NotImplementedError


def ry(theta: float) -> np.ndarray:
    """RY(θ) = exp(−iθY/2)."""
    # TODO
    raise NotImplementedError


def rz(theta: float) -> np.ndarray:
    """RZ(θ) = exp(−iθZ/2)."""
    # TODO
    raise NotImplementedError


# ---------- Trạng thái và áp gate ----------

def zero_state(n: int) -> np.ndarray:
    """|0...0> của n qubit: vector complex dài 2**n, phần tử đầu bằng 1."""
    # TODO
    raise NotImplementedError


def apply_gate(state: np.ndarray, U: np.ndarray, wires: list[int], n: int) -> np.ndarray:
    """Áp gate k qubit U (ma trận 2**k x 2**k) lên các wire `wires` (theo đúng thứ tự đó), trả trạng thái mới.

    Không tạo ma trận 2**n x 2**n: reshape trạng thái thành tensor (2,)*n, nhân U vào đúng các trục.
    Không sửa `state` truyền vào.
    """
    # TODO
    raise NotImplementedError


# ---------- Đo ----------

def probabilities(state: np.ndarray) -> np.ndarray:
    """Xác suất đo được từng chuỗi bit (Born rule), mảng thực dài 2**n, tổng bằng 1."""
    # TODO
    raise NotImplementedError


def sample_counts(state: np.ndarray, shots: int, rng: np.random.Generator) -> dict[str, int]:
    """Đo `shots` lần trong cơ sở tính toán. Trả {chuỗi bit: số lần}, chỉ các chuỗi xuất hiện, wire 0 bên trái.

    Số ngẫu nhiên chỉ lấy từ `rng`.
    """
    # TODO
    raise NotImplementedError


def expval_z(state: np.ndarray, wire: int, n: int) -> float:
    """<Z_wire> = P(wire đo ra 0) − P(wire đo ra 1), trả float Python."""
    # TODO
    raise NotImplementedError
