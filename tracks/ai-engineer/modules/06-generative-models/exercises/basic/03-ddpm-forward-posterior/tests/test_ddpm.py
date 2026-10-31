import math

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(2)


@pytest.fixture(scope="module")
def ddpm():
    return ex.module("ddpm.py")


def small_betas(T: int = 10) -> torch.Tensor:
    return torch.linspace(0.05, 0.4, T, dtype=torch.float64)


def test_linear_betas(ddpm):
    b = ddpm.linear_betas()
    assert b.shape == (1000,) and b.dtype == torch.float64
    assert b[0].item() == pytest.approx(1e-4) and b[-1].item() == pytest.approx(0.02)
    assert torch.all(b[1:] > b[:-1])
    b2 = ddpm.linear_betas(5, 0.1, 0.5)
    torch.testing.assert_close(b2, torch.tensor([0.1, 0.2, 0.3, 0.4, 0.5], dtype=torch.float64))


def test_alpha_bars(ddpm):
    b = small_betas()
    ab = ddpm.alpha_bars(b)
    expected, acc = [], 1.0
    for beta in b.tolist():
        acc *= 1 - beta
        expected.append(acc)
    torch.testing.assert_close(ab, torch.tensor(expected, dtype=torch.float64))


def test_cosine_betas(ddpm):
    T, s = 1000, 0.008
    b = ddpm.cosine_betas(T)
    assert b.shape == (T,) and b.dtype == torch.float64
    assert b.max().item() == pytest.approx(0.999), "beta cuối bị chặn ở max_beta"
    ab = ddpm.alpha_bars(b)
    f = lambda u: math.cos((u / T + s) / (1 + s) * math.pi / 2) ** 2
    for t in (0, 10, 250, 500, 900):
        assert ab[t].item() == pytest.approx(f(t + 1) / f(0), rel=1e-9), f"alpha_bar[{t}] = f({t + 1}) / f(0)"
    assert torch.all(b > 0) and torch.all(b[1:] >= b[:-1] - 1e-12)
    assert ab[-1].item() < 1e-6


def test_q_sample_formula_and_per_sample_t(ddpm):
    b = small_betas()
    ab = ddpm.alpha_bars(b)
    g = torch.Generator().manual_seed(0)
    x0 = torch.randn(4, 2, 3, 3, generator=g)
    noise = torch.randn(4, 2, 3, 3, generator=g)
    t = torch.tensor([0, 3, 9, 3])
    out = ddpm.q_sample(x0, t, noise, ab)
    assert out.shape == x0.shape and out.dtype == x0.dtype
    for i in range(4):
        a = ab[t[i]].item()
        torch.testing.assert_close(out[i], math.sqrt(a) * x0[i] + math.sqrt(1 - a) * noise[i])


def test_q_sample_matches_iterated_chain(ddpm):
    """Chạy chuỗi Markov x_t = sqrt(1 - beta) x_{t-1} + sqrt(beta) eps từng bước, so phân phối với dạng đóng."""
    b = small_betas(8)
    ab = ddpm.alpha_bars(b)
    g = torch.Generator().manual_seed(1)
    n = 200_000
    x0 = torch.full((n, 1), 1.5, dtype=torch.float64)
    x = x0.clone()
    for beta in b:
        x = (1 - beta).sqrt() * x + beta.sqrt() * torch.randn(n, 1, generator=g, dtype=torch.float64)
    closed = ddpm.q_sample(x0, torch.full((n,), 7), torch.randn(n, 1, generator=g, dtype=torch.float64), ab)
    for sample in (x, closed):
        assert sample.mean().item() == pytest.approx(1.5 * math.sqrt(ab[-1].item()), abs=0.01)
        assert sample.var().item() == pytest.approx(1 - ab[-1].item(), abs=0.01)


def bayes_posterior(x0, xt, t, betas):
    """Tích hai Gauss q(x_{t-1} | x_0) và q(x_t | x_{t-1}) theo x_{t-1}: viết theo độ chính xác (precision)."""
    alphas = 1 - betas
    ab = torch.cumprod(alphas, 0)
    ab_prev = 1.0 if t == 0 else ab[t - 1].item()
    a_t, b_t = alphas[t].item(), betas[t].item()
    if t == 0:
        return x0, 0.0
    prec = 1 / (1 - ab_prev) + a_t / b_t
    var = 1 / prec
    mean = var * (math.sqrt(ab_prev) * x0 / (1 - ab_prev) + math.sqrt(a_t) * xt / b_t)
    return mean, var


def test_q_posterior_matches_bayes(ddpm):
    b = small_betas()
    g = torch.Generator().manual_seed(2)
    t = torch.tensor([0, 1, 4, 9])
    x0 = torch.randn(4, 3, generator=g, dtype=torch.float64)
    xt = torch.randn(4, 3, generator=g, dtype=torch.float64)
    mean, var = ddpm.q_posterior(x0, xt, t, b)
    assert mean.shape == x0.shape
    var = torch.as_tensor(var).expand_as(x0)
    for i, ti in enumerate(t.tolist()):
        m, v = bayes_posterior(x0[i], xt[i], ti, b)
        torch.testing.assert_close(mean[i], torch.as_tensor(m, dtype=torch.float64))
        torch.testing.assert_close(var[i], torch.full((3,), float(v), dtype=torch.float64), atol=1e-12, rtol=1e-9)


def test_predict_x0_inverts_q_sample(ddpm):
    b = ddpm.linear_betas(50, 1e-3, 0.2)
    ab = ddpm.alpha_bars(b)
    g = torch.Generator().manual_seed(3)
    x0 = torch.randn(5, 4, generator=g, dtype=torch.float64)
    eps = torch.randn(5, 4, generator=g, dtype=torch.float64)
    t = torch.tensor([0, 7, 20, 33, 49])
    xt = ddpm.q_sample(x0, t, eps, ab)
    torch.testing.assert_close(ddpm.predict_x0(xt, t, eps, ab), x0)


def test_p_mean_with_true_noise_equals_posterior(ddpm):
    """Model đoán đúng nhiễu thì mean của p(x_{t-1} | x_t) phải trùng mean của posterior thật."""
    b = ddpm.linear_betas(50, 1e-3, 0.2)
    ab = ddpm.alpha_bars(b)
    g = torch.Generator().manual_seed(4)
    x0 = torch.randn(4, 6, generator=g, dtype=torch.float64)
    eps = torch.randn(4, 6, generator=g, dtype=torch.float64)
    t = torch.tensor([0, 1, 25, 49])
    xt = ddpm.q_sample(x0, t, eps, ab)
    mean, var = ddpm.p_mean_variance(xt, t, eps, b)
    pmean, pvar = ddpm.q_posterior(x0, xt, t, b)
    torch.testing.assert_close(mean, pmean)
    torch.testing.assert_close(torch.as_tensor(var).expand_as(x0), torch.as_tensor(pvar).expand_as(x0))


def test_snr(ddpm):
    ab = torch.tensor([0.5, 0.2, 0.9], dtype=torch.float64)
    torch.testing.assert_close(ddpm.snr(ab), torch.tensor([1.0, 0.25, 9.0], dtype=torch.float64))
