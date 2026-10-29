"""Instrumental variables: Wald estimator, first stage và 2SLS tự viết bằng numpy."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _design(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    return np.column_stack([np.ones(len(df)), df[cols].to_numpy(dtype=float)])


def wald_estimator(df: pd.DataFrame, outcome: str, endog: str, instrument: str) -> float:
    """(E[y | z=1] − E[y | z=0]) / (E[d | z=1] − E[d | z=0])."""
    m = df.groupby(instrument)[[outcome, endog]].mean()
    return float((m.loc[1, outcome] - m.loc[0, outcome]) / (m.loc[1, endog] - m.loc[0, endog]))


def first_stage(df: pd.DataFrame, endog: str, instrument: str, exog: list[str]) -> tuple[float, float]:
    """Hệ số của instrument trong endog ~ 1 + instrument + exog, và F = t² (SE homoskedastic)."""
    Z = _design(df, [instrument, *exog])
    d = df[endog].to_numpy(dtype=float)
    ZtZ_inv = np.linalg.inv(Z.T @ Z)
    gamma = ZtZ_inv @ Z.T @ d
    resid = d - Z @ gamma
    sigma2 = resid @ resid / (len(d) - Z.shape[1])
    t = gamma[1] / np.sqrt(sigma2 * ZtZ_inv[1, 1])
    return float(gamma[1]), float(t**2)


def two_sls(df: pd.DataFrame, outcome: str, endog: str, instrument: str, exog: list[str]) -> tuple[float, float]:
    """2SLS: (hệ số của endog, SE thông thường với phần dư tính bằng X thật)."""
    X = _design(df, [endog, *exog])
    Z = _design(df, [instrument, *exog])
    y = df[outcome].to_numpy(dtype=float)
    X_hat = Z @ np.linalg.solve(Z.T @ Z, Z.T @ X)
    beta = np.linalg.solve(X_hat.T @ X, X_hat.T @ y)
    u = y - X @ beta
    sigma2 = u @ u / (len(y) - X.shape[1])
    cov = sigma2 * np.linalg.inv(X_hat.T @ X_hat)
    return float(beta[1]), float(np.sqrt(cov[1, 1]))
