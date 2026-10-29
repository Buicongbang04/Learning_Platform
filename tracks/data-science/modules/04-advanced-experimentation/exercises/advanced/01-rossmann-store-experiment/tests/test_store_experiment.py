import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

PRE = ("2015-05-04", "2015-05-31")
EXP = ("2015-06-01", "2015-06-28")


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("store_experiment.ipynb")


def make_train(n_stores: int = 400, seed: int = 0) -> pd.DataFrame:
    """Dữ liệu ngày giống train.csv của Rossmann: mỗi cửa hàng một mức doanh số riêng, Chủ nhật đóng cửa."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-05-04", "2015-06-28", freq="D")
    level = rng.lognormal(8.8, 0.35, n_stores)
    store = np.repeat(np.arange(1, n_stores + 1), len(dates))
    date = np.tile(dates, n_stores)
    open_ = (pd.DatetimeIndex(date).dayofweek < 6).astype(int)
    sales = level[store - 1] * rng.lognormal(0, 0.25, len(store)) * open_
    return pd.DataFrame({"Store": store, "Date": date, "Sales": sales.round(), "Open": open_})


@pytest.fixture(scope="module")
def panel_small():
    return pd.DataFrame({
        "pre": np.linspace(3000, 15000, 200),
        "y": np.linspace(3000, 15000, 200) * 0.97 + np.random.default_rng(1).normal(0, 400, 200),
    }, index=pd.Index(np.arange(1, 201), name="Store"))


def test_store_panel_uses_open_days_inside_windows(nb):
    train = pd.DataFrame({
        "Store": [1, 1, 1, 1, 1, 2, 2, 3],
        "Date": pd.to_datetime(["2015-05-03", "2015-05-04", "2015-05-31", "2015-06-01", "2015-06-28",
                                "2015-05-10", "2015-06-02", "2015-05-05"]),
        "Sales": [999, 100, 300, 50, 70, 0, 80, 40],
        "Open": [1, 1, 1, 1, 1, 0, 1, 1],
    })
    panel = nb.store_panel(train, PRE, EXP)
    assert {"pre", "y"} <= set(panel.columns)
    assert panel.loc[1, "pre"] == pytest.approx(200)      # 05-03 nằm ngoài cửa sổ, hai mút được tính
    assert panel.loc[1, "y"] == pytest.approx(60)
    assert 2 not in panel.index                           # cửa hàng 2 đóng cửa cả kỳ trước
    assert 3 not in panel.index                           # cửa hàng 3 không có dữ liệu kỳ thí nghiệm


def test_estimate_diff_and_validation(nb, panel_small):
    treat = np.arange(200) % 2 == 0
    out = nb.estimate(panel_small, treat, "diff")
    y = panel_small.y.to_numpy()
    assert out["diff"] == pytest.approx(y[treat].mean() - y[~treat].mean())
    assert out["se"] == pytest.approx(np.sqrt(y[treat].var(ddof=1) / 100 + y[~treat].var(ddof=1) / 100))
    with pytest.raises(ValueError):
        nb.estimate(panel_small, treat, "magic")


def test_cuped_and_poststrat_shrink_se(nb, panel_small):
    treat = np.random.default_rng(2).permutation(np.arange(200) % 2 == 0)
    raw = nb.estimate(panel_small, treat, "diff")
    cuped = nb.estimate(panel_small, treat, "cuped")
    post = nb.estimate(panel_small, treat, "poststrat")
    assert cuped["se"] < 0.2 * raw["se"]
    assert post["se"] < 0.5 * raw["se"]
    assert abs(cuped["diff"]) < 3 * cuped["se"]


def test_power_study(nb, panel_small):
    aa = nb.power_study(panel_small, lift=0.0, method="cuped", n_sims=400, seed=0)
    assert 0.02 <= aa <= 0.09
    weak = nb.power_study(panel_small, lift=0.03, method="diff", n_sims=200, seed=1)
    strong = nb.power_study(panel_small, lift=0.03, method="cuped", n_sims=200, seed=1)
    assert strong > 0.9 and weak < 0.3
    assert nb.power_study(panel_small, lift=0.02, method="cuped", n_sims=50, seed=3) == \
        nb.power_study(panel_small, lift=0.02, method="cuped", n_sims=50, seed=3)


def test_panel_from_daily_data(nb):
    panel = nb.store_panel(make_train(), PRE, EXP)
    assert len(panel) == 400
    assert np.corrcoef(panel.pre, panel.y)[0, 1] > 0.9


def test_real_rossmann(nb):
    path = ex.dataset("store-sales") / "train.csv"
    train = pd.read_csv(path, parse_dates=["Date"], dtype={"StateHoliday": str})
    panel = nb.store_panel(train, PRE, EXP)
    assert len(panel) == 1115
    assert panel.y.mean() == pytest.approx(7014.2, abs=1)
    assert np.corrcoef(panel.pre, panel.y)[0, 1] > 0.98


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300
