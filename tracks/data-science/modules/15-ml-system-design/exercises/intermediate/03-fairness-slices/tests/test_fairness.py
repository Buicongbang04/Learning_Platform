import math

import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

DF = pd.DataFrame({
    "g":   ["A", "A", "A", "A", "B", "B", "B", "B", "B", "B"],
    "y":   [1, 1, 0, 0, 1, 0, 0, 0, 0, 0],
    "sel": [1, 0, 1, 0, 0, 1, 1, 0, 0, 0],
})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("fairness.ipynb")


def test_add_region(nb):
    df = pd.DataFrame({"customer_state": ["SP", "BA", "AM", "RJ", "MG", "CE"], "x": range(6)})
    out = nb.add_region(df)
    assert list(out.region) == ["SP", "N/NE", "N/NE", "khác", "khác", "N/NE"]
    assert "region" not in df.columns                      # không sửa df gốc
    out2 = nb.add_region(df.rename(columns={"customer_state": "uf"}), state_col="uf")
    assert list(out2.region) == list(out.region)


def test_select_top_k(nb):
    s = [0.1, 0.9, 0.5, 0.7, 0.3]
    assert list(nb.select_top_k(s, 2)) == [False, True, False, True, False]
    assert nb.select_top_k(s, 10).sum() == 5
    assert nb.select_top_k(np.array(s), 0).sum() == 0


def test_slice_report_by_hand(nb):
    rep = nb.slice_report(DF, "g", "y", "sel")
    assert list(rep.index) == ["A", "B"]
    a, b = rep.loc["A"], rep.loc["B"]
    assert a["n"] == 4 and b["n"] == 6
    assert a["prevalence"] == pytest.approx(0.5) and b["prevalence"] == pytest.approx(1 / 6)
    assert a["selection_rate"] == pytest.approx(0.5) and b["selection_rate"] == pytest.approx(2 / 6)
    assert a["precision"] == pytest.approx(0.5) and b["precision"] == pytest.approx(0.0)
    assert a["recall"] == pytest.approx(0.5) and b["recall"] == pytest.approx(0.0)
    assert a["fpr"] == pytest.approx(0.5) and b["fpr"] == pytest.approx(2 / 5)
    assert a["share_of_selected"] == pytest.approx(0.5) and b["share_of_positives"] == pytest.approx(1 / 3)


def test_slice_report_nan_when_undefined(nb):
    df = pd.DataFrame({"g": ["A", "A", "B", "B"], "y": [0, 0, 1, 0], "sel": [0, 0, 1, 0]})
    rep = nb.slice_report(df, "g", "y", "sel")
    assert math.isnan(rep.loc["A", "precision"]) and math.isnan(rep.loc["A", "recall"])
    assert rep.loc["B", "recall"] == pytest.approx(1.0)


def test_disparity(nb):
    rep = pd.DataFrame({"recall": [0.6, 0.3, np.nan], "fpr": [0.02, 0.1, 0.05]}, index=["X", "Y", "Z"])
    d = nb.disparity(rep, "recall")
    assert d["ratio"] == pytest.approx(0.5) and d["difference"] == pytest.approx(0.3) and d["worst_group"] == "Y"
    assert nb.disparity(rep, "fpr", higher_is_better=False)["worst_group"] == "Y"
    assert nb.disparity(rep, "fpr")["worst_group"] == "X"


def test_allocate_by_need(nb):
    rng = np.random.default_rng(0)
    groups = np.array(["A"] * 500 + ["B"] * 300 + ["C"] * 200)
    scores = np.r_[rng.uniform(0, 0.2, 500), rng.uniform(0, 0.4, 300), rng.uniform(0, 0.1, 200)]
    k = 101
    mask = nb.allocate_by_need(scores, groups, k)
    assert mask.dtype == bool and mask.sum() == k
    need = np.array([scores[groups == g].sum() for g in "ABC"])
    exact = need / need.sum() * k
    for g, e in zip("ABC", exact):
        got = mask[groups == g].sum()
        assert math.floor(e) <= got <= math.ceil(e)
        sg, mg = scores[groups == g], mask[groups == g]
        if 0 < got < len(sg):
            assert sg[mg].min() >= sg[~mg].max()        # top trong từng nhóm


def test_real_region_rates(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_delivered_customer_date", "order_estimated_delivery_date"]
    o = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    o = o[(o.order_status == "delivered") & o.order_delivered_customer_date.notna()]
    o = o.merge(pd.read_csv(raw / "olist_customers_dataset.csv")[["customer_id", "customer_state"]], on="customer_id")
    o["late"] = (o.order_delivered_customer_date > o.order_estimated_delivery_date).astype(int)
    o = nb.add_region(o)
    o["sel"] = nb.select_top_k(o.late + 0.0, int(o.late.sum()))
    rep = nb.slice_report(o, "region", "late", "sel")
    assert rep.loc["N/NE", "prevalence"] == pytest.approx(0.136, abs=0.001)
    assert rep.loc["SP", "prevalence"] == pytest.approx(0.059, abs=0.001)
    assert rep.loc["khác", "prevalence"] == pytest.approx(0.088, abs=0.001)
    assert rep.n.sum() == 96470
