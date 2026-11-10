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


def q_from_v(P: MDP, V: np.ndarray, gamma: float) -> np.ndarray:
    """Một Bellman backup: Q[s, a] = Σ p · (r + γ·V[s']) trên mọi chuyển của (s, a); bỏ γ·V[s'] khi terminated.

    Trả mảng (nS, nA). nS = len(P), nA = len(P[0]).
    """
    # TODO
    raise NotImplementedError


def policy_evaluation(P: MDP, policy: np.ndarray, gamma: float, tol: float = 1e-10,
                      max_iter: int = 100_000) -> np.ndarray:
    """V^π bằng cách lặp Bellman expectation backup từ V = 0 cho tới khi max |V_mới - V_cũ| < tol.

    policy shape (nS, nA), mỗi dòng có tổng 1. Trả V shape (nS,).
    """
    # TODO
    raise NotImplementedError


def greedy_policy(Q: np.ndarray) -> np.ndarray:
    """Policy tất định dạng one-hot (nS, nA), chọn action có Q lớn nhất; hoà thì chọn chỉ số nhỏ nhất."""
    # TODO
    raise NotImplementedError


def value_iteration(P: MDP, gamma: float, tol: float = 1e-10,
                    max_iter: int = 100_000) -> tuple[np.ndarray, np.ndarray, int]:
    """Lặp Bellman optimality backup từ V = 0 cho tới khi max |V_mới - V_cũ| < tol.

    Trả (V*, policy greedy theo V*, n_iter) với n_iter là số lần quét đã chạy.
    """
    # TODO
    raise NotImplementedError


def policy_iteration(P: MDP, gamma: float, tol: float = 1e-10,
                     max_iter: int = 1_000) -> tuple[np.ndarray, np.ndarray, int]:
    """Bắt đầu từ policy đều, xen kẽ policy_evaluation (với tol) và cải thiện greedy cho tới khi policy không đổi.

    Trả (V, policy, n_iter) với n_iter là số lần gọi policy_evaluation (kể cả lần cuối xác nhận policy đã ổn định).
    """
    # TODO
    raise NotImplementedError
