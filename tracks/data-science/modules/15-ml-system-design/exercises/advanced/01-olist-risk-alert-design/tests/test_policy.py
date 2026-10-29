import itertools
import re

import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

SECTIONS = ["Bối cảnh và mục tiêu", "Đóng khung bài toán", "Metric", "Dữ liệu, nhãn và feature", "Model",
            "Chính sách cảnh báo và năng lực vận hành", "Serving và fallback", "Monitoring và retrain",
            "Thí nghiệm", "Fairness và rủi ro", "Phương án đã loại", "Câu hỏi mở"]


@pytest.fixture(scope="module")
def policy():
    return ex.module("policy.py")


def reference_alerts(scores, weeks, threshold, cap):
    df = pd.DataFrame({"s": scores, "w": weeks})
    out = np.zeros(len(df), dtype=bool)
    for _, g in df[df.s >= threshold].groupby("w"):
        out[g.nlargest(cap, "s").index] = True
    return out


def test_weekly_late_volume_small(policy):
    T = pd.to_datetime
    orders = pd.DataFrame({
        "order_status": ["delivered"] * 5 + ["canceled"],
        "order_purchase_timestamp": T(["2018-01-01", "2018-01-02", "2018-01-03", "2018-01-16", "2018-01-22", "2018-01-02"]),
        "order_delivered_customer_date": T(["2018-01-20", "2018-01-05", "2018-01-30", "2018-02-10", "2018-02-01", "NaT"]),
        "order_estimated_delivery_date": T(["2018-01-15", "2018-01-10", "2018-01-25", "2018-02-01", "2018-02-05", "2018-01-10"]),
    })
    out = policy.weekly_late_volume(orders, start="2018-01-01", end="2018-02-01")
    # tuần kết thúc 01-07: 2 trễ | 01-14: 0 | 01-21: 1 | 01-28: 0
    assert list(out.index) == list(pd.to_datetime(["2018-01-07", "2018-01-14", "2018-01-21", "2018-01-28"]))
    assert list(out.astype(int)) == [2, 0, 1, 0]


def test_hybrid_alerts_small(policy):
    scores = [0.9, 0.8, 0.7, 0.2, 0.95, 0.1, 0.6]
    weeks = [1, 1, 1, 1, 2, 2, 2]
    out = policy.hybrid_alerts(scores, weeks, threshold=0.5, cap_per_week=2)
    assert list(out) == [True, True, False, False, True, False, True]
    assert policy.hybrid_alerts(scores, weeks, threshold=0.99, cap_per_week=5).sum() == 0


@pytest.mark.parametrize("seed", range(5))
def test_hybrid_alerts_random(policy, seed):
    rng = np.random.default_rng(seed)
    n = 3000
    scores, weeks = rng.random(n), rng.integers(0, 15, n)
    for t, cap in [(0.5, 30), (0.9, 1000), (0.0, 10)]:
        out = np.asarray(policy.hybrid_alerts(scores, weeks, t, cap))
        assert np.array_equal(out, reference_alerts(scores, weeks, t, cap))


@pytest.mark.parametrize("seed", range(5))
def test_choose_policy_matches_brute_force(policy, seed):
    rng = np.random.default_rng(seed)
    n = 4000
    weeks = rng.integers(0, 20, n)
    risk = rng.beta(1, 10, n) * np.where(weeks % 5 == 0, 3, 1)   # vài tuần khủng hoảng
    y = (rng.random(n) < np.clip(risk, 0, 1)).astype(int)
    scores = np.clip(risk + rng.normal(0, 0.03, n), 0, 1)
    thresholds, caps = [0.05, 0.1, 0.2, 0.3], [5, 20, 50]
    best = None
    for t, c in itertools.product(thresholds, caps):
        sel = reference_alerts(scores, weeks, t, c)
        v = y[sel].sum() * 0.15 * 30 - sel.sum() * 0.5
        key = (v, -sel.sum())
        if best is None or key > best[0]:
            best = (key, t, c)
    out = policy.choose_policy(y, scores, weeks, thresholds, caps, 0.5, 30, 0.15)
    assert out["value"] == pytest.approx(best[0][0])
    assert out["n_alerts"] == -best[0][1]
    assert (out["threshold"], out["cap"]) == (best[1], best[2])


def test_real_weekly_volume(policy):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=dates)
    out = policy.weekly_late_volume(orders)
    assert len(out) == 61
    assert out.median() == pytest.approx(61)
    assert out.max() == 565
    assert out.quantile(0.9) == pytest.approx(289, abs=1)


def test_design_doc_written():
    doc = ex.read("DESIGN.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 1200
    headings = re.findall(r"^## \d+\. (.+)$", doc, re.M)
    for s in SECTIONS:
        assert s in headings, f"Thiếu mục {s}"
