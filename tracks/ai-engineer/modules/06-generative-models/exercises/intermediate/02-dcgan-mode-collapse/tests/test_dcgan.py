import copy
import math

import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("dcgan.ipynb")


def test_ring_centers(nb):
    c = nb.ring_centers()
    assert c.shape == (8, 2)
    torch.testing.assert_close(c[0], torch.tensor([2.0, 0.0]))
    torch.testing.assert_close(c[2], torch.tensor([0.0, 2.0]), atol=1e-6, rtol=0)
    c3 = nb.ring_centers(3, 1.5)
    torch.testing.assert_close(c3[1], torch.tensor([1.5 * math.cos(2 * math.pi / 3), 1.5 * math.sin(2 * math.pi / 3)]))


def test_ring_data(nb):
    x = nb.ring_data(8000, torch.Generator().manual_seed(0))
    assert x.shape == (8000, 2) and x.dtype == torch.float32
    y = nb.ring_data(8000, torch.Generator().manual_seed(0))
    torch.testing.assert_close(x, y, msg="cùng generator cùng dữ liệu")
    centers = nb.ring_centers()
    nearest, idx = torch.cdist(x, centers).min(1)
    assert nearest.max().item() < 0.15
    counts = torch.bincount(idx, minlength=8)
    assert counts.min().item() > 850 and counts.max().item() < 1150, "8 mode chọn đều"
    resid = x - centers[idx]
    assert resid.std().item() == pytest.approx(0.02, rel=0.05)
    wide = nb.ring_data(4000, torch.Generator().manual_seed(1), n_modes=4, radius=5.0, std=0.1)
    assert (wide - nb.ring_centers(4, 5.0)[torch.cdist(wide, nb.ring_centers(4, 5.0)).argmin(1)]).std().item() == pytest.approx(0.1, rel=0.05)


def test_generator_architecture(nb):
    G = nb.Generator()
    assert sum(p.numel() for p in G.parameters()) == 1_329_921
    types = [type(m) for m in G.net]
    assert types == [nn.ConvTranspose2d, nn.BatchNorm2d, nn.ReLU, nn.ConvTranspose2d, nn.BatchNorm2d, nn.ReLU, nn.ConvTranspose2d, nn.Tanh]
    assert G.net[0].bias is None and G.net[3].bias is None, "conv đứng trước BatchNorm không cần bias"
    G.eval()
    out = G(torch.randn(5, 64))
    assert out.shape == (5, 1, 28, 28)
    assert out.abs().max().item() <= 1.0
    small = nb.Generator(z_dim=16, c=8)
    assert small.z_dim == 16 and small(torch.randn(2, 16)).shape == (2, 1, 28, 28)


def test_discriminator_architecture(nb):
    D = nb.Discriminator()
    assert sum(p.numel() for p in D.parameters()) == 138_689
    types = [type(m) for m in D.net]
    assert types == [nn.Conv2d, nn.LeakyReLU, nn.Conv2d, nn.BatchNorm2d, nn.LeakyReLU, nn.Conv2d]
    assert D.net[1].negative_slope == 0.2 and D.net[2].bias is None
    with torch.no_grad():
        D.net[5].bias.fill_(5.0)
    D.eval()
    out = D(torch.randn(6, 1, 28, 28))
    assert out.shape == (6,)
    assert out.max().item() > 1.0, "D trả logit, không qua sigmoid"


def test_dcgan_init(nb):
    torch.manual_seed(0)
    G, D = nb.Generator(), nb.Discriminator()
    G.apply(nb.dcgan_init)
    D.apply(nb.dcgan_init)
    w = G.net[0].weight
    assert abs(w.mean().item()) < 1e-3 and w.std().item() == pytest.approx(0.02, rel=0.02)
    assert D.net[2].weight.std().item() == pytest.approx(0.02, rel=0.05)
    bn = G.net[1]
    assert bn.weight.mean().item() == pytest.approx(1.0, abs=0.01) and bn.weight.std().item() == pytest.approx(0.02, rel=0.3)
    assert torch.all(bn.bias == 0) and torch.all(G.net[6].bias == 0) and torch.all(D.net[0].bias == 0)
    lin = nn.Linear(4, 3)
    before = lin.weight.clone()
    lin.apply(nb.dcgan_init)
    torch.testing.assert_close(lin.weight, before, msg="module không phải conv/BN thì giữ nguyên")


def reference_step(G, D, opt_g, opt_d, real, generator, loss):
    z = torch.randn(len(real), G.z_dim, generator=generator)
    fake = G(z)
    rl, fl = D(real), D(fake.detach())
    ld = F.softplus(-rl).mean() + F.softplus(fl).mean()
    opt_d.zero_grad(); ld.backward(); opt_d.step()
    out = D(fake)
    lg = F.softplus(-out).mean() if loss == "ns" else -F.softplus(out).mean()
    opt_g.zero_grad(); lg.backward(); opt_g.step()
    return {"d_loss": ld.item(), "g_loss": lg.item(), "d_real": torch.sigmoid(rl).mean().item(), "d_fake": torch.sigmoid(fl).mean().item()}


@pytest.mark.parametrize("loss", ["ns", "saturating"])
def test_gan_step_matches_reference(nb, loss):
    torch.manual_seed(1)
    G, D = nb.Generator(z_dim=8, c=4), nb.Discriminator(c=4)
    G2, D2 = copy.deepcopy(G), copy.deepcopy(D)
    real = torch.rand(6, 1, 28, 28, generator=torch.Generator().manual_seed(2)) * 2 - 1
    opts = [torch.optim.Adam(m.parameters(), 1e-2, betas=(0.5, 0.999)) for m in (G, D, G2, D2)]
    for step in range(2):
        out = nb.gan_step(G, D, opts[0], opts[1], real, torch.Generator().manual_seed(10 + step), loss=loss)
        ref = reference_step(G2, D2, opts[2], opts[3], real, torch.Generator().manual_seed(10 + step), loss)
        assert set(out) >= {"d_loss", "g_loss", "d_real", "d_fake"}
        for k in ref:
            assert isinstance(out[k], float)
            assert out[k] == pytest.approx(ref[k], rel=1e-5, abs=1e-6), k
    for a, b in zip(list(G.parameters()) + list(D.parameters()), list(G2.parameters()) + list(D2.parameters())):
        torch.testing.assert_close(a, b, msg="tham số sau hai bước phải khớp bản tham chiếu (thứ tự, detach, loss)")


def test_gan_step_d_update_ignores_generator(nb):
    """lr của G bằng 0: G không đổi; bước D không được để gradient chảy vào G."""
    torch.manual_seed(3)
    G, D = nb.Generator(z_dim=8, c=4), nb.Discriminator(c=4)
    before = [p.detach().clone() for p in G.parameters()]
    opt_g = torch.optim.SGD(G.parameters(), lr=0.0)
    opt_d = torch.optim.SGD(D.parameters(), lr=0.1)
    nb.gan_step(G, D, opt_g, opt_d, torch.rand(4, 1, 28, 28) * 2 - 1, torch.Generator().manual_seed(0))
    for a, b in zip(G.parameters(), before):
        torch.testing.assert_close(a, b)


def test_class_histogram(nb):
    uniform = torch.arange(1000) % 10
    n, kl = nb.class_histogram(uniform)
    assert n == 10 and kl == pytest.approx(0.0, abs=1e-12)
    n, kl = nb.class_histogram(torch.full((500,), 3))
    assert n == 1 and kl == pytest.approx(math.log(10))
    pred = torch.cat([torch.zeros(600, dtype=torch.long), torch.ones(395, dtype=torch.long), torch.full((5,), 7)])
    n, kl = nb.class_histogram(pred)
    assert n == 2, "lớp 7 chỉ 0.5% < min_frac 1%"
    p = torch.tensor([0.6, 0.395, 0.005])
    assert kl == pytest.approx(float((p * (p * 10).log()).sum()))
    assert nb.class_histogram(pred, min_frac=0.001)[0] == 3
    assert isinstance(n, int) and isinstance(kl, float)
