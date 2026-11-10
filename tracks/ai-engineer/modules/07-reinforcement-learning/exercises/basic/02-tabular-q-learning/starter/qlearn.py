"""Q-learning và SARSA dạng bảng, ε-greedy, lịch ε tuyến tính.

Env theo API Gymnasium: reset(seed=...) -> (obs, info), step(a) -> (obs, reward, terminated, truncated, info),
obs là số nguyên (trạng thái rời rạc), env.observation_space.n và env.action_space.n là số trạng thái, số action.
Chỉ dùng numpy trong tệp này (env do bên ngoài truyền vào).
"""

from __future__ import annotations

import numpy as np


def linear_epsilon(step: int, start: float, end: float, decay_steps: int) -> float:
    """ε giảm tuyến tính từ `start` (step 0) tới `end` (step = decay_steps), sau đó giữ nguyên `end`.

    decay_steps <= 0 nghĩa là luôn trả `end`.
    """
    # TODO
    raise NotImplementedError


def epsilon_greedy(q_row: np.ndarray, epsilon: float, rng: np.random.Generator) -> int:
    """Với xác suất ε: action ngẫu nhiên đều trong mọi action. Còn lại: action có Q lớn nhất, hoà thì chọn ngẫu nhiên
    đều giữa các action hoà. Mọi ngẫu nhiên lấy từ `rng`. Trả int Python.
    """
    # TODO
    raise NotImplementedError


def q_learning_update(Q: np.ndarray, s: int, a: int, r: float, s_next: int, terminated: bool,
                      alpha: float, gamma: float) -> float:
    """Cập nhật Q[s, a] tại chỗ theo Q-learning. Trả TD error (target - Q[s, a] TRƯỚC khi cập nhật)."""
    # TODO
    raise NotImplementedError


def sarsa_update(Q: np.ndarray, s: int, a: int, r: float, s_next: int, a_next: int, terminated: bool,
                 alpha: float, gamma: float) -> float:
    """Cập nhật Q[s, a] tại chỗ theo SARSA (dùng action a_next agent sẽ làm thật). Trả TD error trước cập nhật."""
    # TODO
    raise NotImplementedError


def train_td(env, method: str, n_episodes: int, alpha: float, gamma: float, eps_start: float,
             eps_end: float, eps_decay_episodes: int, seed: int) -> tuple[np.ndarray, list[float]]:
    """Train Q-learning (method="q_learning") hoặc SARSA (method="sarsa") dạng bảng.

    - Q khởi tạo 0, shape (env.observation_space.n, env.action_space.n); rng = np.random.default_rng(seed).
    - Episode thứ ep (đếm từ 0): ε = linear_epsilon(ep, eps_start, eps_end, eps_decay_episodes),
      env.reset(seed=seed + ep), chọn action bằng epsilon_greedy với rng.
    - Episode kết thúc khi terminated hoặc truncated; chỉ terminated mới cắt bootstrap.
    - Trả (Q, danh sách tổng reward của từng episode).
    """
    # TODO
    raise NotImplementedError
