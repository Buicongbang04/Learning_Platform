"""Q-learning và SARSA dạng bảng, ε-greedy, lịch ε tuyến tính.

Env theo API Gymnasium: reset(seed=...) -> (obs, info), step(a) -> (obs, reward, terminated, truncated, info),
obs là số nguyên (trạng thái rời rạc), env.action_space.n là số action.
Chỉ dùng numpy trong tệp này (env do bên ngoài truyền vào).
"""

from __future__ import annotations

import numpy as np


def linear_epsilon(step: int, start: float, end: float, decay_steps: int) -> float:
    if decay_steps <= 0:
        return float(end)
    frac = min(max(step, 0) / decay_steps, 1.0)
    return float(start + frac * (end - start))


def epsilon_greedy(q_row: np.ndarray, epsilon: float, rng: np.random.Generator) -> int:
    if rng.random() < epsilon:
        return int(rng.integers(len(q_row)))
    best = np.flatnonzero(q_row == q_row.max())
    return int(rng.choice(best))


def q_learning_update(Q: np.ndarray, s: int, a: int, r: float, s_next: int, terminated: bool,
                      alpha: float, gamma: float) -> float:
    target = r + (0.0 if terminated else gamma * Q[s_next].max())
    td = target - Q[s, a]
    Q[s, a] += alpha * td
    return float(td)


def sarsa_update(Q: np.ndarray, s: int, a: int, r: float, s_next: int, a_next: int, terminated: bool,
                 alpha: float, gamma: float) -> float:
    target = r + (0.0 if terminated else gamma * Q[s_next, a_next])
    td = target - Q[s, a]
    Q[s, a] += alpha * td
    return float(td)


def train_td(env, method: str, n_episodes: int, alpha: float, gamma: float, eps_start: float,
             eps_end: float, eps_decay_episodes: int, seed: int) -> tuple[np.ndarray, list[float]]:
    rng = np.random.default_rng(seed)
    Q = np.zeros((env.observation_space.n, env.action_space.n))
    returns = []
    for ep in range(n_episodes):
        eps = linear_epsilon(ep, eps_start, eps_end, eps_decay_episodes)
        s, _ = env.reset(seed=seed + ep)
        a = epsilon_greedy(Q[s], eps, rng)
        total, done = 0.0, False
        while not done:
            s2, r, terminated, truncated, _ = env.step(a)
            total += r
            if method == "q_learning":
                q_learning_update(Q, s, a, r, s2, terminated, alpha, gamma)
                a2 = epsilon_greedy(Q[s2], eps, rng)
            elif method == "sarsa":
                a2 = epsilon_greedy(Q[s2], eps, rng)
                sarsa_update(Q, s, a, r, s2, a2, terminated, alpha, gamma)
            else:
                raise ValueError(f"method phải là 'q_learning' hoặc 'sarsa', không phải {method!r}")
            s, a = s2, a2
            done = terminated or truncated
        returns.append(total)
    return Q, returns
