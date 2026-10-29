import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("validation.ipynb")


def forest():
    return RandomForestClassifier(n_estimators=60, min_samples_leaf=5, random_state=0, n_jobs=1)


def drift_data(seed: int, n: int = 3000):
    """Tỉ lệ nhãn trôi theo thời gian (random walk); model học được 'giai đoạn' từ cột t."""
    rng = np.random.default_rng(seed)
    t = np.sort(rng.uniform(0, 1, n))
    level = np.cumsum(rng.normal(0, 0.35, 200))[(t * 199).astype(int)]
    x = rng.normal(size=n)
    y = (rng.random(n) < 1 / (1 + np.exp(-(level - level.mean() + 0.5 * x)))).astype(int)
    dates = pd.Timestamp("2017-01-01") + pd.to_timedelta(t * 365, unit="D")
    perm = rng.permutation(n)                                  # dữ liệu đến không theo thứ tự
    X = pd.DataFrame({"t": t, "x": x}).iloc[perm].reset_index(drop=True)
    return X, y[perm], pd.Series(dates[perm]), np.arange(n)


def customer_data(seed: int, n_customers: int = 300, rows_each: int = 10):
    """Mỗi khách nhiều dòng; đặc điểm khách không liên quan tới nhãn, nhưng nhãn phụ thuộc khách."""
    rng = np.random.default_rng(seed)
    groups = np.repeat(np.arange(n_customers), rows_each)
    profile = rng.normal(size=(n_customers, 5))[groups]
    propensity = rng.normal(size=n_customers)[groups]
    y = (rng.random(len(groups)) < 1 / (1 + np.exp(-3 * propensity))).astype(int)
    dates = pd.Series(pd.Timestamp("2017-01-01") + pd.to_timedelta(rng.uniform(0, 365, len(groups)), unit="D"))
    return pd.DataFrame(profile, columns=[f"p{i}" for i in range(5)]), y, dates, groups


def test_time_splits_respect_order(nb):
    rng = np.random.default_rng(0)
    dates = pd.Series(pd.Timestamp("2018-01-01") + pd.to_timedelta(rng.permutation(500), unit="h"))
    splits = nb.time_cv_splits(dates, n_splits=4)
    assert len(splits) == 4
    seen_test = []
    for tr, te in splits:
        assert isinstance(tr, np.ndarray) and isinstance(te, np.ndarray)
        assert dates.iloc[tr].max() < dates.iloc[te].min()
        seen_test.extend(te.tolist())
    assert len(seen_test) == len(set(seen_test)) == 400        # 4 fold test × 100 dòng, không trùng
    assert set(splits[-1][0]) | set(splits[-1][1]) == set(range(500))


def test_time_splits_gap(nb):
    rng = np.random.default_rng(1)
    dates = pd.Series(pd.Timestamp("2018-01-01") + pd.to_timedelta(rng.permutation(300), unit="D"))
    for tr, te in nb.time_cv_splits(dates, n_splits=3, gap=7):
        last_train, first_test = dates.iloc[tr].max(), dates.iloc[te].min()
        assert ((dates > last_train) & (dates < first_test)).sum() == 7


def test_cv_auc_matches_manual_and_uses_fresh_models(nb):
    X, y, dates, _ = drift_data(0, n=800)
    splits = list(KFold(4, shuffle=True, random_state=1).split(X))
    calls = []

    def make_model():
        calls.append(1)
        return LogisticRegression()

    out = nb.cv_auc(make_model, X, pd.Series(y), splits)
    manual = [roc_auc_score(y[te], LogisticRegression().fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[te])[:, 1])
              for tr, te in splits]
    assert isinstance(out, np.ndarray)
    assert out == pytest.approx(manual)
    assert len(calls) == 4


def test_compare_schemes_shape(nb):
    X, y, dates, groups = customer_data(0, n_customers=60)
    out = nb.compare_schemes(LogisticRegression, X, y, dates, groups, n_splits=3)
    assert list(out.index) == ["kfold", "group_kfold", "time"]
    assert {"mean", "std"} <= set(out.columns)
    expected = nb.cv_auc(LogisticRegression, X, y, list(KFold(3, shuffle=True, random_state=0).split(X)))
    assert out.loc["kfold", "mean"] == pytest.approx(expected.mean())
    assert out.loc["kfold", "std"] == pytest.approx(expected.std())


def test_kfold_overestimates_under_drift(nb):
    X, y, dates, groups = drift_data(3)
    out = nb.compare_schemes(forest, X, y, dates, groups)
    assert out.loc["kfold", "mean"] - out.loc["time", "mean"] > 0.1


def test_kfold_overestimates_with_repeated_customers(nb):
    X, y, dates, groups = customer_data(3)
    out = nb.compare_schemes(forest, X, y, dates, groups)
    assert out.loc["kfold", "mean"] - out.loc["group_kfold", "mean"] > 0.25
    assert out.loc["group_kfold", "mean"] < 0.6
    assert out.loc["time", "mean"] > 0.75          # chia theo thời gian KHÔNG chữa được rò rỉ theo khách


def test_real_olist_folds(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    orders = pd.read_csv(raw / "olist_orders_dataset.csv",
                         parse_dates=["order_purchase_timestamp", "order_delivered_customer_date"])
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    latest = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    dev = delivered.merge(latest, on="order_id")
    dev = dev[dev.order_purchase_timestamp < "2018-04-01"].sample(frac=1, random_state=0)   # xáo trộn thứ tự
    splits = nb.time_cv_splits(dev.order_purchase_timestamp, n_splits=5)
    first = dev.order_purchase_timestamp.iloc[splits[0][1]]
    last = dev.order_purchase_timestamp.iloc[splits[-1][1]]
    assert len(dev) == 63830
    assert first.min().date() == pd.Timestamp("2017-05-29").date()
    assert last.max().date() == pd.Timestamp("2018-03-31").date()
