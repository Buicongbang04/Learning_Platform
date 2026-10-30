import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("vqc.ipynb")


# ---------- Mạch tham chiếu viết tay bằng numpy (để so với make_vqc) ----------

def _ry(t):
    c, s = np.cos(t / 2), np.sin(t / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def _rz(t):
    return np.diag([np.exp(-1j * t / 2), np.exp(1j * t / 2)])


CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex)


def reference_vqc(params, x):
    psi = np.zeros(4, dtype=complex)
    psi[0] = 1
    for layer in params:
        ops = []
        for w in range(2):
            ops.append(_rz(layer[w, 1]) @ _ry(layer[w, 0]) @ _ry(x[w]))
        psi = CNOT @ np.kron(ops[0], ops[1]) @ psi
    p = np.abs(psi) ** 2
    return p[0] + p[1] - p[2] - p[3]


def small_moons(n=40):
    from sklearn.datasets import make_moons

    X, y = make_moons(n_samples=n, noise=0.15, random_state=3)
    X = (X - X.min(0)) / (X.max(0) - X.min(0)) * np.pi
    return X, 2 * y - 1


# ---------- parameter_shift_jacobian ----------

def trig_fn(p):
    """Mỗi output là tổ hợp a + b cos θ_i + c sin θ_i theo từng tham số: parameter-shift đúng chính xác."""
    return np.array([np.cos(p[0]) * np.sin(p[1]) + 0.3,
                     np.sin(p[0] - 0.4) * np.cos(p[2]),
                     np.cos(p[1] + 1.1) - 2 * np.sin(p[2])])


def trig_jac(p):
    J = np.zeros((3, 3))           # [tham số, output]
    J[0] = [-np.sin(p[0]) * np.sin(p[1]), np.cos(p[0] - 0.4) * np.cos(p[2]), 0]
    J[1] = [np.cos(p[0]) * np.cos(p[1]), 0, -np.sin(p[1] + 1.1)]
    J[2] = [0, -np.sin(p[0] - 0.4) * np.sin(p[2]), -2 * np.cos(p[2])]
    return J


@pytest.mark.parametrize("shift", [np.pi / 2, np.pi / 4, 1.0])
def test_parameter_shift_exact_on_trig_functions(nb, shift):
    p = np.array([0.7, -1.3, 2.2])
    J = nb.parameter_shift_jacobian(trig_fn, p, shift=shift)
    assert J.shape == (3, 3), "shape là params.shape + output shape"
    np.testing.assert_allclose(J, trig_jac(p), atol=1e-12)


def test_parameter_shift_scalar_output_and_param_shape(nb):
    p = np.array([[0.3, -0.9], [1.4, 0.2]])

    def f(q):
        return float(np.cos(q[0, 0]) * np.sin(q[1, 1]) + np.sin(q[0, 1]))

    J = nb.parameter_shift_jacobian(f, p)
    assert J.shape == (2, 2)
    expected = np.array([[-np.sin(0.3) * np.sin(0.2), np.cos(-0.9)], [0.0, np.cos(0.3) * np.cos(0.2)]])
    np.testing.assert_allclose(J, expected, atol=1e-12)


def test_parameter_shift_calls_and_no_mutation(nb):
    p = np.array([0.1, 0.2, 0.3, 0.4])
    before = p.copy()
    seen = []

    def f(q):
        seen.append(q.copy())
        return np.sin(q).sum()

    nb.parameter_shift_jacobian(f, p)
    np.testing.assert_array_equal(p, before)
    assert 2 * p.size <= len(seen) <= 2 * p.size + 1
    shifted = [q for q in seen if not np.array_equal(q, before)]
    assert len(shifted) == 2 * p.size
    for q in shifted:
        diff = q - before
        assert np.count_nonzero(diff) == 1, "mỗi lần chỉ dịch đúng một tham số"
        assert np.isclose(abs(diff).max(), np.pi / 2)


def test_parameter_shift_on_pennylane_qnode(nb):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=2)

    @qml.qnode(dev)
    def circuit(p):
        qml.RX(p[0], wires=0)
        qml.RY(p[1], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RZ(p[2], wires=1)
        qml.RY(p[3], wires=1)
        return qml.expval(qml.PauliZ(1))

    p = np.array([0.4, -0.8, 1.2, 0.5])
    J = nb.parameter_shift_jacobian(lambda q: float(circuit(q)), p)
    eps = 1e-6
    fd = np.array([(float(circuit(p + eps * e)) - float(circuit(p - eps * e))) / (2 * eps) for e in np.eye(4)])
    np.testing.assert_allclose(J, fd, atol=1e-7)


# ---------- make_vqc ----------

@pytest.mark.parametrize("L", [1, 3])
def test_make_vqc_matches_reference(nb, L):
    rng = np.random.default_rng(L)
    params = rng.uniform(-np.pi, np.pi, size=(L, 2, 2))
    X = rng.uniform(0, np.pi, size=(5, 2))
    out = nb.make_vqc(L)(params, X)
    assert isinstance(out, np.ndarray) and out.shape == (5,)
    assert out.dtype.kind == "f"
    np.testing.assert_allclose(out, [reference_vqc(params, x) for x in X], atol=1e-10)


def test_make_vqc_exposes_qnode(nb):
    params = np.random.default_rng(9).uniform(-np.pi, np.pi, size=(2, 2, 2))
    X = np.array([[0.3, 1.2], [2.0, 0.1]])
    model = nb.make_vqc(2)
    assert callable(getattr(model, "circuit", None)), "gắn QNode gốc vào model.circuit"
    np.testing.assert_allclose(np.asarray(model.circuit(params, X), dtype=float), model(params, X), atol=1e-12)


def test_make_vqc_single_row_batch(nb):
    params = np.full((2, 2, 2), 0.5)
    out = nb.make_vqc(2)(params, np.array([[0.3, 1.2]]))
    assert out.shape == (1,)
    assert out[0] == pytest.approx(reference_vqc(params, [0.3, 1.2]))


# ---------- loss_and_grad, train_vqc ----------

def test_loss_and_grad_matches_finite_differences(nb):
    X, y = small_moons(12)
    model = nb.make_vqc(2)
    params = np.random.default_rng(7).uniform(-np.pi, np.pi, size=(2, 2, 2))
    loss, grad = nb.loss_and_grad(model, params, X, y)
    assert isinstance(loss, float)
    preds = np.array([reference_vqc(params, x) for x in X])
    assert loss == pytest.approx(np.mean((preds - y) ** 2))
    assert grad.shape == params.shape

    def ref_loss(p):
        return np.mean((np.array([reference_vqc(p, x) for x in X]) - y) ** 2)

    eps = 1e-6
    fd = np.zeros_like(params)
    for idx in np.ndindex(params.shape):
        e = np.zeros_like(params)
        e[idx] = eps
        fd[idx] = (ref_loss(params + e) - ref_loss(params - e)) / (2 * eps)
    np.testing.assert_allclose(grad, fd, atol=1e-7)


def test_train_vqc_follows_spec(nb):
    X, y = small_moons(40)
    model = nb.make_vqc(2)
    params, hist = nb.train_vqc(model, X, y, n_layers=2, steps=15, lr=0.3, seed=5)
    assert params.shape == (2, 2, 2)
    assert len(hist) == 15
    # history[0] là loss tại điểm khởi tạo U(−π, π) với seed 5
    p0 = np.random.default_rng(5).uniform(-np.pi, np.pi, size=(2, 2, 2))
    assert hist[0] == pytest.approx(np.mean((np.array([reference_vqc(p0, x) for x in X]) - y) ** 2))
    # đúng một bước gradient descent từ p0
    _, g0 = nb.loss_and_grad(model, p0, X, y)
    p1 = p0 - 0.3 * g0
    assert hist[1] == pytest.approx(np.mean((np.array([reference_vqc(p1, x) for x in X]) - y) ** 2))
    assert hist[-1] < hist[0]
    one_step, _ = nb.train_vqc(model, X, y, n_layers=2, steps=1, lr=0.3, seed=5)
    np.testing.assert_allclose(one_step, p1, atol=1e-10, err_msg="khởi tạo U(−π, π) từ default_rng(seed), rồi một bước GD")
    again, hist2 =nb.train_vqc(model, X, y, n_layers=2, steps=15, lr=0.3, seed=5)
    np.testing.assert_allclose(again, params)


def test_train_vqc_learns_moons(nb):
    X, y = small_moons(40)
    model = nb.make_vqc(3)
    params, hist = nb.train_vqc(model, X, y, n_layers=3, steps=40, lr=0.3, seed=0)
    acc = np.mean(np.sign(model(params, X)) == y)
    assert hist[-1] < 0.6 * hist[0]
    assert acc >= 0.85, f"train accuracy {acc:.3f}"
