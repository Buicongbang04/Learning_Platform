import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

PSI_THRESHOLD = 0.1
KS_ALPHA = 0.05
NUMERIC_MIN_UNIQUE = 21
ZERO_FLOOR = 0.0001


def _fill_zero_shares(shares):
    shares = shares.astype(float).copy()
    nonzero = shares[shares != 0]
    fill = nonzero.min() / 10**6 if nonzero.min() <= ZERO_FLOOR else ZERO_FLOOR
    shares[shares == 0] = fill
    return shares


def psi(reference, current):
    reference = pd.Series(reference).dropna()
    current = pd.Series(current).dropna()
    if pd.api.types.is_numeric_dtype(reference) and reference.nunique() >= NUMERIC_MIN_UNIQUE:
        edges = np.histogram_bin_edges(np.concatenate([reference.to_numpy(), current.to_numpy()]), bins="sturges")
        ref_counts = np.histogram(reference, edges)[0]
        cur_counts = np.histogram(current, edges)[0]
    else:
        keys = sorted(set(reference.unique()) | set(current.unique()), key=str)
        ref_counts = np.array([(reference == k).sum() for k in keys])
        cur_counts = np.array([(current == k).sum() for k in keys])
    ref_share = _fill_zero_shares(ref_counts / len(reference))
    cur_share = _fill_zero_shares(cur_counts / len(current))
    return float(np.sum((ref_share - cur_share) * np.log(ref_share / cur_share)))


def ks_pvalue(reference, current):
    reference = pd.Series(reference).dropna().to_numpy(dtype=float)
    current = pd.Series(current).dropna().to_numpy(dtype=float)
    return float(ks_2samp(reference, current)[1])


def drift_flags(reference, current):
    score = psi(reference, current)
    p_value = ks_pvalue(reference, current)
    return {
        "psi": score,
        "ks_p": p_value,
        "psi_drift": score >= PSI_THRESHOLD,
        "ks_drift": p_value < KS_ALPHA,
    }
