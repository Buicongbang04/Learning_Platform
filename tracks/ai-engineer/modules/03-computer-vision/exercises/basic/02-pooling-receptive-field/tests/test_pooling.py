import numpy as np
import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)

POOLS = [(2, 2), (3, 2), (3, 1), (2, 1), (4, 3)]   # (k, stride): không chồng và chồng nhau


@pytest.fixture(scope="module")
def P():
    return ex.module("pooling.py")


def test_only_numpy():
    src = ex.read("pooling.py")
    assert "import torch" not in src and "from torch" not in src, "chỉ dùng numpy trong pooling.py"


@pytest.mark.parametrize("n,k,s,p,d", [(32, 3, 1, 1, 1), (32, 3, 2, 1, 1), (7, 3, 2, 0, 1), (224, 7, 2, 3, 1),
                                       (28, 5, 1, 0, 1), (32, 3, 1, 2, 2), (33, 3, 2, 4, 4), (10, 2, 2, 0, 1)])
def test_conv_output_size_matches_torch(P, n, k, s, p, d):
    out = nn.Conv2d(1, 1, k, stride=s, padding=p, dilation=d)(torch.zeros(1, 1, n, n))
    assert P.conv_output_size(n, k, s, p, d) == out.shape[-1]


def empirical_rf(layers) -> int:
    """Đo receptive field bằng gradient trên "ảnh" 1 x 400: kernel (1, k) trọng số 1, không padding; đếm số
    pixel input có gradient khác 0 tới điểm output ở giữa."""
    mods = []
    for layer in layers:
        k, s = layer[0], layer[1]
        d = layer[2] if len(layer) > 2 else 1
        conv = nn.Conv2d(1, 1, (1, k), stride=(1, s), dilation=(1, d), bias=False).double()
        nn.init.ones_(conv.weight)
        mods.append(conv)
    x = torch.zeros(1, 1, 1, 400, dtype=torch.float64, requires_grad=True)
    out = nn.Sequential(*mods)(x)
    out[0, 0, 0, out.shape[-1] // 2].backward()
    return int((x.grad[0, 0, 0] != 0).sum())


@pytest.mark.parametrize("layers", [
    [(3, 1)] * 3,                                         # ba conv 3x3 = một 7x7
    [(3, 1), (3, 1), (2, 2), (3, 1), (3, 1), (2, 2)],     # hai khối đầu VGG
    [(7, 2), (3, 2), (3, 1), (3, 1), (3, 2), (3, 1)],     # gốc ResNet: conv 7x7/2, maxpool 3x3/2, ...
    [(3, 1, 1), (3, 1, 2), (3, 1, 4)],                    # dilation 1, 2, 4 (WaveNet/DeepLab)
    [(5, 3), (4, 2), (3, 1)],
])
def test_receptive_field_matches_gradient(P, layers):
    rf, jump = P.receptive_field(layers)
    assert rf == empirical_rf(layers)
    assert jump == int(np.prod([layer[1] for layer in layers]))


def test_receptive_field_vgg16(P):
    vgg = ([(3, 1)] * 2 + [(2, 2)]) * 2 + ([(3, 1)] * 3 + [(2, 2)]) * 3
    assert P.receptive_field(vgg[:-1]) == (196, 16)      # conv5_3
    assert P.receptive_field(vgg) == (212, 32)           # pool5


def data(seed, shape=(2, 3, 9, 8)):
    return np.random.default_rng(seed).normal(size=shape)


@pytest.mark.parametrize("k,s", POOLS)
def test_maxpool_matches_torch(P, k, s):
    x = data(k * 10 + s)
    out, cache = P.maxpool2d_forward(x, k, s)
    tx = torch.tensor(x, requires_grad=True)
    ref = F.max_pool2d(tx, k, s)
    np.testing.assert_allclose(out, ref.detach().numpy(), atol=0)
    G = np.random.default_rng(1).normal(size=out.shape)
    (ref * torch.tensor(G)).sum().backward()
    dx = P.maxpool2d_backward(G, cache)
    assert dx.shape == x.shape
    np.testing.assert_allclose(dx, tx.grad.numpy(), atol=1e-12)


def test_maxpool_overlap_accumulates(P):
    # k=3, s=1: phần tử lớn nhất ở giữa là max của cả 9 cửa sổ
    x = np.zeros((1, 1, 5, 5))
    x[0, 0, 2, 2] = 10.0
    out, cache = P.maxpool2d_forward(x, 3, 1)
    dx = P.maxpool2d_backward(np.ones_like(out), cache)
    assert dx[0, 0, 2, 2] == 9.0 and dx.sum() == 9.0


def test_maxpool_ties_go_to_first(P):
    x = np.ones((1, 1, 2, 2))
    out, cache = P.maxpool2d_forward(x, 2, 2)
    dx = P.maxpool2d_backward(np.array([[[[3.0]]]]), cache)
    np.testing.assert_array_equal(dx[0, 0], [[3.0, 0.0], [0.0, 0.0]])


@pytest.mark.parametrize("k,s", POOLS)
def test_avgpool_matches_torch(P, k, s):
    x = data(k * 7 + s)
    out, cache = P.avgpool2d_forward(x, k, s)
    tx = torch.tensor(x, requires_grad=True)
    ref = F.avg_pool2d(tx, k, s)
    np.testing.assert_allclose(out, ref.detach().numpy(), atol=1e-12)
    G = np.random.default_rng(2).normal(size=out.shape)
    (ref * torch.tensor(G)).sum().backward()
    np.testing.assert_allclose(P.avgpool2d_backward(G, cache), tx.grad.numpy(), atol=1e-12)
