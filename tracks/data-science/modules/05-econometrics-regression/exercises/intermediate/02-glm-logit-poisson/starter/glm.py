"""Diễn giải GLM: odds ratio, average marginal effect, overdispersion, chọn model đếm.

Các hàm nhận kết quả fit từ statsmodels formula API (smf.logit, smf.glm, smf.negativebinomial).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


def odds_ratios(res, alpha: float = 0.05) -> pd.DataFrame:
    """Odds ratio và CI (1 - alpha) cho mọi hệ số của một logit. Cột: odds_ratio, ci_low, ci_high."""
    # TODO: exp của params và của conf_int(alpha)
    raise NotImplementedError


def discrete_ame(res, df: pd.DataFrame, var: str) -> float:
    """Average marginal effect rời rạc của biến 0/1 `var`: mean P(var=1) - mean P(var=0) trên mọi dòng df."""
    # TODO: res.predict trên hai bản sao của df
    raise NotImplementedError


def pearson_dispersion(res) -> float:
    """Pearson chi2 / bậc tự do residual của một GLM Poisson: sum((y - mu)^2 / mu) / df_resid."""
    # TODO: y = res.model.endog, mu = res.fittedvalues; không dùng res.pearson_chi2
    raise NotImplementedError


def fit_count_model(formula: str, df: pd.DataFrame, threshold: float = 1.5):
    """Fit Poisson GLM; nếu pearson_dispersion > threshold thì fit Negative Binomial (smf.negativebinomial).

    Trả (kết quả fit, "poisson" hoặc "negbin").
    """
    # TODO
    raise NotImplementedError
