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
    ci = res.conf_int(alpha=alpha)
    return pd.DataFrame({
        "odds_ratio": np.exp(res.params),
        "ci_low": np.exp(ci.iloc[:, 0]),
        "ci_high": np.exp(ci.iloc[:, 1]),
    })


def discrete_ame(res, df: pd.DataFrame, var: str) -> float:
    """Average marginal effect rời rạc của biến 0/1 `var`: mean P(var=1) - mean P(var=0) trên mọi dòng df."""
    p1 = np.asarray(res.predict(df.assign(**{var: 1})))
    p0 = np.asarray(res.predict(df.assign(**{var: 0})))
    return float((p1 - p0).mean())


def pearson_dispersion(res) -> float:
    """Pearson chi2 / bậc tự do residual của một GLM Poisson: sum((y - mu)^2 / mu) / df_resid."""
    y = np.asarray(res.model.endog)
    mu = np.asarray(res.fittedvalues)
    return float(((y - mu) ** 2 / mu).sum() / res.df_resid)


def fit_count_model(formula: str, df: pd.DataFrame, threshold: float = 1.5):
    """Fit Poisson GLM; nếu pearson_dispersion > threshold thì fit Negative Binomial (smf.negativebinomial).

    Trả (kết quả fit, "poisson" hoặc "negbin").
    """
    pois = smf.glm(formula, df, family=sm.families.Poisson()).fit()
    if pearson_dispersion(pois) <= threshold:
        return pois, "poisson"
    return smf.negativebinomial(formula, df).fit(disp=0), "negbin"
