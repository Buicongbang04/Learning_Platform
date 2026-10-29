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
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    latest = (reviews.sort_values("review_answer_timestamp")
                     .drop_duplicates("order_id", keep="last")[["order_id", "review_score"]])
    first_item = (items.loc[items.order_item_id == 1, ["order_id", "product_id"]]
                       .merge(products[["product_id", "product_category_name"]], on="product_id")
                       .merge(translation, on="product_category_name"))
    df = (delivered[["order_id"]]
          .merge(latest, on="order_id")
          .merge(first_item[["order_id", "product_category_name_english"]], on="order_id"))
    out = (df.assign(bad=df.review_score <= 2)
             .groupby("product_category_name_english")
             .agg(n=("bad", "size"), bad=("bad", "sum")))
    out.index.name = "category"
    out["bad"] = out["bad"].astype(int)
    return out.sort_values("n", ascending=False)


def beta_posterior(a: float, b: float, k: int, n: int) -> tuple[float, float]:
    """Prior Beta(a, b), quan sát k thành công trên n lần → tham số posterior."""
    return a + k, b + n - k


def credible_interval(a: float, b: float, level: float = 0.95) -> tuple[float, float]:
    """Khoảng credible hai phía đều đuôi (equal-tailed) của Beta(a, b)."""
    tail = (1 - level) / 2
    return float(beta.ppf(tail, a, b)), float(beta.ppf(1 - tail, a, b))


def fit_beta_prior(k: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """Empirical Bayes: ước lượng prior Beta(a, b) từ k, n của nhiều nhóm (method of moments).

    m    = sum(k) / sum(n)
    s2   = sum(n_i (p_i - m)^2) / sum(n)              với p_i = k_i / n_i
    tau2 = s2 - m (1 - m) G / sum(n)                   G là số nhóm (trừ phần nhiễu Binomial)
    Nếu tau2 <= 0: raise ValueError (dữ liệu không cho thấy các nhóm khác nhau thật).
    a + b = m (1 - m) / tau2 - 1;  a = m (a + b);  b = (1 - m)(a + b)
    """
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    m = k.sum() / n.sum()
    s2 = (n * (k / n - m) ** 2).sum() / n.sum()
    tau2 = s2 - m * (1 - m) * len(n) / n.sum()
    if tau2 <= 0:
        raise ValueError("Phương sai giữa các nhóm không lớn hơn nhiễu Binomial: không ước lượng được prior")
    total = m * (1 - m) / tau2 - 1
    return float(m * total), float((1 - m) * total)


def prob_greater(a1: float, b1: float, a2: float, b2: float, n_draws: int = 200_000,
                 seed: int = 0) -> float:
    """P(p1 > p2) với p1 ~ Beta(a1, b1), p2 ~ Beta(a2, b2) độc lập, ước lượng bằng Monte Carlo."""
    rng = np.random.default_rng(seed)
    return float(np.mean(rng.beta(a1, b1, n_draws) > rng.beta(a2, b2, n_draws)))


def shrinkage_table(counts: pd.DataFrame, a: float, b: float, level: float = 0.95) -> pd.DataFrame:
    """Thêm vào counts (cột n, bad) các cột raw_rate, post_mean, ci_lo, ci_hi; sắp theo post_mean giảm dần."""
    out = counts.copy()
    post_a = a + out["bad"]
    post_b = b + out["n"] - out["bad"]
    tail = (1 - level) / 2
    out["raw_rate"] = out["bad"] / out["n"]
    out["post_mean"] = post_a / (post_a + post_b)
    out["ci_lo"] = beta.ppf(tail, post_a, post_b)
    out["ci_hi"] = beta.ppf(1 - tail, post_a, post_b)
    return out.sort_values("post_mean", ascending=False)
