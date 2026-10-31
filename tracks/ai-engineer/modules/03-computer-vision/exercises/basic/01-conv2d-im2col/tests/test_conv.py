import time
from typing import Callable

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)

# (N, C, H, W, F, kh, kw, stride, padding): kernel vuông và chữ nhật, stride 1/2, có và không padding
CONFIGS = [
    (2, 3, 7, 7, 4, 3, 3, 1, 0),
    (2, 3, 7, 6, 4, 3, 3, 1, 1),
    (3, 2, 9, 8, 5, 3, 3, 2, 1),
    (1, 4, 8, 9, 2, 2, 3, 2, 0),
    (2, 1, 6, 6, 3, 1, 1, 1, 0),
    (2, 2, 10, 10, 3, 5, 5, 3, 2),
]


@pytest.fixture(scope="module")
def C():
    return ex.module("conv.py")


def data(cfg, seed=0):
    N, Cin, H, W, Fo, kh, kw, s, p = cfg
    rng = np.random.default_rng(seed)
    return rng.normal(size=(N, Cin, H, W)), rng.normal(size=(Fo, Cin, kh, kw)), rng.normal(size=Fo)


def num_grad(f: Callable[[], float], arr: np.ndarray, eps: float = 1e-6) -> np.ndarray:
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


def test_only_numpy():
    src = ex.read("conv.py")
    assert "import torch" not in src and "from torch" not in src, "chỉ dùng numpy trong conv.py"
    assert "sliding_window_view" not in src and "as_strided" not in src, "tự cắt lát cửa sổ, không dùng stride tricks"


@pytest.mark.parametrize("cfg", CONFIGS)
def test_im2col_matches_unfold(C, cfg):
    x, W, _ = data(cfg)
    _, _, _, _, _, kh, kw, s, p = cfg
    cols = C.im2col(x, kh, kw, s, p)
    ref = F.unfold(torch.tensor(x), (kh, kw), stride=s, padding=p)          # (N, C*kh*kw, L)
    ref = ref.transpose(1, 2).reshape(-1, ref.shape[1]).numpy()
    assert cols.shape == ref.shape, "cols phải có shape (N*OH*OW, C*kh*kw)"
    np.testing.assert_allclose(cols, ref, atol=1e-12)


@pytest.mark.parametrize("cfg", CONFIGS)
def test_col2im_is_adjoint_of_im2col(C, cfg):
    # <im2col(x), c> == <x, col2im(c)>: đúng khi col2im CỘNG các vùng chồng nhau và bỏ padding
    x, _, _ = data(cfg, 1)
    _, _, _, _, _, kh, kw, s, p = cfg
    cols = C.im2col(x, kh, kw, s, p)
    c = np.random.default_rng(2).normal(size=cols.shape)
    back = C.col2im(c, x.shape, kh, kw, s, p)
    assert back.shape == x.shape
    assert np.sum(cols * c) == pytest.approx(np.sum(x * back), rel=1e-10)


def test_col2im_sums_overlaps(C):
    # kernel 2x2, stride 1 trên ảnh 3x3: pixel giữa nằm trong cả 4 cửa sổ
    ones = np.ones((4, 4))
    back = C.col2im(ones, (1, 1, 3, 3), 2, 2, 1, 0)
    np.testing.assert_array_equal(back[0, 0], [[1, 2, 1], [2, 4, 2], [1, 2, 1]])


@pytest.mark.parametrize("cfg", CONFIGS)
def test_forward_matches_torch(C, cfg):
    x, W, b = data(cfg, 3)
    s, p = cfg[7], cfg[8]
    out, _ = C.conv2d_forward(x, W, b, s, p)
    ref = F.conv2d(torch.tensor(x), torch.tensor(W), torch.tensor(b), stride=s, padding=p).numpy()
    assert out.shape == ref.shape
    np.testing.assert_allclose(out, ref, atol=1e-10)


@pytest.mark.parametrize("cfg", CONFIGS)
def test_backward_matches_autograd(C, cfg):
    x, W, b = data(cfg, 4)
    s, p = cfg[7], cfg[8]
    out, cache = C.conv2d_forward(x, W, b, s, p)
    G = np.random.default_rng(5).normal(size=out.shape)
    dx, dW, db = C.conv2d_backward(G, cache)

    tx, tW, tb = (torch.tensor(a, requires_grad=True) for a in (x, W, b))
    (F.conv2d(tx, tW, tb, stride=s, padding=p) * torch.tensor(G)).sum().backward()
    np.testing.assert_allclose(dx, tx.grad.numpy(), atol=1e-10)
    np.testing.assert_allclose(dW, tW.grad.numpy(), atol=1e-10)
    np.testing.assert_allclose(db, tb.grad.numpy(), atol=1e-10)


def test_backward_gradcheck(C):
    x, W, b = data((2, 2, 5, 5, 3, 3, 3, 2, 1), 6)
    G = np.random.default_rng(7).normal(size=(2, 3, 3, 3))
    out, cache = C.conv2d_forward(x, W, b, 2, 1)
    dx, dW, db = C.conv2d_backward(G, cache)
    f = lambda: float(np.sum(C.conv2d_forward(x, W, b, 2, 1)[0] * G))
    assert rel(dx, num_grad(f, x)) < 1e-7
    assert rel(dW, num_grad(f, W)) < 1e-7
    assert rel(db, num_grad(f, b)) < 1e-7


def test_vectorized_speed(C):
    # Một tầng conv của ResNet CIFAR: 64 ảnh 16x32x32, 32 bộ lọc 3x3. Bản im2col dưới 1 s;
    # vòng lặp Python qua từng (n, f, oh, ow) chậm hơn vài chục lần.
    rng = np.random.default_rng(8)
    x = rng.normal(size=(64, 16, 32, 32)).astype(np.float32)
    W = rng.normal(size=(32, 16, 3, 3)).astype(np.float32)
    b = np.zeros(32, np.float32)
    start = time.perf_counter()
    out, cache = C.conv2d_forward(x, W, b, 1, 1)
    C.conv2d_backward(np.ones_like(out), cache)
    elapsed = time.perf_counter() - start
    assert out.shape == (64, 32, 32, 32)
    assert elapsed < 10.0, f"forward + backward mất {elapsed:.1f} s: còn vòng lặp Python qua N/OH/OW?"
