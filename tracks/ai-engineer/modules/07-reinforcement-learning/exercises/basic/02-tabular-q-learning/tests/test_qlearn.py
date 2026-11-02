from types import SimpleNamespace

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def ql():
    return ex.module("qlearn.py")


class EndlessReward:
    """Một trạng thái, một action, reward 1 mỗi bước, không bao giờ terminated; bị cắt (truncated) sau `limit` bước.

    Giá trị thật của trạng thái là 1 / (1 - γ): time limit chỉ là giới hạn của lần chạy, không phải của bài toán.
    """

    def __init__(self, limit: int = 5):
        self.limit = limit
        self.observation_space = SimpleNamespace(n=1)
        self.action_space = SimpleNamespace(n=1)

    def reset(self, seed=None):
        self.t = 0
        return 0, {}

    def step(self, action):
        self.t += 1
        return 0, 1.0, False, self.t >= self.limit, {}


def test_linear_epsilon(ql):
    assert ql.linear_epsilon(0, 1.0, 0.1, 100) == pytest.approx(1.0)
    assert ql.linear_epsilon(50, 1.0, 0.1, 100) == pytest.approx(0.55)
    assert ql.linear_epsilon(100, 1.0, 0.1, 100) == pytest.approx(0.1)
    assert ql.linear_epsilon(10_000, 1.0, 0.1, 100) == pytest.approx(0.1), "sau decay_steps giữ nguyên end"
    assert ql.linear_epsilon(3, 0.5, 0.5, 0) == pytest.approx(0.5)


def test_epsilon_greedy_greedy_and_ties(ql):
    rng = np.random.default_rng(0)
    q = np.array([0.0, 2.0, -1.0, 2.0])
    picks = [ql.epsilon_greedy(q, 0.0, rng) for _ in range(400)]
    assert set(picks) == {1, 3}, "ε = 0: chỉ chọn action có Q lớn nhất, hoà thì chọn ngẫu nhiên giữa chúng"
    assert 120 < picks.count(1) < 280
    assert all(isinstance(p, int) for p in picks[:5])


def test_epsilon_greedy_exploration_rate(ql):
    rng = np.random.default_rng(1)
    q = np.array([5.0, 0.0, 0.0, 0.0])
    picks = np.array([ql.epsilon_greedy(q, 0.4, rng) for _ in range(20_000)])
    # khám phá chọn đều trong CẢ 4 action (kể cả action greedy): P(greedy) = 0.6 + 0.4 / 4 = 0.7
    assert np.mean(picks == 0) == pytest.approx(0.7, abs=0.015)
    assert np.bincount(picks, minlength=4)[1:].min() > 1800


def test_epsilon_greedy_reproducible(ql):
    q = np.array([0.0, 1.0, 1.0, 0.5])
    runs = []
    for _ in range(2):
        rng = np.random.default_rng(7)
        runs.append([ql.epsilon_greedy(q, 0.5, rng) for _ in range(50)])
    assert runs[0] == runs[1], "mọi ngẫu nhiên lấy từ rng truyền vào: cùng seed, cùng chuỗi action"


def test_q_learning_update(ql):
    Q = np.array([[1.0, 2.0], [3.0, -1.0], [0.0, 0.0]])
    td = ql.q_learning_update(Q, 0, 1, 0.5, 1, False, alpha=0.1, gamma=0.9)
    assert td == pytest.approx(0.5 + 0.9 * 3.0 - 2.0)
    assert Q[0, 1] == pytest.approx(2.0 + 0.1 * td)
    assert Q[0, 0] == 1.0 and Q[1, 0] == 3.0, "chỉ sửa đúng ô Q[s, a], tại chỗ"


def test_q_learning_update_terminal(ql):
    Q = np.array([[0.0, 0.0], [10.0, 10.0]])
    td = ql.q_learning_update(Q, 0, 0, 1.0, 1, True, alpha=0.5, gamma=0.9)
    assert td == pytest.approx(1.0), "terminated: target chỉ là r, không cộng γ·max Q[s']"
    assert Q[0, 0] == pytest.approx(0.5)


def test_sarsa_update_uses_next_action(ql):
    Q = np.array([[0.0, 0.0], [4.0, -2.0]])
    td = ql.sarsa_update(Q, 0, 0, 1.0, 1, 1, False, alpha=0.5, gamma=0.5)
    assert td == pytest.approx(1.0 + 0.5 * -2.0), "SARSA dùng Q[s', a'] của action thật sự sẽ làm, không phải max"
    td = ql.sarsa_update(Q, 0, 1, 1.0, 1, 0, True, alpha=0.5, gamma=0.5)
    assert td == pytest.approx(1.0)


def test_truncation_still_bootstraps(ql):
    env = EndlessReward(limit=5)
    Q, returns = ql.train_td(env, "q_learning", n_episodes=400, alpha=0.2, gamma=0.9, eps_start=0.0,
                             eps_end=0.0, eps_decay_episodes=1, seed=0)
    assert returns[:3] == [5.0, 5.0, 5.0]
    assert Q[0, 0] == pytest.approx(10.0, abs=0.05), (
        "time limit (truncated) không phải trạng thái kết thúc: Q phải tiến tới 1/(1-γ) = 10"
    )


@pytest.fixture(scope="module")
def gym():
    return pytest.importorskip("gymnasium")


def greedy_rollout(env, Q, seed=0, limit=200):
    s, _ = env.reset(seed=seed)
    total, steps, done = 0.0, 0, False
    while not done and steps < limit:
        s, r, te, tr, _ = env.step(int(Q[s].argmax()))
        total += r
        steps += 1
        done = te or tr
    return total, steps


def test_frozenlake_deterministic(ql, gym):
    env = gym.make("FrozenLake-v1", is_slippery=False)
    Q, returns = ql.train_td(env, "q_learning", 500, 0.5, 0.95, 1.0, 0.05, 250, seed=0)
    assert Q.shape == (16, 4)
    assert greedy_rollout(env, Q) == (1.0, 6), "hồ không trơn: đường ngắn nhất tới đích là 6 bước"
    assert np.mean(returns[-100:]) > 0.8, "sau khi ε giảm về 0.05, phần lớn episode lúc train phải tới đích"
    Q2, returns2 = ql.train_td(env, "q_learning", 500, 0.5, 0.95, 1.0, 0.05, 250, seed=0)
    np.testing.assert_array_equal(Q, Q2)
    assert returns == returns2


def test_cliffwalking_q_learning_vs_sarsa(ql, gym):
    env = gym.make("CliffWalking-v1")
    Qq, ret_q = ql.train_td(env, "q_learning", 500, 0.2, 1.0, 0.1, 0.1, 1, seed=0)
    Qs, ret_s = ql.train_td(env, "sarsa", 500, 0.2, 1.0, 0.1, 0.1, 1, seed=0)
    assert greedy_rollout(env, Qq) == (-13.0, 13), "Q-learning học đường sát vực (tối ưu khi không khám phá)"
    sarsa_return, _ = greedy_rollout(env, Qs)
    assert -19 <= sarsa_return <= -15, "SARSA học đường vòng xa vực vì tính cả rủi ro của ε-greedy"
    assert np.mean(ret_s[-200:]) > np.mean(ret_q[-200:]) + 10, (
        "khi vẫn khám phá ε = 0.1, return lúc train của SARSA cao hơn Q-learning"
    )
