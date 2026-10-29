"""Beta-Binomial: so sánh tỉ lệ review xấu giữa các category ít đơn mà không bị nhiễu đánh lừa.

Được dùng numpy, pandas, scipy.stats.beta. Đọc README của bài để biết công thức empirical Bayes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import beta


def category_counts(orders: pd.DataFrame, reviews: pd.DataFrame, items: pd.DataFrame,
                    products: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    """Số đơn có review (n) và số review xấu (bad, score <= 2) theo category tiếng Anh.

    - Đơn giao xong: order_status == "delivered" và có order_delivered_customer_date.
    - Mỗi đơn giữ review có review_answer_timestamp mới nhất.
    - Category của đơn là category của item có order_item_id == 1; bỏ đơn không có category
      (thiếu trong products hoặc không có bản dịch).
    Index tên "category"; cột "n", "bad" (int); sắp theo n giảm dần.
    """
    # TODO
    raise NotImplementedError


def beta_posterior(a: float, b: float, k: int, n: int) -> tuple[float, float]:
    """Prior Beta(a, b), quan sát k thành công trên n lần → tham số posterior."""
    # TODO
    raise NotImplementedError


def credible_interval(a: float, b: float, level: float = 0.95) -> tuple[float, float]:
    """Khoảng credible hai phía đều đuôi (equal-tailed) của Beta(a, b)."""
    # TODO
    raise NotImplementedError


def fit_beta_prior(k: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """Empirical Bayes: ước lượng prior Beta(a, b) từ k, n của nhiều nhóm (method of moments).

    m    = sum(k) / sum(n)
    s2   = sum(n_i (p_i - m)^2) / sum(n)              với p_i = k_i / n_i
    tau2 = s2 - m (1 - m) G / sum(n)                   G là số nhóm (trừ phần nhiễu Binomial)
    Nếu tau2 <= 0: raise ValueError (dữ liệu không cho thấy các nhóm khác nhau thật).
    a + b = m (1 - m) / tau2 - 1;  a = m (a + b);  b = (1 - m)(a + b)
    """
    # TODO
    raise NotImplementedError


def prob_greater(a1: float, b1: float, a2: float, b2: float, n_draws: int = 200_000,
                 seed: int = 0) -> float:
    """P(p1 > p2) với p1 ~ Beta(a1, b1), p2 ~ Beta(a2, b2) độc lập, ước lượng bằng Monte Carlo."""
    # TODO
    raise NotImplementedError


def shrinkage_table(counts: pd.DataFrame, a: float, b: float, level: float = 0.95) -> pd.DataFrame:
    """Thêm vào counts (cột n, bad) các cột raw_rate, post_mean, ci_lo, ci_hi; sắp theo post_mean giảm dần."""
    # TODO
    raise NotImplementedError
