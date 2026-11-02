import re

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("benchmark.ipynb")


# ---------- angle_kernel_classical ----------

def _angle_state(x):
    psi = np.array([1.0 + 0j])
    for t in x:
        psi = np.kron(psi, [np.cos(t / 2), np.sin(t / 2)])     # RY(t)|0>
    return psi


def test_angle_kernel_matches_statevector(nb):
    rng = np.random.default_rng(0)
    A, B = rng.uniform(-np.pi, np.pi, (5, 3)), rng.uniform(-np.pi, np.pi, (4, 3))
    K = nb.angle_kernel_classical(A, B)
    assert K.shape == (5, 4)
    ref = np.array([[abs(np.vdot(_angle_state(a), _angle_state(b))) ** 2 for b in B] for a in A])
    np.testing.assert_allclose(K, ref, atol=1e-12)


def test_angle_kernel_large_dimension_is_cheap(nb):
    # 40 "qubit": statevector cần 2^40 phần tử; công thức đóng thì tức thì
    rng = np.random.default_rng(1)
    X = rng.uniform(-0.3, 0.3, (6, 40))
    K = nb.angle_kernel_classical(X, X)
    np.testing.assert_allclose(np.diag(K), 1.0)
    assert np.linalg.eigvalsh(K).min() > -1e-12
    assert K[0, 1] == pytest.approx(np.prod(np.cos((X[0] - X[1]) / 2) ** 2))


# ---------- gradient_variance ----------

def test_gradient_variance_one_qubit(nb):
    # C = cos θ_RY nên dC/dθ = −sin θ, θ ~ U(0, 2π): phương sai 1/2
    v = nb.gradient_variance(1, 1, "global", n_samples=4000, seed=0)
    assert isinstance(v, float)
    assert v == pytest.approx(0.5, abs=0.03)


def test_gradient_variance_matches_pennylane(nb):
    qml = pytest.importorskip("pennylane")
    n, L, S, seed = 3, 2, 12, 4
    theta = np.random.default_rng(seed).uniform(0, 2 * np.pi, size=(S, L, n, 2))
    dev = qml.device("default.qubit", wires=n)

    def make(cost):
        @qml.qnode(dev)
        def circuit(t):
            for l in range(L):
                for w in range(n):
                    qml.RY(t[l, w, 0], wires=w)
                    qml.RZ(t[l, w, 1], wires=w)
                for w in range(n - 1):
                    qml.CZ(wires=[w, w + 1])
            obs = qml.prod(*[qml.PauliZ(w) for w in range(n)]) if cost == "global" else qml.PauliZ(0)
            return qml.expval(obs)
        return circuit

    for cost in ("global", "local"):
        circuit = make(cost)
        grads = []
        for t in theta:
            p, m = t.copy(), t.copy()
            p[0, 0, 0] += np.pi / 2
            m[0, 0, 0] -= np.pi / 2
            grads.append((float(circuit(p)) - float(circuit(m))) / 2)
        ours = nb.gradient_variance(n, L, cost, n_samples=S, seed=seed)
        assert ours == pytest.approx(np.var(grads), abs=1e-10), f"cost={cost}"


def test_global_cost_has_barren_plateau(nb):
    v2 = nb.gradient_variance(2, 5, "global", n_samples=300, seed=1)
    v8 = nb.gradient_variance(8, 5, "global", n_samples=300, seed=1)
    assert v8 < v2 / 16, f"global: n=2 {v2:.2e}, n=8 {v8:.2e}"
    # một layer, cost local: phương sai gần như không đổi theo n
    l8 = nb.gradient_variance(8, 1, "local", n_samples=300, seed=1)
    assert l8 > 0.3


def test_gradient_variance_seeded(nb):
    a = nb.gradient_variance(4, 3, "local", n_samples=50, seed=7)
    b = nb.gradient_variance(4, 3, "local", n_samples=50, seed=7)
    c = nb.gradient_variance(4, 3, "local", n_samples=50, seed=8)
    assert a == b and a != c


# ---------- paired_ci ----------

def test_paired_ci_values(nb):
    a = [0.90, 0.80, 0.85, 0.95, 0.90]
    b = [0.85, 0.80, 0.80, 0.90, 0.88]
    r = nb.paired_ci(a, b)
    d = np.subtract(a, b)
    assert set(r) == {"mean_diff", "std_diff", "ci_low", "ci_high"}
    assert all(isinstance(v, float) for v in r.values())
    assert r["mean_diff"] == pytest.approx(d.mean())
    assert r["std_diff"] == pytest.approx(d.std(ddof=1))
    half = 2.7764451051977987 * d.std(ddof=1) / np.sqrt(5)       # t_{0.975, 4}
    assert r["ci_low"] == pytest.approx(d.mean() - half)
    assert r["ci_high"] == pytest.approx(d.mean() + half)


def test_paired_ci_confidence_and_sign(nb):
    a = [0.70, 0.72, 0.69, 0.71, 0.70, 0.73]
    b = [0.80, 0.79, 0.82, 0.80, 0.81, 0.80]
    r95, r99 = nb.paired_ci(a, b), nb.paired_ci(a, b, confidence=0.99)
    assert r95["ci_high"] < 0, "a kém hơn b rõ ràng: cả khoảng tin cậy âm"
    assert r99["ci_high"] - r99["ci_low"] > r95["ci_high"] - r95["ci_low"]


# ---------- MEMO.md ----------

def test_memo_written():
    doc = ex.read("MEMO.md")
    assert "TODO" not in doc, "còn TODO trong MEMO.md"
    words = len(re.findall(r"\w+", doc))
    assert words >= 500, f"MEMO.md mới có {words} từ, cần ít nhất 500"
    for heading in ["## Khuyến nghị", "## Bằng chứng", "## Khi nào nên xem lại"]:
        assert heading in doc, f"thiếu mục {heading}"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng số"
