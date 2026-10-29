import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

FEATURES = ["lag_h", "lag_h_7", "lag_h_14", "lag_364", "roll_mean_28", "dow_mean_8w",
            "DayOfWeek", "Promo", "SchoolHoliday", "StateHoliday", "month", "day"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("lgbm_lags.ipynb")


def make_stores(n_stores=3, days=500, seed=0, start="2014-01-01"):
    """Doanh thu giả lập: mức riêng từng cửa hàng × mùa vụ tuần × khuyến mãi xen kẽ theo tuần."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=days, freq="D")
    frames = []
    for store in range(1, n_stores + 1):
        dow = dates.day_of_week.to_numpy() + 1
        promo = ((np.arange(days) // 7) % 2 == 0).astype(int) * (dow <= 5)
        open_ = (dow != 7).astype(int)
        level = 4000 + 1500 * store
        sales = level * np.array([1.2, 1.0, 1.0, 1.0, 1.1, 0.9, 0.0])[dow - 1] * (1 + 0.35 * promo)
        sales = np.round(sales * rng.lognormal(0, 0.08, days)) * open_
        frames.append(pd.DataFrame({
            "Store": store, "DayOfWeek": dow, "Date": dates, "Sales": sales,
            "Customers": np.round(sales / 9), "Open": open_, "Promo": promo,
            "StateHoliday": "0", "SchoolHoliday": (dates.month.isin([7, 8])).astype(int).astype(str),
        }))
    return pd.concat(frames, ignore_index=True)


def test_select_stores_keeps_complete_stores(nb):
    df = make_stores(n_stores=4, days=30)
    df = df[~((df.Store == 2) & (df.Date == "2014-01-10"))]          # cửa hàng 2 thiếu một ngày
    df = df.sample(frac=1, random_state=0)                           # xáo thứ tự
    out = nb.select_stores(df, n_stores=2)
    assert sorted(out.Store.unique()) == [1, 3]
    assert list(out.index) == list(range(len(out)))
    assert out.Store.is_monotonic_increasing
    assert (out.groupby("Store").Date.apply(lambda d: d.is_monotonic_increasing)).all()


def test_feature_columns_and_index(nb):
    df = make_stores(days=420)
    X = nb.make_features(df, horizon=42)
    assert list(X.columns) == FEATURES
    assert X.index.equals(df.index)


def test_lag_values_by_hand(nb):
    df = make_stores(n_stores=2, days=420)
    X = nb.make_features(df, horizon=42)
    s2 = df[df.Store == 2].reset_index()
    row = s2.loc[400]                                                # thứ Năm: mọi lag bội số 7 đều rơi vào ngày mở cửa
    sales_open = s2.Sales.where(s2.Open == 1)
    x = X.loc[row["index"]]
    assert x.lag_h == pytest.approx(sales_open[400 - 42])
    assert x.lag_h_7 == pytest.approx(sales_open[400 - 49])
    assert x.lag_h_14 == pytest.approx(sales_open[400 - 56])
    assert x.lag_364 == pytest.approx(sales_open[400 - 364])
    assert x.roll_mean_28 == pytest.approx(sales_open[400 - 42 - 27: 400 - 42 + 1].mean())
    assert x.dow_mean_8w == pytest.approx(sales_open[[400 - 42 - 7 * k for k in range(8)]].mean())
    assert x.month == row.Date.month and x.day == row.Date.day


def test_closed_days_are_not_zero_sales(nb):
    df = make_stores(n_stores=1, days=200)
    X = nb.make_features(df, horizon=42)
    # t là Chủ nhật thì t - 42 cũng là Chủ nhật (đóng cửa): lag phải là NaN, không phải 0
    sundays = df.index[(df.DayOfWeek == 7) & (df.index >= 42)]
    assert len(sundays) > 0 and X.loc[sundays, "lag_h"].isna().all()
    assert X.dow_mean_8w.dropna().min() > 0


def test_no_leakage_from_future_sales(nb):
    df = make_stores(days=450, seed=1)
    X = nb.make_features(df, horizon=42)
    boundary = pd.Timestamp("2015-01-15")
    changed = df.copy()
    later = changed.Date >= boundary
    changed.loc[later, "Sales"] = changed.loc[later, "Sales"] * 10 + 12345
    X2 = nb.make_features(changed, horizon=42)
    safe = df.Date < boundary + pd.Timedelta(days=42)               # ngày t chỉ thấy Sales tới t - 42
    pd.testing.assert_frame_equal(X[safe], X2[safe])
    assert not X[~safe].equals(X2[~safe])                           # và feature có dùng Sales thật


def test_customers_is_not_used(nb):
    df = make_stores(days=420, seed=2)
    changed = df.assign(Customers=df.Customers * 0 + 1)
    pd.testing.assert_frame_equal(nb.make_features(df), nb.make_features(changed))


def test_stores_do_not_leak_into_each_other(nb):
    df = make_stores(n_stores=3, days=420, seed=3)
    changed = df.copy()
    changed.loc[changed.Store == 2, "Sales"] *= 3
    X, X2 = nb.make_features(df), nb.make_features(changed)
    other = df.Store != 2
    pd.testing.assert_frame_equal(X[other], X2[other])


def test_horizon_changes_lags(nb):
    df = make_stores(n_stores=1, days=420)
    X7 = nb.make_features(df, horizon=7)
    s = df.Sales.where(df.Open == 1)
    assert X7.loc[300, "lag_h"] == pytest.approx(s[293])          # index 300 là thứ Ba (mở cửa)
    assert X7.loc[300, "dow_mean_8w"] == pytest.approx(s[[300 - 7 - 7 * k for k in range(8)]].mean())


def test_fit_predict_ignores_test_period_sales(nb):
    df = make_stores(days=500, seed=4)
    cutoff = df.Date.max() - pd.Timedelta(days=41)
    pred = nb.fit_predict(df, cutoff, horizon=42)
    test_rows = df.index[df.Date >= cutoff]
    assert set(pred.index) == set(test_rows)
    hidden = df.copy()
    hidden.loc[hidden.Date >= cutoff, "Sales"] = np.nan          # lúc dự báo thật, ta chưa có doanh thu tương lai
    pred2 = nb.fit_predict(hidden, cutoff, horizon=42)
    pd.testing.assert_series_equal(pred.sort_index(), pred2.sort_index())
    assert (pred[df.loc[pred.index, "Open"] == 0] == 0).all()


def test_seasonal_naive_last_week(nb):
    df = make_stores(n_stores=2, days=100, seed=5)
    cutoff = pd.Timestamp("2014-03-10")                            # thứ Hai
    pred = nb.seasonal_naive_last_week(df, cutoff, horizon=14)
    row = df[(df.Store == 2) & (df.Date == "2014-03-19")].iloc[0]  # thứ Tư tuần sau nữa
    same_dow_last_week = df[(df.Store == 2) & (df.Date == "2014-03-05")].Sales.iloc[0]
    assert pred.loc[row.name] == pytest.approx(same_dow_last_week)
    assert len(pred) == 2 * 14


def test_evaluate(nb):
    df = pd.DataFrame({"Sales": [100.0, 200.0, 0.0, 50.0], "Open": [1, 1, 0, 1]})
    pred = pd.Series([110.0, 150.0, 0.0, 50.0], index=[0, 1, 2, 3])
    out = nb.evaluate(df, pred)
    assert out["mae"] == pytest.approx(20.0)
    assert out["rmspe"] == pytest.approx(np.sqrt((0.1**2 + 0.25**2 + 0) / 3))


def test_lightgbm_beats_naive_on_simulated_promo(nb):
    df = make_stores(n_stores=5, days=600, seed=6)
    cutoff = df.Date.max() - pd.Timedelta(days=41)
    lgbm = nb.evaluate(df, nb.fit_predict(df, cutoff))
    naive = nb.evaluate(df, nb.seasonal_naive_last_week(df, cutoff))
    assert lgbm["mae"] < 0.6 * naive["mae"]


def test_real_rossmann(nb):
    raw = pd.read_csv(ex.dataset("store-sales") / "train.csv", dtype={"StateHoliday": str}, parse_dates=["Date"])
    df = nb.select_stores(raw)
    assert len(df) == 47100 and df.Store.nunique() == 50 and df.Store.max() == 60
    naive = nb.evaluate(df, nb.seasonal_naive_last_week(df, "2015-06-20"))
    assert naive["mae"] == pytest.approx(1501.3, abs=0.1)
    lgbm = nb.evaluate(df, nb.fit_predict(df, "2015-06-20"))
    assert lgbm["mae"] < 0.75 * naive["mae"]
