"""Sai phân, ACF và kiểm định stationarity (ADF + KPSS).

Được dùng statsmodels.tsa.stattools.adfuller và kpss cho kiểm định. ACF tự viết bằng numpy.
"""

from __future__ import annotations

import warnings

import numpy as np
from statsmodels.tsa.stattools import adfuller, kpss


def difference(y, lag: int = 1) -> np.ndarray:
    """y[t] - y[t - lag], độ dài len(y) - lag."""
    y = np.asarray(y, dtype=float)
    return y[lag:] - y[:-lag]


def inverse_difference(diff_forecast, history, lag: int = 1) -> np.ndarray:
    """Đưa dự báo trên chuỗi đã sai phân (bậc `lag`) về mức gốc.

    history: các quan sát gốc tới thời điểm T. Mức dự báo bước k là
    diff_forecast[k] + (mức ở k - lag), lấy từ history hoặc từ mức đã dựng.
    """
    levels = list(np.asarray(history, dtype=float)[-lag:])
    for d in np.asarray(diff_forecast, dtype=float):
        levels.append(d + levels[-lag])
    return np.array(levels[lag:])


def acf(y, nlags: int) -> np.ndarray:
    """Autocorrelation r_0..r_nlags, cùng định nghĩa với statsmodels acf (adjusted=False)."""
    z = np.asarray(y, dtype=float)
    z = z - z.mean()
    denom = np.sum(z**2)
    return np.array([np.sum(z[k:] * z[: len(z) - k]) / denom for k in range(nlags + 1)])


def verdict(adf_p: float, kpss_p: float, alpha: float = 0.05) -> str:
    """Kết hợp hai kiểm định có giả thuyết ngược nhau.

    ADF: H0 = có unit root. KPSS: H0 = stationary.
    Trả 'stationary', 'non_stationary', 'trend_stationary' hoặc 'difference_stationary'.
    """
    adf_says_stationary = adf_p < alpha       # bác bỏ unit root
    kpss_says_stationary = kpss_p >= alpha    # không bác bỏ stationarity
    if adf_says_stationary and kpss_says_stationary:
        return "stationary"
    if not adf_says_stationary and not kpss_says_stationary:
        return "non_stationary"
    if kpss_says_stationary:
        return "trend_stationary"
    return "difference_stationary"


def _kpss_p(y) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")   # p bị chặn ở 0.01 / 0.1 theo bảng tra
        return float(kpss(y, regression="c", nlags="auto", result_object=False)[1])


def stationarity_report(y, alpha: float = 0.05) -> dict:
    """{'adf_p', 'kpss_p', 'verdict'}: adfuller(autolag='AIC'), kpss(regression='c', nlags='auto'),
    cả hai với result_object=False (trả tuple, p-value ở vị trí [1])."""
    y = np.asarray(y, dtype=float)
    adf_p = float(adfuller(y, autolag="AIC", result_object=False)[1])
    kpss_p = _kpss_p(y)
    return {"adf_p": adf_p, "kpss_p": kpss_p, "verdict": verdict(adf_p, kpss_p, alpha)}


def n_diffs(y, max_d: int = 2, alpha: float = 0.05) -> int:
    """Số lần sai phân nhỏ nhất (0..max_d) để KPSS không bác bỏ stationarity."""
    y = np.asarray(y, dtype=float)
    for d in range(max_d + 1):
        if _kpss_p(y) >= alpha:
            return d
        y = difference(y)
    return max_d
