import time

import numpy as np
import pytest
import torch
import torch.nn.functional as F
from threadpoolctl import threadpool_limits

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("mlp.ipynb")


def blobs(n: int, d: int, k: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """k cụm Gauss trong d chiều: dữ liệu nhỏ, học được, sinh trong test."""
    rng = np.random.default_rng(seed)
    centers = rng.normal(0, 2, (k, d))
    y = rng.integers(0, k, n)
    X = centers[y] + rng.normal(size=(n, d))
    return X.astype(np.float32), y.astype(np.int64)


def test_init_shapes_dtype_and_he_scale(nb):
    model = nb.MLP([20, 16, 8, 4], seed=0)
    pairs = model.params()
    assert len(pairs) == 6, "params() trả cặp (W1, dW1), (b1, db1), ... cho 3 tầng"
    shapes = [p.shape for p, _ in pairs]
    assert shapes == [(20, 16), (16,), (16, 8), (8,), (8, 4), (4,)]
    assert all(p.dtype == np.float32 for p, _ in pairs)
    assert all(np.all(b == 0) for b, _ in pairs[1::2])

    W1 = nb.MLP([1000, 500, 10], seed=0).params()[0][0]
    target = np.sqrt(2 / 1000)
    assert abs(W1.std() - target) / target < 0.03, "khởi tạo He: std = sqrt(2 / fan_in)"


def test_seed_controls_init(nb):
    a, b, c = nb.MLP([10, 6, 3], seed=1), nb.MLP([10, 6, 3], seed=1), nb.MLP([10, 6, 3], seed=2)
    assert all(np.array_equal(p, q) for (p, _), (q, _) in zip(a.params(), b.params()))
    assert not np.array_equal(a.params()[0][0], c.params()[0][0])


def test_forward_returns_logits(nb):
    X, _ = blobs(7, 5, 3, 0)
    logits = nb.MLP([5, 8, 3], seed=0).forward(X)
    assert logits.shape == (7, 3)


def test_loss_and_gradients_match_torch(nb):
    rng = np.random.default_rng(3)
    model = nb.MLP([6, 5, 4, 3], seed=1)
    for b, _ in model.params()[1::2]:
        b[...] = rng.normal(0, 0.1, b.shape)              # bias khác 0 để kiểm cả db
    X = rng.normal(size=(8, 6)).astype(np.float32)
    y = rng.integers(0, 3, 8)

    loss = model.loss_and_backward(X, y)
    assert isinstance(loss, float)

    t = [torch.tensor(p.copy(), requires_grad=True) for p, _ in model.params()]
    h = torch.tensor(X)
    for i in range(0, len(t), 2):
        h = h @ t[i] + t[i + 1]
        if i < len(t) - 2:
            h = torch.relu(h)
    ref = F.cross_entropy(h, torch.tensor(y))
    ref.backward()

    assert loss == pytest.approx(ref.item(), rel=1e-5)
    for (_, g), tp in zip(model.params(), t):
        assert g.shape == tuple(tp.shape)
        np.testing.assert_allclose(g, tp.grad.numpy(), rtol=1e-4, atol=1e-6)


def test_sgd_step_updates_in_place(nb):
    X, y = blobs(16, 5, 3, 1)
    model = nb.MLP([5, 8, 3], seed=0)
    model.loss_and_backward(X, y)
    before = [(p.copy(), g.copy()) for p, g in model.params()]
    nb.sgd_step(model, 0.1)
    for (p, _), (p0, g0) in zip(model.params(), before):
        np.testing.assert_allclose(p, p0 - 0.1 * g0, rtol=1e-6, atol=1e-7)
    assert not np.allclose(model.params()[0][0], before[0][0]), "sgd_step phải sửa chính mảng trong model"


def test_train_epoch_loss_is_mean_over_samples(nb):
    # lr = 0: tham số đứng yên, nên loss trung bình theo mẫu của epoch = loss trên cả tập.
    # 250 mẫu, batch 64: batch cuối 58 mẫu; lấy trung bình các batch như nhau sẽ lệch.
    X, y = blobs(250, 10, 4, 2)
    model = nb.MLP([10, 12, 4], seed=0)
    epoch_loss = nb.train_epoch(model, X, y, lr=0.0, batch_size=64, rng=np.random.default_rng(0))
    assert isinstance(epoch_loss, float)
    assert epoch_loss == pytest.approx(model.loss_and_backward(X, y), rel=1e-5)


def test_train_epoch_loss_decreases(nb):
    X, y = blobs(512, 20, 4, 3)
    model, rng = nb.MLP([20, 32, 4], seed=0), np.random.default_rng(0)
    first = nb.train_epoch(model, X, y, lr=0.05, batch_size=32, rng=rng)
    second = nb.train_epoch(model, X, y, lr=0.05, batch_size=32, rng=rng)
    assert second < first


def test_overfit_32_samples(nb):
    rng = np.random.default_rng(4)
    X = rng.normal(size=(32, 20)).astype(np.float32)
    y = rng.integers(0, 10, 32)                           # nhãn ngẫu nhiên: chỉ thuộc lòng được
    model = nb.MLP([20, 64, 10], seed=0)
    for _ in range(200):
        model.loss_and_backward(X, y)
        nb.sgd_step(model, 0.5)
    assert nb.accuracy(model, X, y) == 1.0


def test_same_seed_same_result(nb):
    X, y = blobs(300, 10, 3, 5)
    runs = []
    for _ in range(2):
        model, rng = nb.MLP([10, 16, 3], seed=7), np.random.default_rng(7)
        losses = [nb.train_epoch(model, X, y, lr=0.1, batch_size=32, rng=rng) for _ in range(2)]
        runs.append((losses, [p.copy() for p, _ in model.params()]))
    assert runs[0][0] == runs[1][0]
    assert all(np.array_equal(p, q) for p, q in zip(runs[0][1], runs[1][1]))


def test_accuracy(nb):
    X, y = blobs(50, 5, 3, 6)
    model = nb.MLP([5, 8, 3], seed=0)
    acc = nb.accuracy(model, X, y)
    assert isinstance(acc, float)
    assert acc == pytest.approx(float((model.forward(X).argmax(axis=1) == y).mean()))


# ---------- Dữ liệu thật: tự skip nếu chưa tải MNIST ----------

_MNIST: dict[str, tuple] = {}


def load_real(nb) -> tuple:
    """Đọc MNIST thật một lần cho cả hai test; gọi trong thân test để starter FAIL chứ không ERROR."""
    root = ex.dataset("mnist")
    if "data" not in _MNIST:
        _MNIST["data"] = nb.load_mnist(root)
    return _MNIST["data"]


def test_load_mnist_real(nb):
    X, y, Xt, yt = load_real(nb)
    assert X.shape == (60000, 784) and Xt.shape == (10000, 784)
    assert y.shape == (60000,) and yt.shape == (10000,)
    assert X.dtype == np.float32 and Xt.dtype == np.float32
    assert X.min() == 0.0 and X.max() == 1.0
    assert y.dtype == np.int64 and set(np.unique(y)) == set(range(10))
    assert y[:5].tolist() == [5, 0, 4, 1, 9] and yt[:5].tolist() == [7, 2, 1, 0, 4]
    assert float(X.mean()) == pytest.approx(0.1307, abs=1e-4)


def test_mlp_on_real_mnist(nb):
    X, y, Xt, yt = load_real(nb)
    start = time.perf_counter()
    with threadpool_limits(4):                            # ma trận nhỏ: nhiều luồng BLAS chỉ làm chậm
        model, rng = nb.MLP([784, 128, 10], seed=0), np.random.default_rng(0)
        for _ in range(2):
            nb.train_epoch(model, X[:20000], y[:20000], lr=0.1, batch_size=64, rng=rng)
        acc = nb.accuracy(model, Xt, yt)
    assert time.perf_counter() - start < 30
    assert acc >= 0.91, f"test accuracy {acc:.4f}; lời giải mẫu đạt 0.9235 với đúng cấu hình này"
