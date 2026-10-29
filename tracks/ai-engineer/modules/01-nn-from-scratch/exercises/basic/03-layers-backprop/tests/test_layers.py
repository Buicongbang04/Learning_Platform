from typing import Callable

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def L():
    return ex.module("layers.py")


def num_grad(f: Callable[[], float], arr: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Sai phân trung tâm theo từng phần tử của `arr`, sửa `arr` tại chỗ (f đọc nó qua layer)."""
    g = np.zeros_like(arr)
    for idx in np.ndindex(arr.shape):
        old = arr[idx]
        arr[idx] = old + eps
        fp = f()
        arr[idx] = old - eps
        fm = f()
        arr[idx] = old
        g[idx] = (fp - fm) / (2 * eps)
    return g


def rel(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs(a - b)) / max(np.max(np.abs(a)) + np.max(np.abs(b)), 1e-12))


def away_from_zero(rng: np.random.Generator, shape) -> np.ndarray:
    """Số ngẫu nhiên có |x| trong [0.1, 2]: sai phân không nhảy qua điểm gãy của ReLU."""
    return rng.choice([-1.0, 1.0], size=shape) * rng.uniform(0.1, 2.0, size=shape)


def test_linear_he_init(L):
    layer = L.Linear(1000, 500, np.random.default_rng(0))
    assert layer.W.shape == (1000, 500) and layer.W.dtype == np.float64
    assert layer.b.shape == (500,) and np.all(layer.b == 0)
    target = np.sqrt(2 / 1000)
    assert abs(layer.W.std() - target) / target < 0.02
    assert abs(layer.W.mean()) < 1e-3
    again = L.Linear(1000, 500, np.random.default_rng(0))
    assert np.array_equal(layer.W, again.W), "cùng seed phải ra cùng trọng số: chỉ lấy số ngẫu nhiên từ rng"


def test_linear_forward(L):
    rng = np.random.default_rng(1)
    layer = L.Linear(4, 3, rng)
    layer.b = rng.normal(size=3)
    x = rng.normal(size=(5, 4))
    np.testing.assert_allclose(layer.forward(x), x @ layer.W + layer.b, atol=1e-12)


def test_linear_backward_gradcheck(L):
    rng = np.random.default_rng(2)
    layer = L.Linear(4, 3, rng)
    layer.b = rng.normal(size=3)
    x = rng.normal(size=(5, 4))
    G = rng.normal(size=(5, 3))  # gradient giả từ phía sau: loss = sum(out * G)

    layer.forward(x)
    dx = layer.backward(G)
    dW, db = layer.dW.copy(), layer.db.copy()
    assert dx.shape == x.shape and dW.shape == layer.W.shape and db.shape == layer.b.shape

    f = lambda: float(np.sum(layer.forward(x) * G))
    assert rel(dx, num_grad(f, x)) < 1e-6
    assert rel(dW, num_grad(f, layer.W)) < 1e-6
    assert rel(db, num_grad(f, layer.b)) < 1e-6


def test_linear_backward_overwrites_not_accumulates(L):
    rng = np.random.default_rng(3)
    layer = L.Linear(4, 3, rng)
    x, G = rng.normal(size=(5, 4)), rng.normal(size=(5, 3))
    layer.forward(x)
    layer.backward(G)
    first = layer.dW.copy()
    layer.forward(x)
    layer.backward(G)
    np.testing.assert_allclose(layer.dW, first, atol=1e-12)


def test_relu_forward_backward(L):
    rng = np.random.default_rng(4)
    relu = L.ReLU()
    x = away_from_zero(rng, (6, 5))
    G = rng.normal(size=(6, 5))
    np.testing.assert_array_equal(relu.forward(x), np.maximum(x, 0))
    dx = relu.backward(G)
    f = lambda: float(np.sum(relu.forward(x) * G))
    assert rel(dx, num_grad(f, x)) < 1e-6


def test_relu_grad_at_zero_is_zero(L):
    relu = L.ReLU()
    relu.forward(np.array([[0.0, 1.0]]))
    np.testing.assert_array_equal(relu.backward(np.array([[5.0, 5.0]])), [[0.0, 5.0]])


def test_softmax_ce_loss_and_gradcheck(L):
    rng = np.random.default_rng(5)
    ce = L.SoftmaxCrossEntropy()
    logits = rng.normal(size=(6, 4))
    y = rng.integers(0, 4, 6)
    loss = ce.forward(logits, y)
    assert isinstance(loss, float)
    dlogits = ce.backward()
    assert dlogits.shape == logits.shape
    f = lambda: ce.forward(logits, y)
    assert rel(dlogits, num_grad(f, logits)) < 1e-6


def _mlp(L, seed: int):
    rng = np.random.default_rng(seed)
    N, D, H, C = 8, 5, 6, 3
    l1, relu, l2, ce = L.Linear(D, H, rng), L.ReLU(), L.Linear(H, C, rng), L.SoftmaxCrossEntropy()
    l1.b = rng.normal(0, 0.1, H)
    l2.b = rng.normal(0, 0.1, C)
    X = rng.normal(size=(N, D))
    y = rng.integers(0, C, N)
    return X, y, l1, relu, l2, ce


def test_chain_gradcheck(L):
    X, y, l1, relu, l2, ce = _mlp(L, 6)

    def loss() -> float:
        return ce.forward(l2.forward(relu.forward(l1.forward(X))), y)

    loss()
    dX = l1.backward(relu.backward(l2.backward(ce.backward())))
    grads = {"W1": l1.dW.copy(), "b1": l1.db.copy(), "W2": l2.dW.copy(), "b2": l2.db.copy()}
    params = {"W1": l1.W, "b1": l1.b, "W2": l2.W, "b2": l2.b}
    for name, p in params.items():
        assert rel(grads[name], num_grad(loss, p)) < 1e-6, name
    assert rel(dX, num_grad(loss, X)) < 1e-6


def test_chain_matches_torch(L):
    X, y, l1, relu, l2, ce = _mlp(L, 7)
    loss = ce.forward(l2.forward(relu.forward(l1.forward(X))), y)
    l1.backward(relu.backward(l2.backward(ce.backward())))

    # Lưu ý: nn.Linear của PyTorch lưu weight shape (out, in); ở đây tính thẳng X @ W như bài.
    t = {k: torch.tensor(v, requires_grad=True) for k, v in {"W1": l1.W, "b1": l1.b, "W2": l2.W, "b2": l2.b}.items()}
    logits = torch.relu(torch.tensor(X) @ t["W1"] + t["b1"]) @ t["W2"] + t["b2"]
    lt = F.cross_entropy(logits, torch.tensor(y))
    lt.backward()

    assert loss == pytest.approx(lt.item(), abs=1e-8)
    np.testing.assert_allclose(l1.dW, t["W1"].grad.numpy(), rtol=0, atol=1e-8)
    np.testing.assert_allclose(l1.db, t["b1"].grad.numpy(), rtol=0, atol=1e-8)
    np.testing.assert_allclose(l2.dW, t["W2"].grad.numpy(), rtol=0, atol=1e-8)
    np.testing.assert_allclose(l2.db, t["b2"].grad.numpy(), rtol=0, atol=1e-8)


def test_softmax_ce_large_logits_stable(L):
    ce = L.SoftmaxCrossEntropy()
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        # đúng lớp thấp hơn 1000 đơn vị: loss = 1000, không phải inf hay nan
        assert ce.forward(np.array([[1000.0, 0.0]]), np.array([1])) == pytest.approx(1000.0)
        assert ce.forward(np.array([[1000.0, 0.0]]), np.array([0])) == pytest.approx(0.0, abs=1e-12)

        rng = np.random.default_rng(8)
        logits = 1e3 * rng.normal(size=(16, 10))
        y = rng.integers(0, 10, 16)
        loss = ce.forward(logits, y)
        d = ce.backward()
    assert np.isfinite(loss) and np.all(np.isfinite(d))
    np.testing.assert_allclose(d.sum(axis=1), 0.0, atol=1e-12)  # mỗi dòng p - onehot có tổng 0
    ref = F.cross_entropy(torch.tensor(logits), torch.tensor(y))
    assert loss == pytest.approx(ref.item(), rel=1e-12)
