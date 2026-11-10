"""Return, n-step return, GAE(λ) và chuẩn hoá advantage cho một rollout buffer.

Quy ước buffer (T bước, có thể kèm N env song song: shape (T,) hoặc (T, N)):
    rewards[t]      reward nhận sau action ở bước t
    values[t]       V(s_t) do critic ước lượng
    next_values[t]  V(s_{t+1}) với s_{t+1} là observation THẬT ngay sau bước t
                    (khi episode bị cắt vì time limit, đó là final observation, không phải obs sau reset)
    terminated[t]   episode kết thúc thật ở bước t (rơi hố, hạ cánh, đổ cột): không bootstrap
    truncated[t]    episode bị cắt ở bước t (time limit): vẫn bootstrap từ next_values[t]
Episode kết thúc (terminated hoặc truncated) thì đệ quy không được nối sang episode sau.
Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np


def reward_to_go(rewards: np.ndarray, gamma: float) -> np.ndarray:
    rewards = np.asarray(rewards, dtype=np.float64)
    out = np.zeros_like(rewards)
    running = 0.0
    for t in reversed(range(len(rewards))):
        running = rewards[t] + gamma * running
        out[t] = running
    return out


def n_step_returns(rewards: np.ndarray, next_values: np.ndarray, terminated: np.ndarray,
                   truncated: np.ndarray, gamma: float, n: int) -> np.ndarray:
    rewards = np.asarray(rewards, dtype=np.float64)
    next_values = np.asarray(next_values, dtype=np.float64)
    terminated = np.asarray(terminated, dtype=bool)
    truncated = np.asarray(truncated, dtype=bool)
    T = len(rewards)
    out = np.zeros_like(rewards)
    for t in range(T):
        G = np.zeros_like(rewards[t])
        discount = np.ones_like(rewards[t])
        alive = np.ones_like(rewards[t], dtype=bool)
        for k in range(n):
            i = t + k
            if i >= T:
                break
            G = G + alive * discount * rewards[i]
            discount = discount * gamma
            stop_here = alive & (terminated[i] | truncated[i] | (k == n - 1) | (i == T - 1))
            boot = stop_here & ~terminated[i]
            G = G + boot * discount * next_values[i]
            alive = alive & ~stop_here
        out[t] = G
    return out


def gae(rewards: np.ndarray, values: np.ndarray, next_values: np.ndarray, terminated: np.ndarray,
        truncated: np.ndarray, gamma: float, lam: float) -> tuple[np.ndarray, np.ndarray]:
    rewards = np.asarray(rewards, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    next_values = np.asarray(next_values, dtype=np.float64)
    not_term = 1.0 - np.asarray(terminated, dtype=np.float64)
    not_done = not_term * (1.0 - np.asarray(truncated, dtype=np.float64))
    adv = np.zeros_like(rewards)
    running = np.zeros_like(rewards[0])
    for t in reversed(range(len(rewards))):
        delta = rewards[t] + gamma * not_term[t] * next_values[t] - values[t]
        running = delta + gamma * lam * not_done[t] * running
        adv[t] = running
    return adv, adv + values


def normalize_advantages(adv: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    adv = np.asarray(adv, dtype=np.float64)
    return (adv - adv.mean()) / (adv.std() + eps)
