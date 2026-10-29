import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)
RAW = ROOT / "data" / "raw"
COLUMNS = ["n", "events", "rate", "expected", "lower", "upper", "excess", "flag"]


@pytest.fixture(scope="module")
def sc():
    return ex.module("scorecard.py")


def make_small():
    # tỉ lệ chung = 60 / 1000 = 0.06
    rows = {"big_bad": (400, 46), "big_ok": (400, 12), "tiny": (2, 2), "mid": (198, 0)}
    parts = [pd.DataFrame({"seller_id": k, "late": [True] * e + [False] * (n - e)}) for k, (n, e) in rows.items()]
    return pd.concat(parts, ignore_index=True)


def test_funnel_columns_and_counts(sc):
    f = sc.seller_funnel(make_small())
    assert list(f.columns) == COLUMNS
    assert f.loc["big_bad", "n"] == 400 and f.loc["big_bad", "events"] == 46
    assert f.loc["big_bad", "rate"] == pytest.approx(0.115)
    assert np.allclose(f["expected"], 0.06)
    assert f.loc["big_bad", "excess"] == pytest.approx(46 - 0.06 * 400)


def test_funnel_limits(sc):
    f = sc.seller_funnel(make_small())
    half = 3 * np.sqrt(0.06 * 0.94 / 400)
    # README quy định xấp xỉ normal; giới hạn nhị thức chính xác ở n = 400 cũng nằm trong sai số này
    assert f.loc["big_ok", "upper"] == pytest.approx(0.06 + half, abs=0.01)
    assert f.loc["big_ok", "lower"] == pytest.approx(0.06 - half, abs=0.01)
    assert f.loc["tiny", "lower"] == 0.0                      # cắt ở 0
    assert (f.lower <= f.expected).all() and (f.expected <= f.upper).all()
    assert f.loc["mid", "upper"] - f.loc["mid", "lower"] > f.loc["big_ok", "upper"] - f.loc["big_ok", "lower"]


def test_funnel_flags(sc):
    f = sc.seller_funnel(make_small())
    assert f.loc["big_bad", "flag"] == "above"
    assert f.loc["big_ok", "flag"] == "within"
    assert f.loc["mid", "flag"] == "below"                   # 0/198 khi kỳ vọng 11.9 đơn trễ


def test_funnel_other_unit_and_target(sc):
    t = make_small().rename(columns={"seller_id": "state", "late": "bad"})
    f = sc.seller_funnel(t, unit="state", target="bad", z=2.0)
    assert f.loc["big_ok", "upper"] == pytest.approx(0.06 + 2 * np.sqrt(0.06 * 0.94 / 400), abs=0.01)


def test_alerts_min_n_and_order(sc):
    rows = {"a": (400, 60), "b": (1000, 120), "c": (5000, 300), "tiny": (2, 2), "mid": (200, 0)}
    t = pd.concat([pd.DataFrame({"seller_id": k, "late": [True] * e + [False] * (n - e)})
                   for k, (n, e) in rows.items()], ignore_index=True)
    f = sc.seller_funnel(t)                                    # tỉ lệ chung 482 / 6602 ≈ 7.3%
    # tiny trễ 2/2 nhưng chỉ có 2 đơn; b vượt kỳ vọng ~47 đơn, a ~31; c và mid tốt hơn kỳ vọng
    assert sc.alerts(f, min_n=20) == ["b", "a"]


def simulate(seed):
    rng = np.random.default_rng(seed)
    sizes = np.clip(rng.lognormal(3, 1.2, 300).astype(int), 1, 3000)
    bad = rng.choice(np.where(sizes >= 60)[0], 10, replace=False)
    parts = [pd.DataFrame({"seller_id": f"s{i:03d}", "late": rng.random(n) < (0.30 if i in bad else 0.08)})
             for i, n in enumerate(sizes)]
    return pd.concat(parts, ignore_index=True), {f"s{i:03d}" for i in bad}


def test_alerts_find_planted_bad_sellers(sc):
    for seed in range(5):
        table, bad = simulate(seed)
        out = set(sc.alerts(sc.seller_funnel(table), min_n=20))
        assert len(out & bad) >= 8, seed
        assert len(out - bad) <= 2, seed


def test_naive_ranking_is_dominated_by_tiny_sellers(sc):
    table, _ = simulate(0)
    f = sc.seller_funnel(table)
    top_by_rate = f.sort_values("rate", ascending=False).head(10)
    assert top_by_rate.n.median() < 20                      # đây là lý do cần funnel plot


def test_real_olist(sc):
    if not (RAW / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=dates)
    items = pd.read_csv(RAW / "olist_order_items_dataset.csv", usecols=["order_id", "order_item_id", "seller_id"])
    d = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()
               & (orders.order_purchase_timestamp < "2018-09-01")]
    table = d.merge(items[items.order_item_id == 1][["order_id", "seller_id"]], on="order_id")
    table["late"] = table.order_delivered_customer_date > table.order_estimated_delivery_date
    f = sc.seller_funnel(table)
    assert len(f) == 2960
    assert f.expected.iloc[0] == pytest.approx(0.0811, abs=5e-4)
    out = sc.alerts(f, min_n=20)
    assert 30 <= len(out) <= 50
    assert out[0] == "06a2c3af7b3aee5d69171b0e14f0ee87"      # 90 đơn trễ trên 388, vượt kỳ vọng ~58


def test_dashboard_doc_written():
    doc = ex.read("DASHBOARD.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 350
