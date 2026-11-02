import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def R():
    return ex.module("returns.py")


def buffer(T: int, seed: int, n_envs: int | None = None):
    rng = np.random.default_rng(seed)
    shape = (T,) if n_envs is None else (T, n_envs)
    rewards = rng.normal(size=shape)
    values = rng.normal(size=shape)
    next_values = rng.normal(size=shape)
    no_end = np.zeros(shape, dtype=bool)
    return rewards, values, next_values, no_end


def gae_by_definition(rewards, values, next_values, terminated, truncated, gamma, lam):
    """A_t = Σ_k (γλ)^k δ_{t+k}, dừng ở bước cuối của episode. Chậm nhưng thẳng theo định nghĩa."""
    T = len(rewards)
    deltas = rewards + gamma * (1 - terminated) * next_values - values
    adv = np.zeros(T)
    for t in range(T):
        coef = 1.0
        for k in range(t, T):
            adv[t] += coef * deltas[k]
            if terminated[k] or truncated[k]:
                break
            coef *= gamma * lam
    return adv


def test_reward_to_go(R):
    out = R.reward_to_go(np.array([1.0, 0.0, 2.0]), 0.5)
    np.testing.assert_allclose(out, [1 + 0.5 * 0 + 0.25 * 2, 0 + 0.5 * 2, 2.0])
    assert R.reward_to_go(np.ones(4), 1.0).tolist() == [4.0, 3.0, 2.0, 1.0]


def test_gae_lambda_zero_is_td_error(R):
    r, v, nv, no_end = buffer(6, 0)
    adv, ret = R.gae(r, v, nv, no_end, no_end, 0.9, 0.0)
    np.testing.assert_allclose(adv, r + 0.9 * nv - v, atol=1e-12)
    np.testing.assert_allclose(ret, adv + v, atol=1e-12)


def test_gae_lambda_one_is_monte_carlo(R):
    rng = np.random.default_rng(1)
    r = rng.normal(size=5)
    v = rng.normal(size=5)
    term = np.array([False, False, False, False, True])
    nv = np.append(v[1:], 123.0)  # critic nhất quán: V(s_{t+1}) của bước t là values[t+1]
    adv, ret = R.gae(r, v, nv, term, np.zeros(5, bool), 0.97, 1.0)
    np.testing.assert_allclose(ret, R.reward_to_go(r, 0.97), atol=1e-10)
    np.testing.assert_allclose(adv, R.reward_to_go(r, 0.97) - v, atol=1e-10)


def test_gae_matches_definition_with_episode_ends(R):
    r, v, nv, _ = buffer(12, 2)
    term = np.zeros(12, bool)
    trunc = np.zeros(12, bool)
    term[3] = True
    trunc[7] = True
    adv, ret = R.gae(r, v, nv, term, trunc, 0.95, 0.9)
    np.testing.assert_allclose(adv, gae_by_definition(r, v, nv, term, trunc, 0.95, 0.9), atol=1e-12)


def test_gae_terminated_vs_truncated(R):
    r = np.array([1.0])
    v = np.array([0.5])
    nv = np.array([10.0])
    adv_term, _ = R.gae(r, v, nv, np.array([True]), np.array([False]), 0.9, 0.95)
    adv_trunc, _ = R.gae(r, v, nv, np.array([False]), np.array([True]), 0.9, 0.95)
    assert adv_term[0] == pytest.approx(1.0 - 0.5), "terminated: không bootstrap"
    assert adv_trunc[0] == pytest.approx(1.0 + 0.9 * 10.0 - 0.5), "truncated: vẫn bootstrap từ next_values"


def test_gae_does_not_leak_across_episodes(R):
    r = np.array([0.0, 100.0])
    v = np.zeros(2)
    nv = np.zeros(2)
    for term, trunc in [([True, False], [False, False]), ([False, False], [True, False])]:
        adv, _ = R.gae(r, v, nv, np.array(term), np.array(trunc), 0.99, 0.95)
        assert adv[0] == pytest.approx(0.0), "reward của episode sau không được chảy ngược về episode trước"


def test_gae_vectorized(R):
    r, v, nv, _ = buffer(9, 3, n_envs=3)
    term = np.zeros((9, 3), bool)
    trunc = np.zeros((9, 3), bool)
    term[2, 0] = True
    trunc[5, 1] = True
    term[8, 2] = True
    adv, ret = R.gae(r, v, nv, term, trunc, 0.99, 0.95)
    assert adv.shape == (9, 3) and ret.shape == (9, 3)
    for i in range(3):
        col, _ = R.gae(r[:, i], v[:, i], nv[:, i], term[:, i], trunc[:, i], 0.99, 0.95)
        np.testing.assert_allclose(adv[:, i], col, atol=1e-12)
        np.testing.assert_allclose(col, gae_by_definition(r[:, i], v[:, i], nv[:, i], term[:, i], trunc[:, i], 0.99, 0.95))


def test_n_step_one_is_td_target(R):
    r, v, nv, no_end = buffer(5, 4)
    term = no_end.copy()
    term[2] = True
    out = R.n_step_returns(r, nv, term, no_end, 0.9, 1)
    np.testing.assert_allclose(out, r + 0.9 * (1 - term) * nv, atol=1e-12)


def test_n_step_three(R):
    r = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    nv = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    no_end = np.zeros(5, bool)
    g = 0.5
    out = R.n_step_returns(r, nv, no_end, no_end, g, 3)
    assert out[0] == pytest.approx(1 + g * 2 + g**2 * 3 + g**3 * 30)
    assert out[2] == pytest.approx(3 + g * 4 + g**2 * 5 + g**3 * 50)
    assert out[4] == pytest.approx(5 + g * 50), "cuối buffer: bootstrap từ next_values của bước cuối"


def test_n_step_stops_at_episode_end(R):
    r = np.array([1.0, 2.0, 3.0, 4.0])
    nv = np.array([10.0, 20.0, 30.0, 40.0])
    term = np.array([False, True, False, False])
    trunc = np.array([False, False, False, False])
    out = R.n_step_returns(r, nv, term, trunc, 0.5, 3)
    assert out[0] == pytest.approx(1 + 0.5 * 2), "episode kết thúc ở bước 1: không cộng reward bước 2, không bootstrap"
    trunc2 = np.array([False, True, False, False])
    out2 = R.n_step_returns(r, nv, np.zeros(4, bool), trunc2, 0.5, 3)
    assert out2[0] == pytest.approx(1 + 0.5 * 2 + 0.25 * 20), "bị cắt ở bước 1: bootstrap từ next_values[1]"


def test_n_step_large_n_is_monte_carlo(R):
    rng = np.random.default_rng(5)
    r = rng.normal(size=6)
    term = np.array([False] * 5 + [True])
    out = R.n_step_returns(r, rng.normal(size=6), term, np.zeros(6, bool), 0.9, 100)
    np.testing.assert_allclose(out, R.reward_to_go(r, 0.9), atol=1e-12)


def test_n_step_vectorized(R):
    r, _, nv, _ = buffer(7, 6, n_envs=2)
    term = np.zeros((7, 2), bool)
    term[3, 1] = True
    trunc = np.zeros((7, 2), bool)
    trunc[1, 0] = True
    out = R.n_step_returns(r, nv, term, trunc, 0.9, 3)
    assert out.shape == (7, 2)
    for i in range(2):
        np.testing.assert_allclose(out[:, i], R.n_step_returns(r[:, i], nv[:, i], term[:, i], trunc[:, i], 0.9, 3))


def test_normalize_advantages(R):
    adv = np.array([1.0, 2.0, 3.0, 10.0])
    out = R.normalize_advantages(adv)
    assert out.mean() == pytest.approx(0.0, abs=1e-12)
    assert out.std() == pytest.approx(1.0, abs=1e-6)
    np.testing.assert_array_equal(np.argsort(out), np.argsort(adv))
    const = R.normalize_advantages(np.full(5, 3.0))
    assert np.all(np.isfinite(const)) and np.allclose(const, 0.0), "advantage hằng: không chia cho 0"
    np.testing.assert_allclose(R.normalize_advantages(np.full((2, 2), 3.0)), 0.0)
