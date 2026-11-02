import numpy as np
import pytest
import torch
import torch.nn.functional as F

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)

NAMES = ["sigmoid", "tanh", "relu", "gelu"]
TORCH_FN = {
    "sigmoid": torch.sigmoid,
    "tanh": torch.tanh,
    "relu": torch.relu,
    "gelu": lambda t: F.gelu(t, approximate="tanh"),
}


@pytest.fixture(scope="module")
def act():
    return ex.module("activations.py")


def _inputs() -> np.ndarray:
    """Lưới đều trên [-8, 8] cộng điểm ngẫu nhiên, dạng 2 chiều; tránh đúng điểm gãy 0 của ReLU."""
    rng = np.random.default_rng(0)
    x = np.concatenate([np.linspace(-8, 8, 160), rng.normal(0, 3, 40)])
    x = x[np.abs(x) > 1e-3]
    return x[: x.size // 4 * 4].reshape(-1, 4)


@pytest.mark.parametrize("name", NAMES)
def test_forward_matches_torch(act, name):
    x = _inputs()
    got = getattr(act, name)(x)
    ref = TORCH_FN[name](torch.tensor(x, dtype=torch.float64)).numpy()
    assert got.shape == x.shape
    np.testing.assert_allclose(got, ref, rtol=0, atol=1e-6)


@pytest.mark.parametrize("name", NAMES)
def test_grad_matches_central_difference(act, name):
    x = _inputs()
    f = getattr(act, name)
    eps = 1e-6
    numeric = (f(x + eps) - f(x - eps)) / (2 * eps)
    got = getattr(act, f"{name}_grad")(x)
    assert got.shape == x.shape
    np.testing.assert_allclose(got, numeric, rtol=0, atol=1e-5)


@pytest.mark.parametrize("name", NAMES)
def test_grad_matches_torch_autograd(act, name):
    x = _inputs()
    t = torch.tensor(x, dtype=torch.float64, requires_grad=True)
    TORCH_FN[name](t).sum().backward()
    np.testing.assert_allclose(getattr(act, f"{name}_grad")(x), t.grad.numpy(), rtol=0, atol=1e-6)


def test_relu_grad_at_zero_is_zero(act):
    assert act.relu_grad(np.array([0.0]))[0] == 0.0


def test_sigmoid_no_overflow_for_large_inputs(act):
    x = np.array([-1000.0, -50.0, 0.0, 50.0, 1000.0])
    with np.errstate(over="raise"):
        s = act.sigmoid(x)
        ds = act.sigmoid_grad(x)
    assert np.all(np.isfinite(s)) and np.all(np.isfinite(ds))
    assert s[0] == pytest.approx(0.0, abs=1e-300)
    assert s[2] == pytest.approx(0.5)
    assert s[-1] == pytest.approx(1.0)
    assert np.all((s >= 0) & (s <= 1))


def test_softmax_large_logits_no_nan(act):
    p = act.softmax(np.array([1000.0, 1001.0, 1002.0]))
    assert not np.any(np.isnan(p))
    assert p.sum() == pytest.approx(1.0)
    ref = torch.softmax(torch.tensor([0.0, 1.0, 2.0], dtype=torch.float64), dim=0).numpy()
    np.testing.assert_allclose(p, ref, atol=1e-12)


def test_softmax_matches_torch_on_both_axes(act):
    rng = np.random.default_rng(1)
    z = rng.normal(0, 5, (6, 10))
    zt = torch.tensor(z, dtype=torch.float64)
    p = act.softmax(z)
    assert p.shape == z.shape
    np.testing.assert_allclose(p, torch.softmax(zt, dim=-1).numpy(), atol=1e-12)
    np.testing.assert_allclose(p.sum(axis=-1), 1.0, atol=1e-12)
    np.testing.assert_allclose(act.softmax(z, axis=0), torch.softmax(zt, dim=0).numpy(), atol=1e-12)


def test_softmax_max_is_taken_per_row(act):
    # dòng 2 nhỏ hơn dòng 1 rất nhiều: trừ max của cả mảng thì dòng 2 underflow về 0/0 = nan
    z = np.array([[1000.0, 1001.0], [-1000.0, -999.0]])
    with np.errstate(all="ignore"):
        p = act.softmax(z)
    assert not np.any(np.isnan(p))
    np.testing.assert_allclose(p[0], p[1], atol=1e-12)
