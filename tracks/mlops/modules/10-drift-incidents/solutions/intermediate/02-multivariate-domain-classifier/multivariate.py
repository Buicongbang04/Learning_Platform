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
    ref = reference.sample(n=min(len(reference), max_rows), random_state=seed)
    cur = current.sample(n=min(len(current), max_rows), random_state=seed)
    x = pd.concat([ref[features], cur[features]]).fillna(-1)
    y = np.r_[np.zeros(len(ref)), np.ones(len(cur))]
    return x, y


def _forest(seed):
    return RandomForestClassifier(n_estimators=100, max_depth=8, random_state=seed, n_jobs=1)


def domain_auc(reference, current, features, seed=0, n_splits=5, max_rows=MAX_ROWS):
    x, y = _domain_data(reference, current, features, seed, max_rows)
    folds = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    proba = cross_val_predict(_forest(seed), x, y, cv=folds, method="predict_proba")[:, 1]
    return float(roc_auc_score(y, proba))


def driver_features(reference, current, features, seed=0, max_rows=MAX_ROWS):
    x, y = _domain_data(reference, current, features, seed, max_rows)
    model = _forest(seed).fit(x, y)
    pairs = zip(features, model.feature_importances_)
    return sorted(((f, float(i)) for f, i in pairs), key=lambda p: -p[1])


def multivariate_verdict(reference, current, features, seed=0):
    psi_max = max_feature_psi(reference, current, features)
    auc = domain_auc(reference, current, features, seed=seed)
    return {"max_psi": psi_max, "auc": auc, "hidden_drift": psi_max < 0.1 and auc >= 0.7}
