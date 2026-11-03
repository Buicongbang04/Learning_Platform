import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

PSI_THRESHOLD = 0.1
KS_ALPHA = 0.05
NUMERIC_MIN_UNIQUE = 21
ZERO_FLOOR = 0.0001


def _fill_zero_shares(shares):
    # TODO: thay mọi share bằng 0 theo luật trong README (đã mô tả đủ)
    raise NotImplementedError


def psi(reference, current):
    # TODO: PSI theo cách Evidently tính, đúng các luật trong README
    raise NotImplementedError


def ks_pvalue(reference, current):
    # TODO: p-value của two-sample KS, bỏ NaN
    raise NotImplementedError


def drift_flags(reference, current):
    # TODO: trả dict gồm psi, ks_p, psi_drift, ks_drift
    raise NotImplementedError
