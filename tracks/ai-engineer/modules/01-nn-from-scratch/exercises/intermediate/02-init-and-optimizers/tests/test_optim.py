import numpy as np
import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("optim.ipynb")


# ---------- Khởi tạo ----------

def test_he_init_variance(nb):
    W = nb.he_init(1000, 1000, np.random.default_rng(0))
    assert W.shape == (1000, 1000)
    assert W.var() == pytest.approx(2 / 1000, rel=0.05)
    assert abs(W.mean()) < 1e-3


def test_he_init_uses_fan_in(nb):
    W = nb.he_init(1000, 10, np.random.default_rng(1))
    assert W.shape == (1000, 10)
    assert W.var() == pytest.approx(2 / 1000, rel=0.05), "He: phương sai 2 / fan_in, không phải 2 / fan_out"


def test_xavier_init_variance(nb):
    W = nb.xavier_init(1000, 500, np.random.default_rng(2))
    assert W.shape == (1000, 500)
    assert W.var() == pytest.approx(2 / 1500, rel=0.05)
    assert abs(W.mean()) < 1e-3


def test_init_uses_rng(nb):
    for init in (nb.he_init, nb.xavier_init):
        a = init(50, 40, np.random.default_rng(3))
        b = init(50, 40, np.random.default_rng(3))
        c = init(50, 40, np.random.default_rng(4))
        assert np.array_equal(a, b), "cùng seed phải ra cùng ma trận: chỉ lấy số ngẫu nhiên từ rng"
        assert not np.array_equal(a, c)


# ---------- Optimizer: 20 bước trên hàm bậc hai, so với torch.optim ----------

def quadratic(seed: int = 0):
    """f = Σ c ⊙ (θ − θ*)² / 2 cho hai tham số W (3, 4) và b (4,), độ cong c khác nhau theo từng toạ độ."""
    rng = np.random.default_rng(seed)
    start = [rng.normal(size=(3, 4)), rng.normal(size=4)]
    target = [rng.normal(size=(3, 4)), rng.normal(size=4)]
    curv = [rng.uniform(0.5, 5.0, (3, 4)), rng.uniform(0.5, 5.0, 4)]
    return start, target, curv


def run_numpy(opt, steps: int = 20) -> list[np.ndarray]:
    start, target, curv = quadratic()
    params = [p.copy() for p in start]
    for _ in range(steps):
        grads = [c * (p - t) for p, t, c in zip(params, target, curv)]
        opt.step(list(zip(params, grads)))
    return params


def run_torch(make_opt, steps: int = 20) -> list[np.ndarray]:
    start, target, curv = quadratic()
    params = [torch.tensor(p, requires_grad=True) for p in start]
    target = [torch.tensor(t) for t in target]
    curv = [torch.tensor(c) for c in curv]
    opt = make_opt(params)
    for _ in range(steps):
        opt.zero_grad()
        loss = sum((c * (p - t) ** 2).sum() / 2 for p, t, c in zip(params, target, curv))
        loss.backward()
        opt.step()
    return [p.detach().numpy() for p in params]


def assert_same(ours: list[np.ndarray], ref: list[np.ndarray]) -> None:
    start, _, _ = quadratic()
    assert not np.allclose(ours[0], start[0]), "step phải cập nhật chính các mảng tham số (tại chỗ)"
    for a, b in zip(ours, ref):
        np.testing.assert_allclose(a, b, rtol=0, atol=1e-6)


@pytest.mark.parametrize("momentum", [0.0, 0.9])
def test_sgd_momentum_matches_torch(nb, momentum):
    ours = run_numpy(nb.SGDMomentum(lr=0.05, momentum=momentum))
    ref = run_torch(lambda ps: torch.optim.SGD(ps, lr=0.05, momentum=momentum))
    assert_same(ours, ref)


@pytest.mark.parametrize("betas", [(0.9, 0.999), (0.8, 0.95)])
def test_adam_matches_torch(nb, betas):
    ours = run_numpy(nb.Adam(lr=0.05, betas=betas))
    ref = run_torch(lambda ps: torch.optim.AdamW(ps, lr=0.05, betas=betas, weight_decay=0.0))
    assert_same(ours, ref)


def test_adamw_matches_torch(nb):
    ours = run_numpy(nb.Adam(lr=0.05, weight_decay=0.1))
    ref = run_torch(lambda ps: torch.optim.AdamW(ps, lr=0.05, weight_decay=0.1))
    assert_same(ours, ref)


def test_adamw_decay_is_decoupled(nb):
    # gradient bằng 0: Adam thuần đứng yên; AdamW vẫn co tham số đúng hệ số (1 − lr·λ) mỗi bước
    p = np.full(3, 2.0)
    nb.Adam(lr=0.1, weight_decay=0.5).step([(p, np.zeros(3))])
    np.testing.assert_allclose(p, 2.0 * (1 - 0.1 * 0.5), rtol=0, atol=1e-12)
    q = np.full(3, 2.0)
    nb.Adam(lr=0.1).step([(q, np.zeros(3))])
    np.testing.assert_array_equal(q, np.full(3, 2.0))


def test_adam_first_step_is_lr_times_sign(nb):
    # bias correction: bước đầu m̂ = g, v̂ = g², nên mỗi toạ độ đi đúng lr theo dấu gradient, dù g lớn hay nhỏ
    p = np.zeros(3)
    nb.Adam(lr=0.01).step([(p, np.array([1e-3, -5.0, 200.0]))])
    np.testing.assert_allclose(p, [-0.01, 0.01, -0.01], rtol=1e-4)
