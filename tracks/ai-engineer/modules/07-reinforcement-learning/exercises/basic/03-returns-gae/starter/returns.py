"""Return, n-step return, GAE(λ) và chuẩn hoá advantage cho một rollout buffer.

Quy ước buffer (T bước, có thể kèm N env song song: shape (T,) hoặc (T, N)):
    rewards[t]      reward nhận sau action ở bước t
    values[t]       V(s_t) do critic ước lượng
    next_values[t]  V(s_{t+1}) với s_{t+1} là observation THẬT ngay sau bước t
                    (khi episode bị cắt vì time limit, đó là final observation, không phải obs sau reset)
    terminated[t]   episode kết thúc thật ở bước t (rơi hố, hạ cánh, đổ cột): không bootstrap
    truncated[t]    episode bị cắt ở bước t (time limit): vẫn bootstrap từ next_values[t]
Episode kết thúc (terminated hoặc truncated) thì đệ quy không được nối sang episode sau.
Mọi hàm nhận mảng (T,) hoặc (T, N) và trả cùng shape, kiểu float64. Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np


def reward_to_go(rewards: np.ndarray, gamma: float) -> np.ndarray:
    """G_t = Σ_{k>=0} γ^k r_{t+k} cho MỘT episode hoàn chỉnh (rewards shape (T,))."""
    # TODO
    raise NotImplementedError


def n_step_returns(rewards: np.ndarray, next_values: np.ndarray, terminated: np.ndarray,
                   truncated: np.ndarray, gamma: float, n: int) -> np.ndarray:
    """G_t^(n): cộng tối đa n reward có chiết khấu bắt đầu từ bước t rồi bootstrap γ^k · next_values của bước dừng.

    Dừng sớm hơn n bước khi episode kết thúc (terminated: không bootstrap; truncated: bootstrap) hoặc khi hết
    buffer (bootstrap từ next_values của bước cuối).
    """
    # TODO
    raise NotImplementedError


def gae(rewards: np.ndarray, values: np.ndarray, next_values: np.ndarray, terminated: np.ndarray,
        truncated: np.ndarray, gamma: float, lam: float) -> tuple[np.ndarray, np.ndarray]:
    """Generalized Advantage Estimation. Trả (advantages, returns) với returns = advantages + values."""
    # TODO
    raise NotImplementedError


def normalize_advantages(adv: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Trừ mean, chia (std + eps) trên toàn bộ mảng."""
    # TODO
    raise NotImplementedError
