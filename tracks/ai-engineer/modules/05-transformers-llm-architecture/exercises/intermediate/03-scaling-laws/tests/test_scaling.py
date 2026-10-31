import math

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("scaling.ipynb")


def test_gpt_params(nb):
    p = nb.gpt_params(2, 32, 50, 16)
    assert p == {"total": 27_584, "non_embedding": 25_472}
    p = nb.gpt_params(4, 256, 8000, 128)
    assert p["total"] == 5_240_320, "GPT mini 4 tầng, n_embd 256, vocab 8 000, block 128"
    assert p["non_embedding"] == 5_240_320 - 8000 * 256 - 128 * 256
    big = nb.gpt_params(12, 768, 50257, 1024)
    assert big["total"] == pytest.approx(124.4e6, rel=0.01), "GPT-2 small khoảng 124 triệu tham số"


def test_train_flops(nb):
    assert nb.train_flops(1e6, 2e9) == pytest.approx(1.2e16)


@pytest.mark.parametrize("a,alpha,c", [(50.0, 0.3, 2.0), (8.0, 0.08, 0.5), (300.0, 0.5, 3.2)])
def test_fit_power_law_recovers(nb, a, alpha, c):
    x = np.geomspace(1e4, 1e8, 8)
    y = c + a * x ** -alpha
    fa, falpha, fc = nb.fit_power_law(x, y)
    assert falpha == pytest.approx(alpha, rel=0.05)
    assert fc == pytest.approx(c, abs=0.05 * c + 0.02)
    pred = fc + fa * x ** -falpha
    assert np.max(np.abs(pred - y)) < 0.01 * y.max()


def test_fit_power_law_noisy(nb):
    rng = np.random.default_rng(0)
    x = np.geomspace(1e5, 1e7, 6)
    y = 1.8 + 40.0 * x ** -0.25 + rng.normal(0, 0.003, 6)
    a, alpha, c = nb.fit_power_law(x, y)
    assert 0 <= c < y.min() and a > 0 and alpha > 0
    assert np.sqrt(np.mean((c + a * x ** -alpha - y) ** 2)) < 0.01


def test_chinchilla(nb):
    assert nb.chinchilla_loss(70e9, 1.4e12) == pytest.approx(1.69 + 406.4 / 70e9 ** 0.34 + 410.7 / 1.4e12 ** 0.28)
    assert nb.chinchilla_loss(70e9, 1.4e12) < nb.chinchilla_loss(280e9, 300e9)
    n, d = nb.chinchilla_optimal(6 * 70e9 * 1.4e12)
    assert n == pytest.approx(70e9, rel=1e-9) and d == pytest.approx(1.4e12, rel=1e-9)
    n, d = nb.chinchilla_optimal(6e20, tokens_per_param=100)
    assert d == pytest.approx(100 * n) and 6 * n * d == pytest.approx(6e20)
