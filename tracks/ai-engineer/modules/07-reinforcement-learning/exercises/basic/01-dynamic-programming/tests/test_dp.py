import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def dp():
    return ex.module("dp.py")


def chain_mdp() -> list:
    """3 trạng thái nối tiếp, action 0 = đứng yên (reward 0), action 1 = tiến (reward 1, tới trạng thái 2 thì kết thúc).

    Trạng thái 2 là trạng thái kết thúc: tự quay về chính nó với reward 5 và terminated=True. Code nào cộng giá trị
    của trạng thái sau một chuyển terminated sẽ "thấy" reward 5 mãi mãi.
    """
    return [
        [[(1.0, 0, 0.0, False)], [(1.0, 1, 1.0, False)]],
        [[(1.0, 1, 0.0, False)], [(1.0, 2, 1.0, True)]],
        [[(1.0, 2, 5.0, True)], [(1.0, 2, 5.0, True)]],
    ]


def two_state_mdp() -> list:
    """MDP ngẫu nhiên nhỏ, không có trạng thái kết thúc: giá trị có nghiệm đóng V = (I - γP_π)^{-1} r_π."""
    return [
        [[(0.7, 0, 1.0, False), (0.3, 1, 0.0, False)], [(0.2, 0, 2.0, False), (0.8, 1, -1.0, False)]],
        [[(0.5, 0, 0.5, False), (0.5, 1, 3.0, False)], [(1.0, 0, -2.0, False)]],
    ]


def exact_v(P: list, policy: np.ndarray, gamma: float) -> np.ndarray:
    nS, nA = len(P), len(P[0])
    Pm, r = np.zeros((nS, nS)), np.zeros(nS)
    for s in range(nS):
        for a in range(nA):
            for p, s2, rew, done in P[s][a]:
                r[s] += policy[s, a] * p * rew
                if not done:
                    Pm[s, s2] += policy[s, a] * p
    return np.linalg.solve(np.eye(nS) - gamma * Pm, r)


def test_q_from_v_bellman_backup(dp):
    P = two_state_mdp()
    V = np.array([10.0, -4.0])
    Q = dp.q_from_v(P, V, 0.9)
    assert Q.shape == (2, 2)
    expected = np.array([
        [0.7 * (1 + 0.9 * 10) + 0.3 * (0 + 0.9 * -4), 0.2 * (2 + 0.9 * 10) + 0.8 * (-1 + 0.9 * -4)],
        [0.5 * (0.5 + 0.9 * 10) + 0.5 * (3 + 0.9 * -4), -2 + 0.9 * 10],
    ])
    np.testing.assert_allclose(Q, expected, atol=1e-12)


def test_q_from_v_terminal_no_bootstrap(dp):
    Q = dp.q_from_v(chain_mdp(), np.array([0.0, 0.0, 100.0]), 0.9)
    assert Q[1, 1] == pytest.approx(1.0), "chuyển terminated=True: không cộng γ·V(s') dù V(s') lớn"
    assert Q[2, 0] == pytest.approx(5.0)


def test_policy_evaluation_matches_linear_solve(dp):
    P = two_state_mdp()
    policy = np.array([[0.4, 0.6], [0.9, 0.1]])
    for gamma in [0.5, 0.9, 0.99]:
        V = dp.policy_evaluation(P, policy, gamma)
        np.testing.assert_allclose(V, exact_v(P, policy, gamma), atol=1e-6)


def test_policy_evaluation_terminal(dp):
    P = chain_mdp()
    forward = np.array([[0.0, 1.0]] * 3)
    V = dp.policy_evaluation(P, forward, 0.9)
    np.testing.assert_allclose(V, [1 + 0.9 * 1, 1.0, 5.0], atol=1e-8)


def test_greedy_policy_one_hot_ties_lowest(dp):
    Q = np.array([[1.0, 3.0, 2.0], [0.0, 0.0, 0.0], [-1.0, -5.0, -1.0]])
    pi = dp.greedy_policy(Q)
    np.testing.assert_array_equal(pi, [[0, 1, 0], [1, 0, 0], [1, 0, 0]])


def test_value_iteration_small(dp):
    P = two_state_mdp()
    V, pi, n_iter = dp.value_iteration(P, 0.9)
    assert pi.shape == (2, 2) and np.allclose(pi.sum(axis=1), 1)
    best = max((exact_v(P, np.eye(2)[[a0, a1]], 0.9) for a0 in range(2) for a1 in range(2)), key=lambda v: v.sum())
    np.testing.assert_allclose(V, best, atol=1e-6)
    np.testing.assert_allclose(dp.policy_evaluation(P, pi, 0.9), V, atol=1e-6)
    assert 50 < n_iter < 1000, "n_iter là số lần quét cho tới khi thay đổi lớn nhất nhỏ hơn tol"


def test_policy_iteration_small(dp):
    P = two_state_mdp()
    V_vi, pi_vi, _ = dp.value_iteration(P, 0.9)
    V, pi, n_iter = dp.policy_iteration(P, 0.9)
    np.testing.assert_allclose(V, V_vi, atol=1e-6)
    np.testing.assert_array_equal(pi, pi_vi)
    assert 1 <= n_iter <= 5


@pytest.fixture(scope="module")
def frozen_lake():
    gym = pytest.importorskip("gymnasium")
    return gym.make("FrozenLake-v1").unwrapped.P


def test_frozenlake_value_iteration(dp, frozen_lake):
    V, pi, n_iter = dp.value_iteration(frozen_lake, 0.99)
    assert V[0] == pytest.approx(0.5420, abs=5e-4)
    assert V[5] == 0.0 and V[15] == 0.0, "hố (5) và đích (15) là trạng thái kết thúc: giá trị 0"
    np.testing.assert_array_equal(pi.argmax(axis=1)[[0, 3, 14]], [0, 3, 1])
    assert 400 < n_iter < 800


def test_frozenlake_policy_iteration_agrees(dp, frozen_lake):
    V_vi, _, _ = dp.value_iteration(frozen_lake, 0.99)
    V, pi, n_iter = dp.policy_iteration(frozen_lake, 0.99)
    np.testing.assert_allclose(V, V_vi, atol=1e-6)
    assert 2 <= n_iter <= 4, "từ policy đều, FrozenLake 4x4 ổn định sau 3 lần evaluate"
    random_v = dp.policy_evaluation(frozen_lake, np.full((16, 4), 0.25), 0.99)
    assert random_v[0] == pytest.approx(0.0124, abs=5e-4)
