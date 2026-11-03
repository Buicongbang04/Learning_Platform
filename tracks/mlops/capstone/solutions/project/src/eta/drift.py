import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

MIN_SHARE = 1e-4


def _shares(values: np.ndarray, interior: np.ndarray, n_bins: int) -> np.ndarray:
    counts = np.bincount(np.searchsorted(interior, values, side="right"), minlength=n_bins)
    return np.maximum(counts / len(values), MIN_SHARE)


def psi(ref: pd.Series, cur: pd.Series, bins: int = 10) -> float:
    reference = pd.Series(ref, dtype="float64").dropna().to_numpy()
    current = pd.Series(cur, dtype="float64").dropna().to_numpy()
    if len(reference) == 0 or len(current) == 0:
        raise ValueError("psi cần hai mẫu không rỗng")
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    interior = edges[1:-1]
    n_bins = len(interior) + 1
    r = _shares(reference, interior, n_bins)
    c = _shares(current, interior, n_bins)
    return float(np.sum((c - r) * np.log(c / r)))


def ks_stat(ref: pd.Series, cur: pd.Series) -> float:
    reference = pd.Series(ref, dtype="float64").dropna().to_numpy()
    current = pd.Series(cur, dtype="float64").dropna().to_numpy()
    return float(ks_2samp(reference, current).statistic)


def drift_table(ref: pd.DataFrame, cur: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = [{"feature": c, "psi": psi(ref[c], cur[c]), "ks_stat": ks_stat(ref[c], cur[c])} for c in columns]
    return pd.DataFrame(rows, columns=["feature", "psi", "ks_stat"])
