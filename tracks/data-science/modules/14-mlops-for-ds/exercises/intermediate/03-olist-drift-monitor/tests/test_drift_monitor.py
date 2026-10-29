import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("drift_monitor.ipynb")


def make_period(n: int, start: str, months: int, seed: int, shift: float = 0.0, new_state: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    span = (pd.Timestamp(start) + pd.DateOffset(months=months) - pd.Timestamp(start)).total_seconds()
    days = rng.uniform(0, span, n) / 86400        # mọi đơn nằm trong đúng các tháng được yêu cầu
    state = rng.choice(["SP", "RJ", "MG"], n, p=[0.6, 0.3, 0.1])
    state = np.where(rng.random(n) < new_state, "BA", state)
    return pd.DataFrame({
        "order_purchase_timestamp": pd.Timestamp(start) + pd.to_timedelta(days, unit="D"),
        "delay_days": rng.normal(-10 + shift, 6, n),
        "price": rng.lognormal(4.5, 0.8, n),
        "customer_state": state,
    }).sort_values("order_purchase_timestamp", ignore_index=True)


def test_psi_matches_basic_convention(nb):
    assert nb.psi(np.arange(100), np.arange(50, 150), bins=4) == pytest.approx(
        2 * (1e-4 - 0.25) * np.log(1e-4 / 0.25) + 0.5 * np.log(3), rel=1e-6)
    assert nb.psi(np.r_[np.arange(10.0), np.nan], np.arange(10.0)) == pytest.approx(0.0, abs=1e-12)
    ref = pd.Series(["a"] * 90 + ["b"] * 10)
    assert nb.psi_categorical(ref, ref) == pytest.approx(0.0, abs=1e-12)
    assert nb.psi_categorical(ref, pd.Series(["a"] * 80 + ["b"] * 10 + [None] * 10)) > 0.5


def test_drift_report_structure_and_order(nb):
    ref = make_period(6000, "2017-01-01", 12, seed=1)
    cur = make_period(3000, "2018-01-01", 3, seed=2, shift=6.0, new_state=0.2)
    out = nb.drift_report(ref, cur, ["delay_days", "price"], ["customer_state"])
    assert set(out.index) == {"delay_days", "price", "customer_state"}
    assert {"psi", "ks", "level"} <= set(out.columns)
    assert list(out.psi) == sorted(out.psi, reverse=True)
    assert out.loc["price", "level"] == "stable"
    assert out.loc["delay_days", "level"] == "major"
    assert out.loc["customer_state", "level"] == "major"            # bang mới chiếm 20%
    assert np.isnan(out.loc["customer_state", "ks"])
    assert out.loc["delay_days", "ks"] > 0.3 and out.loc["price", "ks"] < 0.05


def test_drift_report_psi_values(nb):
    ref = make_period(4000, "2017-01-01", 12, seed=3)
    cur = make_period(2000, "2018-01-01", 3, seed=4, shift=3.0)
    out = nb.drift_report(ref, cur, ["delay_days"], ["customer_state"])
    assert out.loc["delay_days", "psi"] == pytest.approx(nb.psi(ref.delay_days, cur.delay_days))
    assert out.loc["customer_state", "psi"] == pytest.approx(nb.psi_categorical(ref.customer_state, cur.customer_state))


def test_monthly_psi_shape(nb):
    ref = make_period(6000, "2017-01-01", 12, seed=5)
    cur = make_period(3000, "2018-01-01", 3, seed=6)
    out = nb.monthly_psi(ref, cur, ["delay_days", "price"])
    assert list(out.index) == ["2018-01", "2018-02", "2018-03"]
    assert set(out.columns) == {"delay_days", "price", "n"}
    months = cur.order_purchase_timestamp.dt.strftime("%Y-%m")
    assert out.n.tolist() == months.value_counts().sort_index().tolist()
    feb = cur[months == "2018-02"]
    assert out.loc["2018-02", "delay_days"] == pytest.approx(nb.psi(ref.delay_days, feb.delay_days))


def test_monthly_detects_the_drifting_month_and_alerts(nb):
    ref = make_period(6000, "2017-01-01", 12, seed=7)
    parts = [make_period(2000, "2018-01-01", 1, seed=8),
             make_period(2000, "2018-02-01", 1, seed=9, shift=8.0),   # tháng 2 trôi mạnh
             make_period(2000, "2018-03-01", 1, seed=10)]
    cur = pd.concat(parts, ignore_index=True)
    out = nb.monthly_psi(ref, cur, ["delay_days", "price"])
    assert out.delay_days.idxmax() == "2018-02"
    assert nb.alerts(out) == [("2018-02", "delay_days")]
    assert nb.alerts(out, threshold=10.0) == []
    many = nb.alerts(out, threshold=0.0)
    assert len(many) == 6 and many == sorted(many)                 # 3 tháng x 2 feature, không có cột n


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    table = nb.load_olist_table(raw)
    splits = nb.time_split(table)
    report = nb.drift_report(splits["train"], splits["test"], nb.NUMERIC, nb.CATEGORICAL)
    assert list(report.index[:2]) == ["freight", "promised_days"]
    assert report.loc["freight", "psi"] == pytest.approx(0.3175, abs=0.003)
    assert report.loc["delay_days", "psi"] == pytest.approx(0.0729, abs=0.002)
    assert report.loc["delay_days", "level"] == "stable"
    prod = table[(table.order_purchase_timestamp >= "2018-01-01") & (table.order_purchase_timestamp < "2018-09-01")]
    monthly = nb.monthly_psi(splits["train"], prod, ["delay_days", "freight"])
    assert len(monthly) == 8
    assert monthly.loc["2018-06", "delay_days"] == pytest.approx(0.652, abs=0.005)
    assert ("2018-06", "delay_days") in nb.alerts(monthly)
