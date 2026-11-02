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
    return ex.notebook("ddpm.ipynb")


def short_schedule(T=50, b0=1e-3, b1=0.3):
    betas = torch.linspace(b0, b1, T, dtype=torch.float64)
    alphas = 1 - betas
    return {"betas": betas.float(), "alphas": alphas.float(), "alpha_bars": torch.cumprod(alphas, 0).float()}


class Oracle(nn.Module):
    """Nhiễu tối ưu E[eps | x_t] khi dữ liệu là N(m, s^2) độc lập từng pixel (s = 0: một điểm duy nhất m)."""

    def __init__(self, alpha_bars, m, s):
        super().__init__()
        self.register_buffer("ab", alpha_bars.double())
        self.m, self.s = m, s
        self.dummy = nn.Parameter(torch.zeros(1, dtype=torch.float64))

    def forward(self, x, t):
        ab = self.ab[t].view(-1, *([1] * (x.dim() - 1)))
        return (1 - ab).sqrt() * (x - ab.sqrt() * self.m) / (ab * self.s ** 2 + 1 - ab)


class Tiny(nn.Module):
    """Model nhỏ tất định để so từng số với bản tham chiếu."""

    def __init__(self):
        super().__init__()
        torch.manual_seed(0)
        self.conv = nn.Conv2d(1, 1, 3, padding=1)
        self.scale = nn.Parameter(torch.tensor(0.01))

    def forward(self, x, t):
        return 0.5 * torch.tanh(self.conv(x)) + self.scale * t.float().view(-1, 1, 1, 1) / 10


def test_make_schedule(nb):
    s = nb.make_schedule(1000, "linear")
    assert set(s) >= {"betas", "alphas", "alpha_bars"}
    assert all(v.dtype == torch.float32 and v.shape == (1000,) for v in s.values())
    assert s["betas"][0].item() == pytest.approx(1e-4) and s["betas"][-1].item() == pytest.approx(0.02)
    torch.testing.assert_close(s["alphas"], 1 - s["betas"])
    ab = torch.cumprod(1 - torch.linspace(1e-4, 0.02, 1000, dtype=torch.float64), 0)
    torch.testing.assert_close(s["alpha_bars"], ab.float())
    c = nb.make_schedule(1000, "cosine")
    f = lambda u: math.cos((u / 1000 + 0.008) / 1.008 * math.pi / 2) ** 2
    assert c["alpha_bars"][499].item() == pytest.approx(f(500) / f(0), rel=1e-5)
    assert c["betas"].max().item() == pytest.approx(0.999)


def test_sinusoidal_embedding(nb):
    t = torch.tensor([0, 5, 999])
    e = nb.sinusoidal_embedding(t, 8)
    assert e.shape == (3, 8) and e.dtype == torch.float32
    torch.testing.assert_close(e[0], torch.tensor([0.0] * 4 + [1.0] * 4))
    w = torch.tensor([10000 ** (-i / 4) for i in range(4)])
    torch.testing.assert_close(e[1], torch.cat([torch.sin(5 * w), torch.cos(5 * w)]))


def test_resblock(nb):
    torch.manual_seed(1)
    blk = nb.ResBlock(8, 16, 12)
    assert isinstance(blk.norm1, nn.GroupNorm) and blk.norm1.num_groups == 8 and blk.norm1.num_channels == 8
    assert isinstance(blk.skip, nn.Conv2d) and blk.skip.kernel_size == (1, 1)
    assert isinstance(nb.ResBlock(16, 16, 12).skip, nn.Identity)
    x, emb = torch.randn(2, 8, 5, 5), torch.randn(2, 12)
    out = blk(x, emb)
    assert out.shape == (2, 16, 5, 5)
    h = blk.conv1(F.silu(blk.norm1(x))) + blk.temb(emb)[:, :, None, None]
    torch.testing.assert_close(out, blk.conv2(F.silu(blk.norm2(h))) + blk.skip(x))
    assert not torch.allclose(blk(x, emb), blk(x, emb + 1.0)), "time embedding phải đổi output"


def test_unet_runs(nb):
    torch.manual_seed(0)
    net = nb.UNet()
    assert sum(p.numel() for p in net.parameters()) == 1_045_729
    assert net(torch.randn(2, 1, 28, 28), torch.tensor([0, 999])).shape == (2, 1, 28, 28)


def test_ddpm_loss_matches_reference(nb):
    s = short_schedule()
    model = Tiny()
    x0 = torch.rand(5, 1, 6, 6, generator=torch.Generator().manual_seed(3)) * 2 - 1
    loss = nb.ddpm_loss(model, x0, s, torch.Generator().manual_seed(4))
    g = torch.Generator().manual_seed(4)
    t = torch.randint(0, 50, (5,), generator=g)
    noise = torch.randn(x0.shape, generator=g)
    ab = s["alpha_bars"][t].view(-1, 1, 1, 1)
    expected = F.mse_loss(model(ab.sqrt() * x0 + (1 - ab).sqrt() * noise, t), noise)
    torch.testing.assert_close(loss, expected)
    loss.backward()
    assert model.conv.weight.grad is not None


def reference_ddpm(model, shape, s, g, clip=True):
    betas, abar = s["betas"], s["alpha_bars"]
    abar_prev = torch.cat([torch.ones(1), abar[:-1]])
    x = torch.randn(shape, generator=g)
    for t in reversed(range(len(betas))):
        eps = model(x, torch.full((shape[0],), t))
        x0 = (x - (1 - abar[t]).sqrt() * eps) / abar[t].sqrt()
        if clip:
            x0 = x0.clamp(-1, 1)
        mean = abar_prev[t].sqrt() * betas[t] / (1 - abar[t]) * x0 + (1 - betas[t]).sqrt() * (1 - abar_prev[t]) / (1 - abar[t]) * x
        x = mean + ((betas[t] * (1 - abar_prev[t]) / (1 - abar[t])).sqrt() * torch.randn(shape, generator=g) if t > 0 else 0)
    return x


def reference_ddim(model, shape, s, steps, g, clip=True):
    abar = s["alpha_bars"]
    ts = torch.linspace(0, len(abar) - 1, steps).round().long().tolist()
    x = torch.randn(shape, generator=g)
    for i in reversed(range(steps)):
        ab = abar[ts[i]]
        ab_prev = abar[ts[i - 1]] if i > 0 else torch.tensor(1.0)
        eps = model(x, torch.full((shape[0],), ts[i]))
        x0 = (x - (1 - ab).sqrt() * eps) / ab.sqrt()
        if clip:
            x0 = x0.clamp(-1, 1)
            eps = (x - ab.sqrt() * x0) / (1 - ab).sqrt()
        x = ab_prev.sqrt() * x0 + (1 - ab_prev).sqrt() * eps
    return x


@pytest.mark.parametrize("clip", [True, False])
def test_ddpm_sample_matches_reference(nb, clip):
    s = short_schedule(20)
    model = Tiny()
    with torch.no_grad():
        expected = reference_ddpm(model, (3, 1, 5, 5), s, torch.Generator().manual_seed(7), clip)
    out = nb.ddpm_sample(model, (3, 1, 5, 5), s, torch.Generator().manual_seed(7), clip=clip)
    torch.testing.assert_close(out, expected, atol=1e-5, rtol=1e-4)


def test_ddim_sample_matches_reference(nb):
    s = short_schedule(40)
    model = Tiny()
    for steps in (40, 7):
        for clip in (True, False):
            with torch.no_grad():
                expected = reference_ddim(model, (3, 1, 5, 5), s, steps, torch.Generator().manual_seed(8), clip)
            out = nb.ddim_sample(model, (3, 1, 5, 5), s, steps, torch.Generator().manual_seed(8), clip=clip)
            torch.testing.assert_close(out, expected, atol=1e-5, rtol=1e-4, msg=f"steps={steps}, clip={clip}")


def test_samplers_recover_single_point(nb):
    """Dữ liệu chỉ có một ảnh x*: với nhiễu đoán đúng, cả hai sampler phải trả đúng x*."""
    s = short_schedule()
    target = torch.linspace(-0.9, 0.9, 16).view(1, 1, 4, 4).double()
    oracle = Oracle(s["alpha_bars"], target, 0.0)
    shape = (3, 1, 4, 4)
    for out in (nb.ddpm_sample(oracle, shape, s, torch.Generator().manual_seed(0)),
                nb.ddim_sample(oracle, shape, s, 10, torch.Generator().manual_seed(0))):
        torch.testing.assert_close(out.double(), target.expand(shape), atol=1e-4, rtol=0)


def test_clip_applies_to_predicted_x0(nb):
    s = short_schedule()
    oracle = Oracle(s["alpha_bars"], 3.0, 0.0)
    shape = (2, 1, 2, 2)
    clipped = nb.ddpm_sample(oracle, shape, s, torch.Generator().manual_seed(0), clip=True)
    free = nb.ddpm_sample(oracle, shape, s, torch.Generator().manual_seed(0), clip=False)
    assert clipped.max().item() <= 1.0 + 1e-4
    torch.testing.assert_close(free.double(), torch.full(shape, 3.0, dtype=torch.float64), atol=1e-4, rtol=0)


def test_ddpm_sampler_gaussian_data(nb):
    """Dữ liệu N(0.3, 0.2²) từng pixel, nhiễu tối ưu dạng đóng: phân phối mẫu phải khớp dữ liệu."""
    s = short_schedule(1000, 1e-4, 0.02)
    oracle = Oracle(s["alpha_bars"], 0.3, 0.2)
    x = nb.ddpm_sample(oracle, (64, 1, 16, 16), s, torch.Generator().manual_seed(1), clip=False).double()
    assert x.mean().item() == pytest.approx(0.3, abs=0.01)
    assert x.std().item() == pytest.approx(0.2, abs=0.01)


def test_ema(nb):
    net = nn.Sequential(nn.Linear(3, 2), nn.BatchNorm1d(2))
    ema = nb.EMA(net, decay=0.9)
    w0 = net[0].weight.detach().clone()
    assert ema.shadow["0.weight"] is not net[0].weight
    with torch.no_grad():
        net[0].weight.add_(1.0)
    net.train()
    net(torch.randn(4, 3))
    ema.update(net)
    torch.testing.assert_close(ema.shadow["0.weight"], 0.9 * w0 + 0.1 * (w0 + 1.0))
    assert ema.shadow["1.num_batches_tracked"].item() == 1, "buffer kiểu nguyên thì chép"
    torch.testing.assert_close(ema.shadow["1.running_mean"], 0.1 * net[1].running_mean, atol=1e-7, rtol=0)
    other = nn.Sequential(nn.Linear(3, 2), nn.BatchNorm1d(2))
    ema.copy_to(other)
    torch.testing.assert_close(other[0].weight, ema.shadow["0.weight"])
