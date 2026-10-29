"""Mô hình phân phối thời gian giao hàng và percentile để đặt ngày hẹn giao."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

CANDIDATES = {"expon": stats.expon, "gamma": stats.gamma, "lognorm": stats.lognorm, "weibull_min": stats.weibull_min}


def fit_candidates(x: np.ndarray) -> pd.DataFrame:
    """Fit từng phân phối trong CANDIDATES bằng MLE với loc cố định 0, so sánh bằng AIC.

    Trả DataFrame cột đúng thứ tự: dist, loglik, n_params, aic, q95; sắp theo aic tăng dần.
      loglik   log-likelihood tại tham số MLE
      n_params số tham số được ước lượng (không tính loc đã cố định): expon 1, còn lại 2
      aic      2 * n_params - 2 * loglik
      q95      percentile 95 của phân phối đã fit
    """
    # TODO
    raise NotImplementedError


def quantile_ci(x: np.ndarray, q: float, n_boot: int = 2000, seed: int = 0,
                alpha: float = 0.05) -> tuple[float, float, float]:
    """(estimate, lo, hi): percentile thực nghiệm q của x và CI bootstrap percentile cho nó.

    Dùng np.random.default_rng(seed); chia lô nếu x lớn (96 nghìn đơn × 2000 lần không vừa bộ nhớ).
    """
    # TODO
    raise NotImplementedError
