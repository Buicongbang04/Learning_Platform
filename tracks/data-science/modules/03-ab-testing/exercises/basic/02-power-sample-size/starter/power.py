"""Power, MDE và cỡ mẫu cho thí nghiệm hai nhóm cân bằng (50/50), kiểm định hai phía.

Được dùng scipy.stats.norm và scipy.optimize. Không dùng statsmodels.stats.power.
"""

from __future__ import annotations

import math

from scipy.optimize import brentq
from scipy.stats import norm


def sample_size_proportions(p_baseline: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Số đơn vị MỖI nhóm để phát hiện p_baseline → p_baseline + mde_abs (mde_abs có thể âm).

    Công thức xấp xỉ normal, không pooled, làm tròn lên.
    """
    # TODO: z = z_{1-alpha/2} + z_{power}; n = z² [p1(1-p1) + p2(1-p2)] / mde²
    raise NotImplementedError


def mde_proportions(p_baseline: float, n_per_group: int, alpha: float = 0.05, power: float = 0.8) -> float:
    """MDE dương nhỏ nhất phát hiện được với n_per_group mỗi nhóm (nghịch đảo hàm trên)."""
    # TODO: giải phương trình theo mde bằng brentq trên khoảng (1e-6, 1 - p_baseline - 1e-9)
    raise NotImplementedError


def sample_size_means(sigma: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Số đơn vị mỗi nhóm cho metric liên tục có độ lệch chuẩn sigma, làm tròn lên."""
    # TODO: n = 2 sigma² (z_{1-alpha/2} + z_{power})² / mde²
    raise NotImplementedError
