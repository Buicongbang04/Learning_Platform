import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

REVIEW_COLUMNS = {"review_id", "review_score", "review_comment_title", "review_comment_message",
                  "review_creation_date", "review_answer_timestamp", "bad_review"}
VALID_AT_DELIVERY = {"delay_days", "delivery_days", "promised_days", "order_estimated_delivery_date",
                     "seller_id", "customer_state", "distance_km"}


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("pipeline.ipynb")


def make_data(seed: int, n: int = 4000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    seller_effect = rng.normal(0, 1, 200)
    seller = rng.integers(0, 200, n)
    x1 = rng.normal(0, 5, n)
    x2 = rng.exponential(100, n)
    state = rng.choice(["SP", "RJ", "MG", "BA"], n)
    logit = -2 + 0.4 * x1 + seller_effect[seller] + np.where(state == "BA", 1.0, 0.0)
    df = pd.DataFrame({
        "x1": x1, "x2": x2, "state": state, "seller": [f"s{i}" for i in seller],
        "bad_review": (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int),
    })
    df.loc[rng.random(n) < 0.05, "x1"] = np.nan
    df.loc[rng.random(n) < 0.05, "state"] = None
    return df


def test_leaky_columns(nb):
    leaky = set(nb.LEAKY_COLUMNS)
    assert REVIEW_COLUMNS <= leaky
    assert not leaky & VALID_AT_DELIVERY


def test_feature_lists_are_clean(nb):
    features = nb.NUMERIC + nb.CATEGORICAL + nb.HIGH_CARDINALITY
    assert len(nb.NUMERIC) >= 3 and nb.CATEGORICAL and nb.HIGH_CARDINALITY
    assert len(features) == len(set(features))
    assert not set(features) & (set(nb.LEAKY_COLUMNS) | REVIEW_COLUMNS)
    assert not {"order_id", "customer_id", "customer_unique_id"} & set(features)


def test_pipeline_learns_and_handles_missing_and_unseen(nb):
    df = make_data(0)
    train, val = df.iloc[:3000].copy(), df.iloc[3000:].copy()
    val.loc[val.index[:20], "state"] = "AM"               # bang chưa từng thấy trong train
    val.loc[val.index[20:40], "seller"] = "seller_moi"     # seller mới
    pipe = nb.build_pipeline(["x1", "x2"], ["state"], ["seller"])
    auc = nb.fit_and_score(pipe, train, val)
    assert isinstance(auc, float)
    assert auc > 0.8
    proba = pipe.predict_proba(val)[:, 1]
    assert np.isfinite(proba).all()


def test_target_column_is_not_a_feature(nb):
    df = make_data(1)
    train, val = df.iloc[:3000].copy(), df.iloc[3000:].copy()
    pipe = nb.build_pipeline(["x1", "x2"], ["state"], ["seller"])
    nb.fit_and_score(pipe, train, val)
    p1 = pipe.predict_proba(val)[:, 1]
    p2 = pipe.predict_proba(val.assign(bad_review=1 - val.bad_review))[:, 1]
    assert np.allclose(p1, p2)


def test_fit_uses_train_only(nb):
    df = make_data(2)
    train, val = df.iloc[:3000].copy(), df.iloc[3000:].copy()
    val["x2"] = val["x2"] * 1000                           # val lệch hẳn: nếu scaler học cả val sẽ khác
    pipe = nb.build_pipeline(["x1", "x2"], ["state"], ["seller"])
    nb.fit_and_score(pipe, train, val)
    fresh = nb.build_pipeline(["x1", "x2"], ["state"], ["seller"])
    fresh.fit(train, train.bad_review)
    probe = make_data(3).iloc[:200]
    assert np.allclose(pipe.predict_proba(probe), fresh.predict_proba(probe))


def test_empty_groups_are_allowed(nb):
    df = make_data(4)
    train, val = df.iloc[:3000], df.iloc[3000:]
    assert nb.fit_and_score(nb.build_pipeline(["x1", "x2"], [], []), train, val) > 0.65


def test_regularisation_parameter_is_used(nb):
    df = make_data(5)
    train, val = df.iloc[:3000], df.iloc[3000:]
    weak = nb.build_pipeline(["x1", "x2"], ["state"], [], C=1e-4)
    strong = nb.build_pipeline(["x1", "x2"], ["state"], [], C=10.0)
    weak.fit(train, train.bad_review)
    strong.fit(train, train.bad_review)
    assert np.abs(weak[-1].coef_).sum() < np.abs(strong[-1].coef_).sum()


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    table = nb.load_olist_table(raw)
    splits = nb.time_split(table)
    assert set(table.columns) >= set(nb.NUMERIC + nb.CATEGORICAL + nb.HIGH_CARDINALITY)
    pipe = nb.build_pipeline(nb.NUMERIC, nb.CATEGORICAL, nb.HIGH_CARDINALITY)
    auc = nb.fit_and_score(pipe, splits["train"], splits["val"])
    assert 0.77 <= auc <= 0.86      # thấp hơn: thiếu feature giao hàng; cao hơn nhiều: nghi leakage
