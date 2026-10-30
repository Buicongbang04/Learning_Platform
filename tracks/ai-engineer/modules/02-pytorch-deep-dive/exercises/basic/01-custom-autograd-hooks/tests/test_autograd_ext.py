import pytest
import torch
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def m():
    return ex.module("autograd_ext.py")


def test_silu_matches_torch(m):
    x = torch.linspace(-8, 8, 101, dtype=torch.float64, requires_grad=True)
    y = m.silu(x)
    assert "SiLUFunction" in type(y.grad_fn).__name__, "silu phải đi qua SiLUFunction.apply"
    torch.testing.assert_close(y, torch.nn.functional.silu(x))
    g = torch.randn(101, dtype=torch.float64, generator=torch.Generator().manual_seed(0))
    (gx,) = torch.autograd.grad(y, x, g)
    x2 = x.detach().clone().requires_grad_()
    (gref,) = torch.autograd.grad(torch.nn.functional.silu(x2), x2, g)
    torch.testing.assert_close(gx, gref)


def test_silu_gradcheck(m):
    x = torch.randn(4, 5, dtype=torch.float64, generator=torch.Generator().manual_seed(1)) * 3
    assert torch.autograd.gradcheck(m.SiLUFunction.apply, (x.requires_grad_(),))


def test_round_ste(m):
    x = torch.tensor([-1.6, -0.4, 0.4, 1.5, 2.5], requires_grad=True)
    y = m.RoundSTE.apply(x)
    torch.testing.assert_close(y, torch.round(x.detach()))
    g = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
    y.backward(g)
    torch.testing.assert_close(x.grad, g, msg="straight-through: gradient đi qua nguyên vẹn")


@pytest.mark.parametrize("lambd", [1.0, 0.3])
def test_grad_reverse(m, lambd):
    lin = nn.Linear(3, 1)
    x = torch.randn(4, 3, generator=torch.Generator().manual_seed(2), requires_grad=True)
    h = m.grad_reverse(x, lambd)
    torch.testing.assert_close(h, x.detach())
    lin(h).sum().backward()
    g_rev = x.grad.clone()
    x.grad = None
    lin(x).sum().backward()
    torch.testing.assert_close(g_rev, -lambd * x.grad)


def test_grad_reverse_default_lambda(m):
    x = torch.ones(3, requires_grad=True)
    (m.grad_reverse(x) * 2).sum().backward()
    torch.testing.assert_close(x.grad, torch.full((3,), -2.0))


def _net():
    torch.manual_seed(0)
    return nn.Sequential(nn.Linear(8, 16), nn.ReLU(), nn.Linear(16, 16), nn.Tanh(), nn.Linear(16, 4), nn.ReLU())


def test_record_activations(m):
    net = _net()
    stats, handles = m.record_activations(net)
    assert set(stats) == set(), "chưa forward thì chưa có thống kê"
    x = torch.randn(32, 8, generator=torch.Generator().manual_seed(3))
    net(x)
    assert set(stats) == {"1", "5"}, "chỉ module có kiểu trong `types`, khoá là tên trong named_modules"
    h1 = net[1](net[0](x)).detach()
    assert isinstance(stats["1"]["mean"], float)
    assert stats["1"]["mean"] == pytest.approx(h1.mean().item(), rel=1e-5)
    assert stats["1"]["std"] == pytest.approx(h1.std().item(), rel=1e-5)
    assert stats["1"]["frac_zero"] == pytest.approx((h1 == 0).float().mean().item())
    out = net(x * 0 - 5).detach()                       # forward lần hai ghi đè
    assert stats["5"]["mean"] == pytest.approx(out.mean().item(), abs=1e-6)
    for h in handles:
        h.remove()
    before = dict(stats["5"])
    net(x)
    assert stats["5"] == before, "đã remove handle thì không ghi nữa"


def test_record_activations_custom_types(m):
    net = _net()
    stats, handles = m.record_activations(net, types=(nn.Tanh, nn.Linear))
    net(torch.randn(4, 8))
    assert set(stats) == {"0", "2", "3", "4"}
    for h in handles:
        h.remove()


def test_track_grad_norms_accumulated(m):
    net = _net()
    net[0].weight.requires_grad_(False)
    norms, handles = m.track_grad_norms(net)
    assert "0.weight" not in norms and "0.bias" in norms and len(norms) == 5
    x = torch.randn(16, 8, generator=torch.Generator().manual_seed(4))
    net(x).pow(2).sum().backward()
    first = {k: v[-1] for k, v in norms.items()}
    g1 = {k: p.grad.clone() for k, p in net.named_parameters() if p.requires_grad}
    for k in first:
        assert first[k] == pytest.approx(g1[k].norm().item(), rel=1e-5)
    net(x).pow(2).sum().backward()                      # không zero_grad: .grad cộng dồn gấp đôi
    for k, v in norms.items():
        assert len(v) == 2
        assert v[1] == pytest.approx(2 * first[k], rel=1e-5), "ghi norm SAU khi cộng dồn vào .grad"
    for h in handles:
        h.remove()
    net(x).sum().backward()
    assert all(len(v) == 2 for v in norms.values())
