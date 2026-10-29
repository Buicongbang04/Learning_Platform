import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def opt():
    return ex.module("optimizers.py")


def ill_conditioned(seed: int, eigenvalues=(1.0, 3.0, 10.0, 40.0, 100.0)):
    """Hàm bậc hai bị xoay ngẫu nhiên, condition number = 100."""
    rng = np.random.default_rng(seed)
    Q, _ = np.linalg.qr(rng.normal(size=(5, 5)))
    A = Q @ np.diag(eigenvalues) @ Q.T
    b = rng.normal(size=5)
    return A, b, np.linalg.solve(A, b), rng.normal(size=5)


def regression(n: int = 5000, seed: int = 0):
    rng = np.random.default_rng(seed)
    Z = rng.normal(size=(n, 3))
    Z[:, 1] = 0.8 * Z[:, 0] + 0.6 * Z[:, 1]
    X = np.column_stack([np.ones(n), Z])
    y = X @ np.array([20.0, 6.0, 4.0, -2.0]) + rng.normal(0, 10, n)
    return X, y


def test_quadratic_grad(opt):
    A, b, w_star, w0 = ill_conditioned(0)
    g = opt.quadratic_grad(A, b)
    assert g(w_star) == pytest.approx(np.zeros(5), abs=1e-10)
    assert g(w0) == pytest.approx(A @ w0 - b)


def test_gd_path_matches_closed_form(opt):
    # A = diag(1, 10), b = 0, lr = 0.1: w_t = ((0.9)^t, 0^t)
    path = opt.gd(opt.quadratic_grad(np.diag([1.0, 10.0]), np.zeros(2)), np.array([1.0, 1.0]), lr=0.1, n_iter=5)
    assert path.shape == (6, 2)
    assert path[:, 0] == pytest.approx(0.9 ** np.arange(6))
    assert path[1:, 1] == pytest.approx(np.zeros(5), abs=1e-15)


def test_gd_diverges_above_two_over_L(opt):
    A, b, w_star, w0 = ill_conditioned(1)
    path = opt.gd(opt.quadratic_grad(A, b), w0, lr=2.1 / 100, n_iter=300)
    assert np.linalg.norm(path[-1] - w_star) > 100 * np.linalg.norm(w0 - w_star)


def test_iterations_to_tol(opt):
    path = np.array([[4.0], [2.0], [1.0], [0.5], [0.03]])
    assert opt.iterations_to_tol(path, np.array([0.0]), tol=0.25) == 2
    assert opt.iterations_to_tol(path, np.array([0.0]), tol=0.001) == -1


def test_momentum_with_zero_beta_is_gd(opt):
    A, b, _, w0 = ill_conditioned(2)
    g = opt.quadratic_grad(A, b)
    assert opt.momentum(g, w0, lr=0.01, beta=0.0, n_iter=50) == pytest.approx(opt.gd(g, w0, lr=0.01, n_iter=50))


def test_momentum_first_steps(opt):
    # f(w) = ½ w², w0 = 1, lr = 0.1, β = 0.5: v1 = −0.1, w1 = 0.9; v2 = −0.05 − 0.09, w2 = 0.76
    path = opt.momentum(lambda w: w, np.array([1.0]), lr=0.1, beta=0.5, n_iter=2)
    assert path[:, 0] == pytest.approx([1.0, 0.9, 0.76])


def test_optimal_momentum_params(opt):
    lr, beta = opt.optimal_momentum_params(1.0, 100.0)
    assert lr == pytest.approx(4 / 121)
    assert beta == pytest.approx((9 / 11) ** 2)


@pytest.mark.parametrize("seed", range(10))
def test_momentum_beats_gd_on_ill_conditioned_problem(opt, seed):
    A, b, w_star, w0 = ill_conditioned(seed)
    g = opt.quadratic_grad(A, b)
    it_gd = opt.iterations_to_tol(opt.gd(g, w0, lr=1 / 100, n_iter=3000), w_star)
    lr, beta = opt.optimal_momentum_params(1.0, 100.0)
    it_mom = opt.iterations_to_tol(opt.momentum(g, w0, lr, beta, n_iter=3000), w_star)
    assert 0 < it_gd and 0 < it_mom < it_gd / 5


def test_sgd_full_batch_equals_gd(opt):
    X, y = regression(n=500, seed=1)
    w, losses = opt.sgd_linreg(X, y, lr0=0.1, n_epochs=30, batch_size=500, seed=0)
    w_gd = np.zeros(4)
    for _ in range(30):
        w_gd = w_gd - 0.1 * 2 / 500 * X.T @ (X @ w_gd - y)
    assert w == pytest.approx(w_gd, rel=1e-9)
    assert len(losses) == 30 and losses[-1] == pytest.approx(np.mean((X @ w - y) ** 2))


def test_sgd_reproducible_with_seed(opt):
    X, y = regression(n=1000, seed=2)
    w1, _ = opt.sgd_linreg(X, y, lr0=0.05, n_epochs=3, batch_size=32, seed=7)
    w2, _ = opt.sgd_linreg(X, y, lr0=0.05, n_epochs=3, batch_size=32, seed=7)
    w3, _ = opt.sgd_linreg(X, y, lr0=0.05, n_epochs=3, batch_size=32, seed=8)
    assert np.array_equal(w1, w2) and not np.array_equal(w1, w3)


@pytest.mark.parametrize("seed", range(10))
def test_decaying_lr_beats_constant_lr_noise_floor(opt, seed):
    X, y = regression(seed=seed)
    ref, *_ = np.linalg.lstsq(X, y, rcond=None)
    w_const, _ = opt.sgd_linreg(X, y, lr0=0.05, n_epochs=20, batch_size=16, seed=seed)
    w_decay, _ = opt.sgd_linreg(X, y, lr0=0.05, n_epochs=20, batch_size=16, seed=seed, decay=0.01)
    d_const, d_decay = np.linalg.norm(w_const - ref), np.linalg.norm(w_decay - ref)
    assert d_const > 0.2            # lr cố định: w nhảy quanh nghiệm, không bao giờ "đậu"
    assert d_decay < 0.1 and d_decay < d_const / 5
