import math

import pytest
import torch
import torch.nn.functional as F
from torch import nn

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)


@pytest.fixture(scope="module")
def gan():
    return ex.module("gan.py")


def logits(n, seed, scale=2.0):
    return scale * torch.randn(n, generator=torch.Generator().manual_seed(seed), dtype=torch.float64)


def test_d_loss_is_bce(gan):
    r, f = logits(8, 0), logits(6, 1)
    expected = F.binary_cross_entropy_with_logits(r, torch.ones_like(r)) + F.binary_cross_entropy_with_logits(f, torch.zeros_like(f))
    torch.testing.assert_close(gan.d_loss(r, f), expected)
    perfect = gan.d_loss(torch.full((4,), 50.0), torch.full((4,), -50.0))
    assert perfect.item() == pytest.approx(0.0, abs=1e-12)
    assert gan.d_loss(torch.zeros(4), torch.zeros(4)).item() == pytest.approx(2 * math.log(2))


def test_generator_losses_values(gan):
    f = logits(10, 2)
    d = torch.sigmoid(f)
    torch.testing.assert_close(gan.g_loss_saturating(f), torch.log(1 - d).mean())
    torch.testing.assert_close(gan.g_loss_nonsaturating(f), -torch.log(d).mean())


def test_generator_losses_stable(gan):
    f = torch.tensor([-200.0, 200.0])
    assert torch.isfinite(gan.g_loss_saturating(f)) and torch.isfinite(gan.g_loss_nonsaturating(f))
    assert gan.g_loss_nonsaturating(torch.tensor([-200.0])).item() == pytest.approx(200.0)


def test_saturating_gradient_vanishes(gan):
    """D phân biệt dễ (logit giả = -8): gradient của bản minimax gốc gần 0, bản non-saturating gần -1."""
    f1 = torch.tensor([-8.0], dtype=torch.float64, requires_grad=True)
    gan.g_loss_saturating(f1).backward()
    f2 = torch.tensor([-8.0], dtype=torch.float64, requires_grad=True)
    gan.g_loss_nonsaturating(f2).backward()
    assert abs(f1.grad.item()) < 1e-3
    assert f2.grad.item() == pytest.approx(-(1 - torch.sigmoid(torch.tensor(-8.0, dtype=torch.float64)).item()))
    assert f1.grad.item() < 0, "cả hai đều đẩy logit của mẫu giả lên"


def hist(seed, n=12, zeros=()):
    p = torch.rand(n, generator=torch.Generator().manual_seed(seed), dtype=torch.float64)
    for i in zeros:
        p[i] = 0
    return p / p.sum()


def test_optimal_discriminator(gan):
    p, q = hist(0, zeros=(3,)), hist(1, zeros=(3, 5))
    d = gan.optimal_discriminator(p, q)
    assert d[3].item() == 0.5, "ô cả hai phân phối bằng 0: quy ước 0.5"
    assert d[5].item() == 1.0
    mask = torch.ones(12, dtype=torch.bool)
    mask[3] = False
    torch.testing.assert_close(d[mask], (p / (p + q))[mask])


def test_js_divergence(gan):
    p, q = hist(2, zeros=(0,)), hist(3, zeros=(1,))
    m = (p + q) / 2
    def kl(a, b):
        keep = a > 0
        return (a[keep] * (a[keep] / b[keep]).log()).sum()
    expected = 0.5 * kl(p, m) + 0.5 * kl(q, m)
    torch.testing.assert_close(gan.js_divergence(p, q), expected)
    assert gan.js_divergence(p, p).item() == pytest.approx(0.0, abs=1e-12)
    a = torch.tensor([1.0, 0.0], dtype=torch.float64)
    b = torch.tensor([0.0, 1.0], dtype=torch.float64)
    assert gan.js_divergence(a, b).item() == pytest.approx(math.log(2)), "hai phân phối rời nhau: JS = log 2 (nats)"


def test_value_at_optimal_d_is_js(gan):
    """Goodfellow 2014, định lý 1: V(D*, G) = -log 4 + 2 JS(p_data || p_g)."""
    for seed in range(3):
        p, q = hist(10 + seed, zeros=(2,)), hist(20 + seed, zeros=(7,))
        v = gan.gan_value(p, q, gan.optimal_discriminator(p, q))
        assert v.item() == pytest.approx(-math.log(4) + 2 * gan.js_divergence(p, q).item(), abs=1e-10)
    p = hist(30)
    assert gan.gan_value(p, p, torch.full_like(p, 0.5)).item() == pytest.approx(-math.log(4))
    d_other = torch.full_like(p, 0.7)
    assert gan.gan_value(p, hist(31), d_other).item() < gan.gan_value(p, hist(31), gan.optimal_discriminator(p, hist(31))).item()


def test_gradient_penalty_linear_critic(gan):
    """Critic tuyến tính f(x) = w·x: gradient theo x là w ở mọi điểm, nên penalty = (||w|| - 1)^2."""
    critic = nn.Linear(6, 1, bias=True).double()
    with torch.no_grad():
        critic.weight.copy_(torch.tensor([[1.0, 2.0, 0.0, -2.0, 0.0, 0.0]]))
    real, fake = logits(24, 4).reshape(4, 6), logits(24, 5).reshape(4, 6)
    gp = gan.gradient_penalty(critic, real, fake, torch.rand(4, dtype=torch.float64))
    assert gp.item() == pytest.approx((3.0 - 1.0) ** 2)
    gp.backward()
    w = critic.weight.detach()
    torch.testing.assert_close(critic.weight.grad, 2 * (w.norm() - 1) * w / w.norm(), msg="penalty phải giữ graph (create_graph=True)")


def test_gradient_penalty_interpolates(gan):
    """Critic f(x) = sum x^2 / 2 có gradient x: penalty đo đúng tại điểm nội suy alpha * real + (1 - alpha) * fake."""
    real = torch.tensor([[3.0, 0.0], [0.0, 1.0]], dtype=torch.float64)
    fake = torch.tensor([[1.0, 0.0], [0.0, 5.0]], dtype=torch.float64)
    alpha = torch.tensor([0.5, 0.25], dtype=torch.float64)
    gp = gan.gradient_penalty(lambda x: 0.5 * (x ** 2).sum(1), real, fake, alpha)
    expected = ((2.0 - 1) ** 2 + (4.0 - 1) ** 2) / 2
    assert gp.item() == pytest.approx(expected)


def ring(n_modes=8, radius=2.0):
    ang = torch.arange(n_modes, dtype=torch.float64) * 2 * math.pi / n_modes
    return torch.stack([radius * ang.cos(), radius * ang.sin()], 1)


def test_mode_coverage(gan):
    centers = ring()
    g = torch.Generator().manual_seed(0)
    idx = torch.arange(800) % 8
    full = centers[idx] + 0.05 * torch.randn(800, 2, generator=g, dtype=torch.float64)
    modes, hq = gan.mode_coverage(full, centers, 0.05)
    assert modes == 8 and hq > 0.98
    collapsed = centers[idx % 3] + 0.05 * torch.randn(800, 2, generator=g, dtype=torch.float64)
    modes, hq = gan.mode_coverage(collapsed, centers, 0.05)
    assert modes == 3 and hq > 0.98
    blurry = 3.0 * torch.randn(800, 2, generator=g, dtype=torch.float64)
    modes, hq = gan.mode_coverage(blurry, centers, 0.05)
    assert hq < 0.05, "mẫu nằm xa mọi tâm không được tính chất lượng cao"
    assert modes == 0, "mode chỉ tính mẫu chất lượng cao, không tính mẫu nằm xa"


def test_mode_coverage_min_count(gan):
    centers = ring()
    samples = torch.cat([centers[0].repeat(50, 1), centers[1].repeat(9, 1), centers[2].repeat(10, 1)])
    assert gan.mode_coverage(samples, centers, 0.05)[0] == 2
    assert gan.mode_coverage(samples, centers, 0.05, min_count=1)[0] == 3
