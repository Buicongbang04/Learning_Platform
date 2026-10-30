from functools import reduce

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("qkernel.ipynb")


# ---------- Feature map ZZ tham chiếu viết tay bằng numpy ----------

H1 = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def _rz(t):
    return np.diag([np.exp(-1j * t / 2), np.exp(1j * t / 2)])


def _on(U, w, n):
    mats = [np.eye(2)] * n
    mats[w] = U
    return reduce(np.kron, mats)


def _cnot(c, t, n):
    P0, P1 = np.diag([1, 0]), np.diag([0, 1])
    X = np.array([[0, 1], [1, 0]])
    a = [np.eye(2)] * n
    a[c] = P0
    b = [np.eye(2)] * n
    b[c] = P1
    b[t] = X
    return reduce(np.kron, a) + reduce(np.kron, b)


def reference_state(x, reps):
    n = len(x)
    psi = np.zeros(2**n, dtype=complex)
    psi[0] = 1
    for _ in range(reps):
        for w in range(n):
            psi = _on(_rz(x[w]) @ H1, w, n) @ psi
        for w in range(n - 1):
            psi = _cnot(w, w + 1, n) @ _on(_rz(x[w] * x[w + 1]), w + 1, n) @ _cnot(w, w + 1, n) @ psi
    return psi


# ---------- feature_states ----------

@pytest.mark.parametrize("n,reps", [(1, 1), (2, 2), (3, 1), (3, 2)])
def test_feature_states_match_reference(nb, n, reps):
    X = np.random.default_rng(n * 10 + reps).uniform(-1.5, 1.5, size=(4, n))
    S = nb.feature_states(X, reps=reps)
    assert S.shape == (4, 2**n)
    assert np.iscomplexobj(S)
    np.testing.assert_allclose(np.linalg.norm(S, axis=1), 1.0, atol=1e-10)
    for x, s in zip(X, S):
        overlap = abs(np.vdot(reference_state(x, reps), s))
        assert overlap == pytest.approx(1.0, abs=1e-9), "statevector khác mạch ZZ của đề (sai thứ tự gate hoặc wire?)"


def test_feature_states_default_reps_is_two(nb):
    X = np.array([[0.4, -0.9, 1.3]])
    S = nb.feature_states(X)
    assert abs(np.vdot(reference_state(X[0], 2), S[0])) == pytest.approx(1.0, abs=1e-9)


# ---------- kernel_matrix ----------

def test_kernel_matrix_matches_reference(nb):
    rng = np.random.default_rng(0)
    A, B = rng.uniform(-1, 1, size=(4, 3)), rng.uniform(-1, 1, size=(5, 3))
    K = nb.kernel_matrix(A, B)
    assert K.shape == (4, 5)
    assert not np.iscomplexobj(K)
    ref = np.array([[abs(np.vdot(reference_state(a, 2), reference_state(b, 2))) ** 2 for b in B] for a in A])
    np.testing.assert_allclose(K, ref, atol=1e-10)


def test_kernel_matrix_is_valid_gram(nb):
    X = np.random.default_rng(1).uniform(-2, 2, size=(7, 2))
    K = nb.kernel_matrix(X, X)
    np.testing.assert_allclose(np.diag(K), 1.0, atol=1e-10)
    np.testing.assert_allclose(K, K.T, atol=1e-12)
    assert np.linalg.eigvalsh(K).min() > -1e-10
    assert (K >= -1e-12).all() and (K <= 1 + 1e-12).all()


def test_kernel_matrix_uses_reps(nb):
    X = np.random.default_rng(2).uniform(-1, 1, size=(3, 2))
    K1 = nb.kernel_matrix(X, X, reps=1)
    ref = np.array([[abs(np.vdot(reference_state(a, 1), reference_state(b, 1))) ** 2 for b in X] for a in X])
    np.testing.assert_allclose(K1, ref, atol=1e-10)


# ---------- kernel_target_alignment ----------

def test_alignment_of_ideal_kernel_is_one(nb):
    y = np.array([0, 0, 1, 2, 2, 1, 0])
    K = (y[:, None] == y[None, :]).astype(float)        # kernel "lý tưởng": 1 nếu cùng lớp, 0 nếu khác
    a = nb.kernel_target_alignment(K, y)
    assert isinstance(a, float)
    assert a == pytest.approx(1.0)


def test_alignment_is_centered(nb):
    rng = np.random.default_rng(3)
    Z = rng.normal(size=(8, 3))
    K = Z @ Z.T
    y = np.array([1, -1, 1, 1, -1, -1, 1, -1])
    a = nb.kernel_target_alignment(K, y)
    # cộng hằng số vào mọi phần tử không đổi alignment đã center
    assert nb.kernel_target_alignment(K + 5.0, y) == pytest.approx(a, abs=1e-10)
    m = len(y)
    Hc = np.eye(m) - 1 / m
    T = np.where(y[:, None] == y[None, :], 1.0, -1.0)
    Kc, Tc = Hc @ K @ Hc, Hc @ T @ Hc
    assert a == pytest.approx(np.sum(Kc * Tc) / (np.linalg.norm(Kc) * np.linalg.norm(Tc)))


def test_alignment_scale_invariant_and_detects_bad_kernel(nb):
    y = np.array([0, 0, 0, 1, 1, 1])
    good = np.where(y[:, None] == y[None, :], 0.9, 0.1)
    bad = np.where(y[:, None] == y[None, :], 0.1, 0.9)
    np.fill_diagonal(bad, 1.0)
    assert nb.kernel_target_alignment(3 * good, y) == pytest.approx(nb.kernel_target_alignment(good, y))
    assert nb.kernel_target_alignment(good, y) > 0.9
    assert nb.kernel_target_alignment(bad, y) < 0


# ---------- sample_kernel ----------

def test_sample_kernel_statistics(nb):
    K = np.array([[1.0, 0.3], [0.3, 1.0 + 1e-12]])     # có phần tử lệch nhẹ trên 1 do làm tròn: phải cắt về [0, 1]
    est = nb.sample_kernel(K, 200, np.random.default_rng(0))
    assert est.shape == K.shape
    assert np.allclose(est * 200, np.round(est * 200)), "mỗi phần tử là (số lần ra toàn 0) / shots"
    assert est[0, 0] == 1.0
    many = np.stack([nb.sample_kernel(K, 200, np.random.default_rng(s))[0, 1] for s in range(400)])
    assert many.mean() == pytest.approx(0.3, abs=0.01)
    assert many.std() == pytest.approx(np.sqrt(0.3 * 0.7 / 200), rel=0.15)


def test_sample_kernel_uses_rng(nb):
    K = np.full((3, 3), 0.5)
    a = nb.sample_kernel(K, 50, np.random.default_rng(1))
    b = nb.sample_kernel(K, 50, np.random.default_rng(1))
    np.testing.assert_array_equal(a, b)
    assert len(np.unique(a)) > 1, "mỗi phần tử ước lượng độc lập"
