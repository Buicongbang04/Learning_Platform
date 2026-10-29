import numpy as np
import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def gc():
    return ex.module("gradcheck.py")


def _logsumexp(x: np.ndarray) -> float:
    m = x.max()
    return float(m + np.log(np.exp(x - m).sum()))


def test_relative_error_formula(gc):
    a = np.array([1.0, 2.0])
    b = np.array([1.0, 3.0])
    # max|a-b| = 1, max|a| + max|b| = 2 + 3 = 5
    assert gc.relative_error(a, b) == pytest.approx(0.2)
    assert isinstance(gc.relative_error(a, b), float)


def test_relative_error_is_scale_free_and_safe_at_zero(gc):
    a = np.array([[1e-8, -3e-8], [2e-8, 0.0]])
    b = a * 1.001
    assert gc.relative_error(a, b) == pytest.approx(gc.relative_error(a * 1e8, b * 1e8))
    assert gc.relative_error(np.zeros(3), np.zeros(3)) == 0.0


def test_cubic_sum_matches_analytic(gc):
    x = np.random.default_rng(0).normal(size=(3, 4))
    numeric = gc.numerical_grad(lambda v: float(np.sum(v**3)), x)
    assert numeric.shape == x.shape
    assert gc.relative_error(numeric, 3 * x**2) < 1e-7


def test_logsumexp_matches_analytic_and_torch(gc):
    x = np.random.default_rng(1).normal(0, 2, size=7)
    numeric = gc.numerical_grad(_logsumexp, x)
    e = np.exp(x - x.max())
    assert gc.relative_error(numeric, e / e.sum()) < 1e-7
    t = torch.tensor(x, requires_grad=True)
    torch.logsumexp(t, dim=0).backward()
    assert gc.relative_error(numeric, t.grad.numpy()) < 1e-7


def test_input_unchanged_after_call(gc):
    x = np.random.default_rng(2).normal(size=(4, 5))
    before = x.copy()
    gc.numerical_grad(lambda v: float(np.sum(np.sin(v) * v)), x)
    # bằng nhau từng bit: cộng rồi trừ eps không trả về đúng số cũ, phải lưu và gán lại giá trị gốc
    assert np.array_equal(x, before)


def test_f_sees_only_one_coordinate_perturbed(gc):
    x = np.arange(6, dtype=float).reshape(2, 3)
    x_orig = x.copy()
    seen = []

    def f(v):
        seen.append(np.count_nonzero(v != x_orig))
        return float(v.sum())

    gc.numerical_grad(f, x, eps=1e-3)
    assert len(seen) == 2 * x.size
    assert max(seen) == 1


def test_eps_argument_is_used(gc):
    # f(x) = x^3: sai phân trung tâm cho 3x^2 + eps^2 đúng, nên eps lớn để lại dấu vết đo được
    x = np.array([1.0])
    g = gc.numerical_grad(lambda v: float(v[0] ** 3), x, eps=0.1)
    assert g[0] == pytest.approx(3.0 + 0.01, abs=1e-9)


def test_detects_wrong_gradient(gc):
    x = np.random.default_rng(3).normal(size=10)
    numeric = gc.numerical_grad(lambda v: float(np.sum(v**3)), x)
    buggy = 3 * x**2 * 1.01
    assert gc.relative_error(numeric, buggy) > 1e-3
