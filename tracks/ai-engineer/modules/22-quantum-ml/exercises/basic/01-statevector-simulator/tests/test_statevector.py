from functools import reduce

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def sv():
    return ex.module("statevector.py")


def kron(*mats):
    return reduce(np.kron, mats)


def basis(bits: str) -> np.ndarray:
    """|bits> với wire 0 là ký tự trái nhất."""
    v = np.zeros(2 ** len(bits), dtype=complex)
    v[int(bits, 2)] = 1
    return v


# ---------- Gate ----------

def test_fixed_gates(sv):
    np.testing.assert_allclose(sv.X @ basis("0"), basis("1"))
    np.testing.assert_allclose(sv.Z @ basis("1"), -basis("1"))
    np.testing.assert_allclose(sv.Y @ basis("0"), 1j * basis("1"))
    np.testing.assert_allclose(sv.H @ basis("0"), (basis("0") + basis("1")) / np.sqrt(2))
    np.testing.assert_allclose(sv.I, np.eye(2))
    # CNOT: control là wire đầu (bit trái)
    np.testing.assert_allclose(sv.CNOT @ basis("10"), basis("11"))
    np.testing.assert_allclose(sv.CNOT @ basis("01"), basis("01"))
    for U in (sv.X, sv.Y, sv.Z, sv.H, sv.CNOT):
        np.testing.assert_allclose(U.conj().T @ U, np.eye(len(U)), atol=1e-12)


@pytest.mark.parametrize("theta", [0.3, -1.2, 2.5])
def test_rotations_are_half_angle_exponentials(sv, theta):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    np.testing.assert_allclose(sv.rx(theta), [[c, -1j * s], [-1j * s, c]], atol=1e-12)
    np.testing.assert_allclose(sv.ry(theta), [[c, -s], [s, c]], atol=1e-12)
    np.testing.assert_allclose(sv.rz(theta), np.diag([np.exp(-1j * theta / 2), np.exp(1j * theta / 2)]), atol=1e-12)


def test_rotation_by_pi_is_pauli_up_to_phase(sv):
    # RX(π) = −iX: góc trong exp là θ/2, quay 2π mới về −I
    np.testing.assert_allclose(sv.rx(np.pi), -1j * sv.X, atol=1e-12)
    np.testing.assert_allclose(sv.ry(2 * np.pi), -np.eye(2), atol=1e-12)


# ---------- Trạng thái và apply_gate ----------

def test_zero_state(sv):
    s = sv.zero_state(3)
    assert s.shape == (8,)
    assert np.iscomplexobj(s)
    np.testing.assert_allclose(s, basis("000"))


def test_wire_zero_is_leftmost_bit(sv):
    s = sv.apply_gate(sv.zero_state(3), sv.X, [0], 3)
    np.testing.assert_allclose(s, basis("100"), err_msg="wire 0 là bit trái nhất: X trên wire 0 cho |100> = chỉ số 4")
    s = sv.apply_gate(sv.zero_state(3), sv.X, [2], 3)
    np.testing.assert_allclose(s, basis("001"))


def test_single_qubit_gate_matches_kron(sv):
    rng = np.random.default_rng(0)
    psi = rng.normal(size=16) + 1j * rng.normal(size=16)
    psi /= np.linalg.norm(psi)
    U = sv.ry(0.7) @ sv.rz(-0.4)
    ours = sv.apply_gate(psi, U, [1], 4)
    ref = kron(np.eye(2), U, np.eye(2), np.eye(2)) @ psi
    np.testing.assert_allclose(ours, ref, atol=1e-12)


@pytest.mark.parametrize("wires", [[0, 1], [1, 0], [0, 2], [2, 0]])
def test_cnot_on_any_wire_pair(sv, wires):
    # |110> rồi CNOT(control, target): chỉ đổi bit target khi bit control là 1
    s = sv.apply_gate(basis("110"), sv.CNOT, wires, 3)
    bits = list("110")
    c, t = wires
    if bits[c] == "1":
        bits[t] = "0" if bits[t] == "1" else "1"
    np.testing.assert_allclose(s, basis("".join(bits)), err_msg=f"CNOT với wires={wires}")


def test_two_qubit_gate_matches_kron_with_wire_order(sv):
    rng = np.random.default_rng(1)
    U, _ = np.linalg.qr(rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4)))
    psi = rng.normal(size=8) + 1j * rng.normal(size=8)
    psi /= np.linalg.norm(psi)
    # U trên wires [2, 0]: hoán vị wire để (2, 0) thành hai bit trái, áp kron(U, I), hoán vị lại
    P = np.zeros((8, 8))
    for i in range(8):
        b = format(i, "03b")
        P[int(b[2] + b[0] + b[1], 2), i] = 1  # (w0, w1, w2) -> (w2, w0, w1)
    ref = P.T @ kron(U, np.eye(2)) @ P @ psi
    np.testing.assert_allclose(sv.apply_gate(psi, U, [2, 0], 3), ref, atol=1e-12)


def test_apply_gate_does_not_modify_input(sv):
    s = sv.zero_state(2)
    before = s.copy()
    sv.apply_gate(s, sv.H, [0], 2)
    np.testing.assert_array_equal(s, before)


def test_apply_gate_scales_without_full_matrix(sv):
    # 20 qubit: ma trận đầy đủ 2^20 x 2^20 cần 16 TB; reshape thành tensor thì vài MB
    n = 20
    s = sv.apply_gate(sv.zero_state(n), sv.H, [7], n)
    assert abs(s[0]) == pytest.approx(1 / np.sqrt(2))
    assert abs(s[1 << (n - 1 - 7)]) == pytest.approx(1 / np.sqrt(2))


def test_random_circuit_matches_pennylane(sv):
    qml = pytest.importorskip("pennylane")
    rng = np.random.default_rng(2)
    angles = rng.uniform(-np.pi, np.pi, size=(3, 3))
    n = 3
    dev = qml.device("default.qubit", wires=n)

    @qml.qnode(dev)
    def circuit():
        for w in range(n):
            qml.Hadamard(w)
            qml.RX(angles[0, w], w)
        qml.CNOT([0, 2])
        for w in range(n):
            qml.RY(angles[1, w], w)
            qml.RZ(angles[2, w], w)
        qml.CNOT([2, 1])
        qml.PauliY(0)
        return qml.state()

    s = sv.zero_state(n)
    for w in range(n):
        s = sv.apply_gate(s, sv.H, [w], n)
        s = sv.apply_gate(s, sv.rx(angles[0, w]), [w], n)
    s = sv.apply_gate(s, sv.CNOT, [0, 2], n)
    for w in range(n):
        s = sv.apply_gate(s, sv.ry(angles[1, w]), [w], n)
        s = sv.apply_gate(s, sv.rz(angles[2, w]), [w], n)
    s = sv.apply_gate(s, sv.CNOT, [2, 1], n)
    s = sv.apply_gate(s, sv.Y, [0], n)
    np.testing.assert_allclose(s, np.asarray(circuit()), atol=1e-10)


# ---------- Đo ----------

def test_probabilities_born_rule(sv):
    s = np.array([0.6, 0.0, 0.8j, 0.0])
    p = sv.probabilities(s)
    np.testing.assert_allclose(p, [0.36, 0.0, 0.64, 0.0])
    assert not np.iscomplexobj(p)


def test_expval_z_per_wire(sv):
    # RY(θ)|0> có <Z> = cos θ; wire 1 giữ |0> nên <Z> = 1
    s = sv.apply_gate(sv.zero_state(2), sv.ry(1.1), [0], 2)
    assert sv.expval_z(s, 0, 2) == pytest.approx(np.cos(1.1))
    assert sv.expval_z(s, 1, 2) == pytest.approx(1.0)
    assert isinstance(sv.expval_z(s, 0, 2), float)
    t = sv.apply_gate(basis("011"), sv.ry(0.4), [2], 3)
    assert sv.expval_z(t, 0, 3) == pytest.approx(1.0)
    assert sv.expval_z(t, 1, 3) == pytest.approx(-1.0)
    assert sv.expval_z(t, 2, 3) == pytest.approx(-np.cos(0.4))


def test_sample_counts_format_and_statistics(sv):
    # RY(2) trên wire 0 rồi CNOT: cos(1)|00> + sin(1)|11>, chỉ '00' và '11' có xác suất khác 0
    s = sv.apply_gate(sv.zero_state(2), sv.ry(2.0), [0], 2)
    s = sv.apply_gate(s, sv.CNOT, [0, 1], 2)
    counts = sv.sample_counts(s, 10_000, np.random.default_rng(0))
    assert set(counts) <= {"00", "11"}, "chỉ trả các chuỗi có xuất hiện; '01', '10' có xác suất 0"
    assert sum(counts.values()) == 10_000
    assert all(isinstance(v, int) for v in counts.values())
    p11 = np.sin(1.0) ** 2
    std = np.sqrt(p11 * (1 - p11) / 10_000)
    assert abs(counts["11"] / 10_000 - p11) < 5 * std
    again = sv.sample_counts(s, 10_000, np.random.default_rng(0))
    assert counts == again, "chỉ lấy số ngẫu nhiên từ rng"


def test_sample_counts_bitstring_order(sv):
    counts = sv.sample_counts(basis("100"), 7, np.random.default_rng(0))
    assert counts == {"100": 7}, "wire 0 là ký tự trái nhất của chuỗi bit"
