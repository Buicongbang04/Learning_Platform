import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

from testkit import ROOT, Exercise

ex = Exercise(__file__)

FAST = dict(objective="binary", metric="binary_logloss", learning_rate=0.1, num_leaves=15,
            min_data_in_leaf=20, num_threads=1, verbose=-1, seed=0)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("lgbm_olist.ipynb")


def make_data(n: int, seed: int, signal: float = 1.0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.normal(size=(n, 6)), columns=[f"x{i}" for i in range(6)])
    logit = signal * (1.5 * X.x0 - X.x1 + 0.8 * X.x2 * X.x3) - 1.5
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return X, y


def splits(seed: int = 0, signal: float = 1.0):
    X_tr, y_tr = make_data(3000, seed, signal)
    X_va, y_va = make_data(1500, seed + 1, signal)
    X_te, y_te = make_data(1500, seed + 2, signal)
    return X_tr, y_tr, X_va, y_va, X_te, y_te


def test_early_stopping_stops_before_max_rounds(nb):
    X_tr, y_tr, X_va, y_va, *_ = splits(0)
    booster = nb.fit_early_stopping(X_tr, y_tr, X_va, y_va, params=FAST, max_rounds=2000, patience=30)
    assert 1 <= booster.best_iteration < 1000


@pytest.mark.parametrize("seed", [1, 2])
def test_best_iteration_minimises_validation_logloss(nb, seed):
    X_tr, y_tr, X_va, y_va, *_ = splits(seed)
    booster = nb.fit_early_stopping(X_tr, y_tr, X_va, y_va, params=FAST, patience=40)
    # train lại không dừng sớm với cùng tham số: logloss validation nhỏ nhất ở đúng best_iteration
    history = {}
    train_set = lgb.Dataset(X_tr, y_tr)
    lgb.train(FAST, train_set, num_boost_round=300, valid_sets=[lgb.Dataset(X_va, y_va, reference=train_set)],
              callbacks=[lgb.record_evaluation(history)])
    losses = history["valid_0"]["binary_logloss"]
    assert booster.best_iteration == int(np.argmin(losses)) + 1


def test_pure_noise_stops_almost_immediately(nb):
    rng = np.random.default_rng(3)
    X_tr, _ = make_data(3000, 3)
    X_va, _ = make_data(1500, 4)
    booster = nb.fit_early_stopping(X_tr, rng.integers(0, 2, 3000), X_va, rng.integers(0, 2, 1500),
                                    params=FAST, patience=30)
    assert booster.best_iteration <= 15


def test_default_params_and_no_mutation(nb):
    X_tr, y_tr, X_va, y_va, *_ = splits(5)
    params = dict(FAST)
    nb.fit_early_stopping(X_tr, y_tr, X_va, y_va, params=params, patience=20)
    assert params == FAST
    before = dict(nb.PARAMS)
    booster = nb.fit_early_stopping(X_tr, y_tr, X_va, y_va, patience=20)
    assert nb.PARAMS == before
    assert booster.best_iteration >= 1


def test_evaluate_uses_best_iteration(nb):
    X_tr, y_tr, X_va, y_va, X_te, y_te = splits(6)
    booster = nb.fit_early_stopping(X_tr, y_tr, X_va, y_va, params=FAST, patience=30)
    out = nb.evaluate(booster, X_te, y_te)
    p = booster.predict(X_te, num_iteration=booster.best_iteration)
    assert set(out) == {"auc", "pr_auc", "logloss"}
    assert out["auc"] == pytest.approx(roc_auc_score(y_te, p))
    assert out["pr_auc"] == pytest.approx(average_precision_score(y_te, p))
    assert out["logloss"] == pytest.approx(log_loss(y_te, p))


def test_lr_sweep_smaller_rate_needs_more_trees(nb):
    X_tr, y_tr, X_va, y_va, X_te, y_te = splits(7)
    table = nb.lr_sweep(X_tr, y_tr, X_va, y_va, X_te, y_te, rates=(0.3, 0.1, 0.03), params=FAST)
    assert list(table.index) == [0.3, 0.1, 0.03]
    assert {"best_iteration", "val_logloss", "test_auc"} <= set(table.columns)
    its = table.best_iteration.to_numpy()
    assert its[0] < its[1] < its[2]
    assert (table.test_auc > 0.75).all()


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    data = nb.build_dataset(raw)
    parts = nb.time_split(data)
    assert len(data) == 95824
    assert [len(parts[k]) for k in ("train", "val", "test")] == [43362, 20468, 31994]
    tr, va, te = parts["train"], parts["val"], parts["test"]
    booster = nb.fit_early_stopping(tr[nb.FEATURES], tr.bad_review, va[nb.FEATURES], va.bad_review)
    val = nb.evaluate(booster, va[nb.FEATURES], va.bad_review)
    test = nb.evaluate(booster, te[nb.FEATURES], te.bad_review)
    assert booster.best_iteration < 1000
    assert 0.67 < test["auc"] < 0.75
    assert val["auc"] > test["auc"] + 0.05      # validation (Q1/2018) khác hẳn test
    assert test["pr_auc"] > 2 * te.bad_review.mean()
