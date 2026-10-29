"""Fixed effects bằng within transformation và Hausman test, tự viết bằng numpy/pandas."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2


def within_estimator(df: pd.DataFrame, entity: str, y: str, xs: list[str]) -> dict:
    """Fixed effects (entity) bằng within transformation; panel có thể không cân bằng.

    Trừ trung bình theo entity cho y và từng x, rồi OLS không hằng số trên dữ liệu đã demean.
    SE cổ điển với bậc tự do đúng: n - N - k (N = số entity, k = len(xs)).
    Raise ValueError nếu một x không thay đổi trong bất kỳ entity nào (không ước lượng được).

    Trả dict: params (Series index xs), se (Series index xs), df_resid (int).
    """
    # TODO: demean theo entity (groupby().transform("mean"))
    # TODO: kiểm biến không đổi theo thời gian
    # TODO: OLS trên dữ liệu đã demean, sigma2 = SSR / (n - N - k), se
    raise NotImplementedError


def hausman(b_fe: pd.Series, b_re: pd.Series, cov_fe: pd.DataFrame, cov_re: pd.DataFrame) -> tuple[float, float]:
    """Hausman test FE vs RE trên các hệ số chung của b_fe và b_re (bỏ hằng số nếu có).

    H = d' (V_fe - V_re)^-1 d, d = b_fe - b_re; p-value theo chi2(số hệ số chung).
    Trả (H, p_value).
    """
    # TODO
    raise NotImplementedError
