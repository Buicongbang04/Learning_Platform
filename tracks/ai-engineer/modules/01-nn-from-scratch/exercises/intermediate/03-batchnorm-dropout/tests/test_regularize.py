from typing import Callable

import numpy as np
import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("regularize.ipynb")


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


def batch(seed: int, n: int = 16, d: int = 4) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return 3.0 + 2.0 * rng.normal(size=(n, d))           # lệch mean và scale, float64


# ---------- BatchNorm1d ----------

def test_batchnorm_init(nb):
    bn = nb.BatchNorm1d(5)
    np.testing.assert_array_equal(bn.gamma, np.ones(5))
    np.testing.assert_array_equal(bn.beta, np.zeros(5))
    np.testing.assert_array_equal(bn.running_mean, np.zeros(5))
    np.testing.assert_array_equal(bn.running_var, np.ones(5))


def _pair(nb, d: int = 4, momentum: float = 0.1):
    rng = np.random.default_rng(10)
    bn = nb.BatchNorm1d(d, momentum=momentum)
    bn.gamma = rng.uniform(0.5, 2.0, d)
    bn.beta = rng.normal(size=d)
    ref = torch.nn.BatchNorm1d(d, momentum=momentum).double()
    with torch.no_grad():
        ref.weight.copy_(torch.tensor(bn.gamma))
        ref.bias.copy_(torch.tensor(bn.beta))
    return bn, ref


@pytest.mark.parametrize("momentum", [0.1, 0.3])
def test_batchnorm_train_matches_torch(nb, momentum):
    bn, ref = _pair(nb, momentum=momentum)
    ref.train()
    for seed in (0, 1):                                    # hai bước: running stats cộng dồn đúng
        x = batch(seed)
        out = bn.forward(x, training=True)
        expected = ref(torch.tensor(x)).detach().numpy()
        np.testing.assert_allclose(out, expected, rtol=0, atol=1e-6)
    np.testing.assert_allclose(bn.running_mean, ref.running_mean.numpy(), rtol=0, atol=1e-6)
    np.testing.assert_allclose(bn.running_var, ref.running_var.numpy(), rtol=0, atol=1e-6,
                               err_msg="running_var của PyTorch dùng phương sai không lệch (chia N - 1)")


def test_batchnorm_eval_matches_torch(nb):
    bn, ref = _pair(nb)
    ref.train()
    for seed in (0, 1):
        bn.forward(batch(seed), training=True)
        ref(torch.tensor(batch(seed)))
    ref.eval()
    x = batch(2, n=6)
    stats = (bn.running_mean.copy(), bn.running_var.copy())
    out = bn.forward(x, training=False)
    np.testing.assert_allclose(out, ref(torch.tensor(x)).detach().numpy(), rtol=0, atol=1e-6)
    np.testing.assert_array_equal(bn.running_mean, stats[0], err_msg="eval không được đổi running stats")
    np.testing.assert_array_equal(bn.running_var, stats[1])
    single = bn.forward(x[:1], training=False)             # eval: một mẫu riêng = cùng mẫu trong batch
    np.testing.assert_allclose(single, out[:1], rtol=0, atol=1e-12)


def test_batchnorm_train_rejects_batch_of_one(nb):
    with pytest.raises(ValueError):
        nb.BatchNorm1d(3).forward(np.ones((1, 3)), training=True)


@pytest.mark.parametrize("training", [True, False])
def test_batchnorm_gradcheck(nb, training):
    rng = np.random.default_rng(20)
    bn = nb.BatchNorm1d(4)
    bn.gamma = rng.uniform(0.5, 2.0, 4)
    bn.beta = rng.normal(size=4)
    bn.running_mean = rng.normal(size=4)
    bn.running_var = rng.uniform(0.5, 2.0, 4)
    x = batch(3, n=8)
    G = rng.normal(size=(8, 4))                           # loss = sum(out * G)
    saved = (bn.running_mean.copy(), bn.running_var.copy())

    def loss() -> float:
        bn.running_mean, bn.running_var = saved[0].copy(), saved[1].copy()
        return float(np.sum(bn.forward(x, training=training) * G))

    loss()
    dx = bn.backward(G)
    dgamma, dbeta = bn.dgamma.copy(), bn.dbeta.copy()
    assert dx.shape == x.shape and dgamma.shape == (4,) and dbeta.shape == (4,)
    assert rel(dx, num_grad(loss, x)) < 1e-5
    assert rel(dgamma, num_grad(loss, bn.gamma)) < 1e-5
    assert rel(dbeta, num_grad(loss, bn.beta)) < 1e-5


# ---------- Dropout ----------

def test_dropout_keeps_expectation(nb):
    drop = nb.Dropout(0.3, np.random.default_rng(0))
    x = np.ones((1000, 1000))
    out = drop.forward(x, training=True)
    assert out.shape == x.shape
    assert out.mean() == pytest.approx(1.0, rel=0.01), "inverted dropout: kỳ vọng không đổi"
    assert np.mean(out == 0) == pytest.approx(0.3, abs=0.01)
    np.testing.assert_allclose(np.unique(out), [0.0, 1 / 0.7])


def test_dropout_eval_is_identity(nb):
    drop = nb.Dropout(0.5, np.random.default_rng(1))
    x = np.random.default_rng(2).normal(size=(4, 5))
    np.testing.assert_array_equal(drop.forward(x, training=False), x)
    G = np.ones((4, 5))
    np.testing.assert_array_equal(drop.backward(G), G)


def test_dropout_backward_reuses_mask(nb):
    drop = nb.Dropout(0.4, np.random.default_rng(3))
    x = np.ones((50, 20))
    out = drop.forward(x, training=True)
    np.testing.assert_array_equal(drop.backward(np.ones_like(x)), out)   # cùng chỗ 0, cùng hệ số 1/(1-p)
    np.testing.assert_array_equal(drop.backward(np.ones_like(x)), out)   # backward không sinh mask mới
    again = drop.forward(x, training=True)
    assert not np.array_equal(again, out), "mỗi forward khi train phải sinh mask mới"


def test_dropout_uses_rng(nb):
    x = np.ones((20, 20))
    a = nb.Dropout(0.5, np.random.default_rng(7)).forward(x, training=True)
    b = nb.Dropout(0.5, np.random.default_rng(7)).forward(x, training=True)
    np.testing.assert_array_equal(a, b)


def test_dropout_zero_is_identity(nb):
    drop = nb.Dropout(0.0, np.random.default_rng(4))
    x = np.random.default_rng(5).normal(size=(3, 4))
    np.testing.assert_array_equal(drop.forward(x, training=True), x)
