"""Sai phân, ACF và kiểm định stationarity (ADF + KPSS).

Được dùng statsmodels.tsa.stattools.adfuller và kpss cho kiểm định. ACF tự viết bằng numpy.
"""

from __future__ import annotations

import warnings

import numpy as np
from statsmodels.tsa.stattools import adfuller, kpss


def difference(y, lag: int = 1) -> np.ndarray:
    """y[t] - y[t - lag], độ dài len(y) - lag."""
    # TODO
    raise NotImplementedError


def inverse_difference(diff_forecast, history, lag: int = 1) -> np.ndarray:
    """Đưa dự báo trên chuỗi đã sai phân (bậc `lag`) về mức gốc.

    history: các quan sát gốc tới thời điểm T. Mức dự báo bước k là
    diff_forecast[k] + (mức ở k - lag), lấy từ history hoặc từ mức đã dựng.
    """
    # TODO
    raise NotImplementedError


def acf(y, nlags: int) -> np.ndarray:
    """Autocorrelation r_0..r_nlags, cùng định nghĩa với statsmodels acf (adjusted=False)."""
    # TODO: trừ trung bình; r_k = sum(z[t] z[t-k]) / sum(z[t]^2)
    raise NotImplementedError


def verdict(adf_p: float, kpss_p: float, alpha: float = 0.05) -> str:
    """Kết hợp hai kiểm định có giả thuyết ngược nhau.

    ADF: H0 = có unit root. KPSS: H0 = stationary.
    Trả 'stationary', 'non_stationary', 'trend_stationary' hoặc 'difference_stationary'.
    """
    # TODO: xem bảng 4 trường hợp trong README
    raise NotImplementedError


def stationarity_report(y, alpha: float = 0.05) -> dict:
    """{'adf_p', 'kpss_p', 'verdict'}: adfuller(autolag='AIC'), kpss(regression='c', nlags='auto'),
    cả hai với result_object=False (trả tuple, p-value ở vị trí [1])."""
    # TODO: kpss cảnh báo InterpolationWarning khi p nằm ngoài bảng tra; có thể tắt bằng warnings
    raise NotImplementedError


def n_diffs(y, max_d: int = 2, alpha: float = 0.05) -> int:
    """Số lần sai phân nhỏ nhất (0..max_d) để KPSS không bác bỏ stationarity."""
    # TODO
    raise NotImplementedError
