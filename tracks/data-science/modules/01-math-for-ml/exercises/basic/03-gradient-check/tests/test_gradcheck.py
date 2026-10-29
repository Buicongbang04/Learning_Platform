import numpy as np
import pytest
from sklearn.metrics import log_loss

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def gc():
    return ex.module("gradcheck.py")


def make_data(n: int = 300, d: int = 4, seed: int = 0):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(n), rng.normal(size=(n, d - 1))])
    w_true = rng.normal(size=d)
    y_reg = X @ w_true + rng.normal(0, 0.5, n)
    y_cls = (rng.random(n) < 1 / (1 + np.exp(-X @ w_true))).astype(float)
    return X, y_reg, y_cls, rng.normal(size=d)


def test_numerical_gradient_known_functions(gc):
    x = np.array([1.0, -2.0, 3.0])
    assert gc.numerical_gradient(lambda v: np.sum(v ** 2), x) == pytest.approx(2 * x, abs=1e-6)
    f = lambda v: np.sin(v[0]) * v[1] ** 2          # ∂/∂v0 = cos(v0) v1², ∂/∂v1 = 2 sin(v0) v1
    x = np.array([0.7, 1.3])
    expected = np.array([np.cos(0.7) * 1.3 ** 2, 2 * np.sin(0.7) * 1.3])
    assert gc.numerical_gradient(f, x) == pytest.approx(expected, abs=1e-8)


def test_numerical_gradient_is_central_difference(gc):
    # f(x) = x³ tại x = 1: sai phân tiến cho 3 + 3h, sai phân trung tâm cho 3 + h² → phân biệt được với h = 1e-3
    g = gc.numerical_gradient(lambda v: v[0] ** 3, np.array([1.0]), eps=1e-3)
    assert g[0] == pytest.approx(3 + 1e-6, abs=1e-9)


def test_numerical_gradient_does_not_modify_input(gc):
    x = np.array([1.0, 2.0, 3.0])
    gc.numerical_gradient(lambda v: np.sum(v ** 3), x)
    assert np.array_equal(x, [1.0, 2.0, 3.0])


def test_relative_error(gc):
    a = np.array([1.0, 2.0, 3.0])
    assert gc.relative_error(a, a) == 0.0
    assert gc.relative_error(a, 1.01 * a) == pytest.approx(0.01 / 2.01, rel=1e-9)
    assert gc.relative_error(np.zeros(3), np.zeros(3)) == 0.0     # không chia cho 0


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_mse_loss_and_gradient(gc, seed):
    X, y, _, w = make_data(seed=seed)
    loss, grad = gc.mse_loss_grad(w, X, y)
    assert loss == pytest.approx(np.mean((X @ w - y) ** 2))
    numeric = gc.numerical_gradient(lambda v: gc.mse_loss_grad(v, X, y)[0], w)
    assert gc.relative_error(grad, numeric) < 1e-7


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_logistic_loss_and_gradient(gc, seed):
    X, _, y, w = make_data(seed=seed)
    loss, grad = gc.logistic_loss_grad(w, X, y)
    assert loss == pytest.approx(log_loss(y, 1 / (1 + np.exp(-X @ w))), rel=1e-9)
    numeric = gc.numerical_gradient(lambda v: gc.logistic_loss_grad(v, X, y)[0], w)
    assert gc.relative_error(grad, numeric) < 1e-7


def test_gradient_check_catches_a_bug(gc):
    X, y, _, w = make_data(seed=3)
    _, grad = gc.mse_loss_grad(w, X, y)
    numeric = gc.numerical_gradient(lambda v: gc.mse_loss_grad(v, X, y)[0], w)
    buggy = grad / 2                     # quên hệ số 2 khi đạo hàm bình phương: lỗi kinh điển
    assert gc.relative_error(buggy, numeric) > 0.1


def test_logistic_loss_is_numerically_stable(gc):
    X = np.array([[1.0, 50.0], [1.0, -50.0], [1.0, 0.0]])
    y = np.array([0.0, 1.0, 1.0])
    w = np.array([0.0, 20.0])            # logit ±1000: sigmoid ngây thơ cho log(0)
    loss, grad = gc.logistic_loss_grad(w, X, y)
    assert np.isfinite(loss) and np.all(np.isfinite(grad))
    assert loss == pytest.approx((1000 + 1000 + np.log(2)) / 3, rel=1e-9)
