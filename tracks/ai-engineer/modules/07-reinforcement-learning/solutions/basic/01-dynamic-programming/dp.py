"""Dynamic programming trên MDP hữu hạn: policy evaluation, value iteration, policy iteration.

MDP ở dạng của Gymnasium toy_text (`env.unwrapped.P`):
    P[s][a] = [(prob, next_state, reward, terminated), ...]
Chuyển với terminated=True kết thúc episode: không cộng giá trị của trạng thái sau.
policy là mảng (nS, nA), mỗi dòng là phân phối xác suất trên action.
Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np

MDP = list[list[list[tuple[float, int, float, bool]]]] | dict


def _sizes(P: MDP) -> tuple[int, int]:
    return len(P), len(P[0])


def q_from_v(P: MDP, V: np.ndarray, gamma: float) -> np.ndarray:
    nS, nA = _sizes(P)
    Q = np.zeros((nS, nA))
    for s in range(nS):
        for a in range(nA):
            Q[s, a] = sum(p * (r + gamma * (0.0 if done else V[s2])) for p, s2, r, done in P[s][a])
    return Q


def policy_evaluation(P: MDP, policy: np.ndarray, gamma: float, tol: float = 1e-10,
                      max_iter: int = 100_000) -> np.ndarray:
    nS, _ = _sizes(P)
    V = np.zeros(nS)
    for _ in range(max_iter):
        V_new = (policy * q_from_v(P, V, gamma)).sum(axis=1)
        delta = np.max(np.abs(V_new - V))
        V = V_new
        if delta < tol:
            break
    return V


def greedy_policy(Q: np.ndarray) -> np.ndarray:
    policy = np.zeros_like(Q, dtype=float)
    policy[np.arange(len(Q)), Q.argmax(axis=1)] = 1.0
    return policy


def value_iteration(P: MDP, gamma: float, tol: float = 1e-10,
                    max_iter: int = 100_000) -> tuple[np.ndarray, np.ndarray, int]:
    nS, _ = _sizes(P)
    V = np.zeros(nS)
    for it in range(1, max_iter + 1):
        V_new = q_from_v(P, V, gamma).max(axis=1)
        delta = np.max(np.abs(V_new - V))
        V = V_new
        if delta < tol:
            break
    return V, greedy_policy(q_from_v(P, V, gamma)), it


def policy_iteration(P: MDP, gamma: float, tol: float = 1e-10,
                     max_iter: int = 1_000) -> tuple[np.ndarray, np.ndarray, int]:
    nS, nA = _sizes(P)
    policy = np.full((nS, nA), 1.0 / nA)
    for it in range(1, max_iter + 1):
        V = policy_evaluation(P, policy, gamma, tol)
        new_policy = greedy_policy(q_from_v(P, V, gamma))
        if np.array_equal(new_policy, policy):
            break
        policy = new_policy
    return V, policy, it
