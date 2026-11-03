import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

MAX_ROWS = 20_000


def feature_psi(reference, current, bins=10, eps=1e-4):
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    reference = reference[~np.isnan(reference)]
    current = current[~np.isnan(current)]
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    ref_share = np.clip(np.histogram(reference, edges)[0] / len(reference), eps, None)
    cur_share = np.clip(np.histogram(current, edges)[0] / len(current), eps, None)
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def max_feature_psi(reference, current, features):
    return max(feature_psi(reference[f], current[f]) for f in features)


def _domain_data(reference, current, features, seed, max_rows):
    # TODO: lấy mẫu mỗi tập tối đa max_rows dòng (sample random_state=seed), NaN thành -1, nhãn 0 cho reference và 1 cho current
    raise NotImplementedError


def domain_auc(reference, current, features, seed=0, n_splits=5, max_rows=MAX_ROWS):
    # TODO: AUC cross-validated của RandomForest phân biệt reference và current (luật trong README)
    raise NotImplementedError


def driver_features(reference, current, features, seed=0, max_rows=MAX_ROWS):
    # TODO: fit trên toàn bộ dữ liệu miền, trả [(feature, importance)] giảm dần theo importance
    raise NotImplementedError


def multivariate_verdict(reference, current, features, seed=0):
    # TODO: dict max_psi, auc, hidden_drift (xem README)
    raise NotImplementedError
