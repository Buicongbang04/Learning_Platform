import math

import pytest
import torch
import torch.nn.functional as F
from torch.distributions import MultivariateNormal, Normal, kl_divergence

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)


@pytest.fixture(scope="module")
def vae():
    return ex.module("vae.py")


def rand(*shape, seed=0, scale=1.0):
    return scale * torch.randn(*shape, generator=torch.Generator().manual_seed(seed), dtype=torch.float64)


def test_gaussian_kl_matches_torch(vae):
    mu, logvar = rand(5, 4, seed=1), rand(5, 4, seed=2)
    kl = vae.gaussian_kl(mu, logvar)
    assert kl.shape == (5,)
    expected = kl_divergence(Normal(mu, (0.5 * logvar).exp()), Normal(torch.zeros_like(mu), torch.ones_like(mu))).sum(1)
    torch.testing.assert_close(kl, expected)
    assert torch.all(kl > 0)
    torch.testing.assert_close(vae.gaussian_kl(torch.zeros(2, 3), torch.zeros(2, 3)), torch.zeros(2))


def test_reparameterize_uses_generator(vae):
    mu, logvar = rand(3, 4, seed=3), rand(3, 4, seed=4)
    z1 = vae.reparameterize(mu, logvar, torch.Generator().manual_seed(7))
    z2 = vae.reparameterize(mu, logvar, torch.Generator().manual_seed(7))
    torch.testing.assert_close(z1, z2)
    eps = torch.randn(mu.shape, generator=torch.Generator().manual_seed(7), dtype=mu.dtype)
    torch.testing.assert_close(z1, mu + (0.5 * logvar).exp() * eps, msg="z = mu + exp(logvar / 2) * eps")


def test_reparameterize_gradient_flows(vae):
    mu = rand(2, 3, seed=5).requires_grad_()
    logvar = rand(2, 3, seed=6).requires_grad_()
    z = vae.reparameterize(mu, logvar, torch.Generator().manual_seed(1))
    z.sum().backward()
    assert mu.grad is not None and logvar.grad is not None, "gradient phải chảy về mu và logvar"
    eps = torch.randn(mu.shape, generator=torch.Generator().manual_seed(1), dtype=mu.dtype)
    torch.testing.assert_close(mu.grad, torch.ones_like(mu))
    torch.testing.assert_close(logvar.grad, 0.5 * (0.5 * logvar.detach()).exp() * eps)


def test_reparameterize_distribution(vae):
    mu = torch.full((200_000, 1), 2.0)
    logvar = torch.full((200_000, 1), math.log(0.25))
    z = vae.reparameterize(mu, logvar, torch.Generator().manual_seed(0))
    assert z.mean().item() == pytest.approx(2.0, abs=0.01)
    assert z.var().item() == pytest.approx(0.25, abs=0.01)


def test_bernoulli_log_likelihood(vae):
    logits = rand(4, 1, 5, 5, seed=8, scale=3.0)
    x = torch.rand(4, 1, 5, 5, generator=torch.Generator().manual_seed(9), dtype=torch.float64)
    ll = vae.bernoulli_log_likelihood(logits, x)
    assert ll.shape == (4,)
    expected = -F.binary_cross_entropy_with_logits(logits, x, reduction="none").flatten(1).sum(1)
    torch.testing.assert_close(ll, expected)


def test_bernoulli_log_likelihood_stable(vae):
    logits = torch.tensor([[100.0, -100.0, 100.0, -100.0]])
    x = torch.tensor([[1.0, 0.0, 0.0, 1.0]])
    ll = vae.bernoulli_log_likelihood(logits, x)
    assert torch.isfinite(ll).all(), "logits ±100 không được ra inf/nan"
    assert ll.item() == pytest.approx(-200.0, abs=1e-3)


def test_gaussian_log_density_and_broadcast(vae):
    z, mu, logvar = rand(6, 3, 4, seed=10), rand(3, 4, seed=11), rand(3, 4, seed=12)
    out = vae.gaussian_log_density(z, mu, logvar)
    assert out.shape == (6, 3)
    expected = Normal(mu, (0.5 * logvar).exp()).log_prob(z).sum(-1)
    torch.testing.assert_close(out, expected)


def test_elbo_combines_terms(vae):
    logits, x = rand(3, 6, seed=13), torch.rand(3, 6, generator=torch.Generator().manual_seed(14), dtype=torch.float64)
    mu, logvar = rand(3, 2, seed=15), rand(3, 2, seed=16)
    e1, recon, kl = vae.elbo(logits, x, mu, logvar)
    torch.testing.assert_close(recon, vae.bernoulli_log_likelihood(logits, x))
    torch.testing.assert_close(kl, vae.gaussian_kl(mu, logvar))
    torch.testing.assert_close(e1, recon - kl)
    e4, _, _ = vae.elbo(logits, x, mu, logvar, beta=4.0)
    torch.testing.assert_close(e4, recon - 4.0 * kl)
    assert torch.all(e1 < recon), "ELBO = recon - KL, KL > 0 nên ELBO nhỏ hơn recon"


def linear_gaussian(seed=0):
    """z ~ N(0, I_2), x | z ~ N(W z + b, s2 I_3): log p(x) và posterior p(z | x) có dạng đóng."""
    g = torch.Generator().manual_seed(seed)
    W = torch.randn(3, 2, generator=g, dtype=torch.float64)
    b = torch.randn(3, generator=g, dtype=torch.float64)
    s2 = 0.3
    x = torch.randn(4, 3, generator=g, dtype=torch.float64)
    cov = W @ W.T + s2 * torch.eye(3, dtype=torch.float64)
    log_px = MultivariateNormal(b, cov).log_prob(x)
    post_cov = torch.linalg.inv(torch.eye(2, dtype=torch.float64) + W.T @ W / s2)
    post_mu = (x - b) @ W / s2 @ post_cov
    return W, b, s2, x, log_px, post_mu, post_cov


def iw_estimate(vae, W, b, s2, x, q_mu, q_logvar, K, seed):
    z = q_mu + (0.5 * q_logvar).exp() * torch.randn(K, *q_mu.shape, generator=torch.Generator().manual_seed(seed), dtype=torch.float64)
    log_px_z = vae.gaussian_log_density(x.expand(K, -1, -1), z @ W.T + b, torch.full((K, *x.shape), math.log(s2), dtype=torch.float64))
    log_pz = vae.gaussian_log_density(z, torch.zeros_like(z), torch.zeros_like(z))
    log_qz = vae.gaussian_log_density(z, q_mu, q_logvar)
    return vae.importance_log_likelihood(log_px_z, log_pz, log_qz)


def test_importance_exact_with_true_posterior(vae):
    """Posterior thật có hiệp phương sai đầy đủ; dùng một hướng chéo hoá được: W trực giao theo cột thì posterior là đường chéo."""
    W = torch.tensor([[1.0, 0.0], [0.0, 2.0], [0.0, 0.0]], dtype=torch.float64)
    b = torch.tensor([0.5, -1.0, 0.2], dtype=torch.float64)
    s2 = 0.5
    x = rand(4, 3, seed=20)
    log_px = MultivariateNormal(b, W @ W.T + s2 * torch.eye(3, dtype=torch.float64)).log_prob(x)
    post_var = 1 / (1 + (W ** 2).sum(0) / s2)
    post_mu = (x - b) @ W / s2 * post_var
    q_logvar = post_var.log().expand_as(post_mu)
    est = iw_estimate(vae, W, b, s2, x, post_mu, q_logvar, K=3, seed=1)
    assert est.shape == (4,)
    torch.testing.assert_close(est, log_px, msg="q đúng bằng posterior thì mọi trọng số bằng p(x): ước lượng chính xác")


def test_elbo_below_iwae_below_log_px(vae):
    W, b, s2, x, log_px, post_mu, post_cov = linear_gaussian(1)
    q_mu, q_logvar = post_mu + 0.5, torch.zeros_like(post_mu)
    elbo_est = torch.stack([iw_estimate(vae, W, b, s2, x, q_mu, q_logvar, K=1, seed=s) for s in range(2000)]).mean(0)
    iw = torch.stack([iw_estimate(vae, W, b, s2, x, q_mu, q_logvar, K=200, seed=10_000 + s) for s in range(10)]).mean(0)
    assert torch.all(elbo_est < iw), "K = 1 là ELBO; K lớn hơn cho cận chặt hơn"
    assert torch.all(iw <= log_px + 0.05), "cận IWAE không vượt log p(x)"
    assert torch.all(log_px - iw < 0.5 * (log_px - elbo_est))


def test_importance_log_likelihood_stable(vae):
    log_px_z = torch.tensor([[-1000.0], [-1001.0], [-1002.0]], dtype=torch.float64)
    zeros = torch.zeros_like(log_px_z)
    out = vae.importance_log_likelihood(log_px_z, zeros, zeros)
    expected = -1000 + math.log((1 + math.exp(-1) + math.exp(-2)) / 3)
    assert torch.isfinite(out).all()
    assert out.item() == pytest.approx(expected, abs=1e-9)
