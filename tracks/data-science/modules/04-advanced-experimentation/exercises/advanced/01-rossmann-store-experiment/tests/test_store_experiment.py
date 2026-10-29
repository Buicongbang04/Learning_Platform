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


def test_cuped_and_poststrat_values(nb):
    # Panel 60 cửa hàng tính tay: y ≈ 0.5 · pre (theta khác 1), 10 decile mỗi decile 6 cửa hàng,
    # số treatment trong mỗi decile khác nhau (2, 3 hoặc 4) để trọng số tầng có ý nghĩa.
    rng = np.random.default_rng(5)
    pre = np.arange(1.0, 61.0) * 100
    y = 0.5 * pre + rng.normal(0, 30, 60)
    panel = pd.DataFrame({"pre": pre, "y": y}, index=pd.Index(np.arange(1, 61), name="Store"))
    pattern = {2: [1, 1, 0, 0, 0, 0], 3: [1, 1, 1, 0, 0, 0], 4: [1, 1, 1, 1, 0, 0]}
    n_treat = [2, 3, 4, 2, 3, 4, 2, 3, 4, 3]
    treat = np.concatenate([pattern[k] for k in n_treat]).astype(bool)

    theta = np.cov(y, pre)[0, 1] / np.var(pre, ddof=1)
    adj = y - theta * (pre - pre.mean())
    cuped = nb.estimate(panel, treat, "cuped")
    assert cuped["diff"] == pytest.approx(adj[treat].mean() - adj[~treat].mean())
    assert cuped["se"] == pytest.approx(np.sqrt(adj[treat].var(ddof=1) / treat.sum()
                                                + adj[~treat].var(ddof=1) / (~treat).sum()))

    strata = np.repeat(np.arange(10), 6)        # đúng bằng 10 decile của pre
    diff = var = 0.0
    for k in range(10):
        yt, yc = y[(strata == k) & treat], y[(strata == k) & ~treat]
        diff += 0.1 * (yt.mean() - yc.mean())   # w_k = N_k / N = 6 / 60
        var += 0.01 * (yt.var(ddof=1) / len(yt) + yc.var(ddof=1) / len(yc))
    post = nb.estimate(panel, treat, "poststrat")
    assert post["diff"] == pytest.approx(diff)
    assert post["se"] == pytest.approx(np.sqrt(var))


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
