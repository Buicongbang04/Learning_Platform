import re

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.proportion import proportion_confint

from testkit import ROOT, Exercise

ex = Exercise(__file__)
RAW = ROOT / "data" / "raw"
MEMO_HEADINGS = ["## Tình huống", "## Vấn đề", "## Câu hỏi", "## Trả lời và đề xuất", "## Bằng chứng", "## Giới hạn"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("eda.ipynb")


def ts(values):
    return pd.to_datetime(pd.Series(values, dtype="object"), format="ISO8601")


ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4"],
    "customer_id": ["c1", "c2", "c3", "c4"],
    "order_status": ["delivered", "delivered", "canceled", "delivered"],
    "order_purchase_timestamp": ts(["2018-01-05 12:00", "2018-02-01", "2018-02-02", "2018-02-03"]),
    "order_delivered_customer_date": ts(["2018-01-10 00:00", "2018-02-20 10:00", None, "2018-02-10"]),
    "order_estimated_delivery_date": ts(["2018-01-25", "2018-02-20", "2018-02-25", "2018-02-28"]),
})
ITEMS = pd.DataFrame({
    "order_id": ["o1", "o1", "o1", "o2", "o4"],
    "order_item_id": [1, 2, 3, 1, 1],
    "seller_id": ["s1", "s1", "s2", "s2", "s1"],
    "price": [10.0, 10.0, 30.0, 99.0, 5.0],
    "freight_value": [2.0, 2.0, 6.0, 15.0, 1.0],
})
REVIEWS = pd.DataFrame({
    "order_id": ["o1", "o2", "o2", "o3"],
    "review_score": [4, 5, 2, 1],
    "review_answer_timestamp": ts(["2018-01-12", "2018-02-21", "2018-02-25", "2018-02-26"]),
})
CUSTOMERS = pd.DataFrame({"customer_id": ["c1", "c2", "c3", "c4"], "customer_state": ["SP", "RJ", "MG", "BA"]})
SELLERS = pd.DataFrame({"seller_id": ["s1", "s2"], "seller_state": ["PR", "SP"]})


def test_order_table(nb):
    out = nb.order_table(ORDERS, ITEMS, REVIEWS, CUSTOMERS, SELLERS).set_index("order_id").sort_index()
    assert list(out.index) == ["o1", "o2"]                    # o3 huỷ; o4 không có review
    assert {"purchase_month", "customer_state", "seller_state", "n_items", "n_sellers", "price", "freight",
            "delivery_days", "promised_days", "late", "bad"} <= set(out.columns)
    o1, o2 = out.loc["o1"], out.loc["o2"]
    assert o1["n_items"] == 3 and o1["n_sellers"] == 2
    assert o1["price"] == pytest.approx(50.0) and o1["freight"] == pytest.approx(10.0)
    assert o1["seller_state"] == "PR" and o2["seller_state"] == "SP"
    assert o1["delivery_days"] == pytest.approx(4.5)
    assert o1["promised_days"] == pytest.approx(19.5)
    assert o1["purchase_month"] == pd.Period("2018-01", "M")
    assert not o1["late"] and not o1["bad"]
    assert o2["late"] and o2["bad"]                            # 10:00 ngày hẹn là trễ; review mới nhất 2 sao


def test_rate_by_wilson_and_lift(nb):
    table = pd.DataFrame({"f": ["a"] * 40 + ["b"] * 100 + ["c"] * 5,
                          "bad": [1] * 10 + [0] * 30 + [1] * 5 + [0] * 95 + [1] * 5})
    out = nb.rate_by(table, "f", min_n=30)
    assert list(out.index) == ["a", "b"]                     # c bị bỏ (n = 5), sắp rate giảm dần
    assert out.index.name == "f"
    assert list(out.columns) == ["n", "rate", "ci_low", "ci_high", "lift"]
    lo, hi = proportion_confint(10, 40, method="wilson")
    # statsmodels dùng z = 1.95996…; z = 1.96 lệch cỡ 1e-6
    assert out.loc["a", "ci_low"] == pytest.approx(lo, abs=1e-4) and out.loc["a", "ci_high"] == pytest.approx(hi, abs=1e-4)
    overall = 20 / 145                                       # tính trên toàn bảng, kể cả nhóm nhỏ
    assert out.loc["b", "lift"] == pytest.approx(0.05 / overall)
    assert out.loc["a", "n"] == 40


def test_rate_by_handles_zero_and_one(nb):
    table = pd.DataFrame({"f": ["x"] * 50 + ["y"] * 50, "bad": [0] * 50 + [1] * 50})
    out = nb.rate_by(table, "f")
    assert out.loc["x", "ci_low"] == pytest.approx(0.0, abs=1e-12) and 0 < out.loc["x", "ci_high"] < 0.1
    assert 0.9 < out.loc["y", "ci_low"] < 1 and out.loc["y", "ci_high"] == pytest.approx(1.0)


def mix_table():
    # kỳ A: 10% trễ; kỳ B: 30% trễ; tỉ lệ review xấu trong từng segment giữ nguyên
    rows = []
    for period, n_late, n_on in (("A", 100, 900), ("B", 300, 700)):
        rows += [(period, True, i < n_late // 2) for i in range(n_late)]
        rows += [(period, False, i < n_on // 10) for i in range(n_on)]
    return pd.DataFrame(rows, columns=["period", "late", "bad"])


def test_decompose_pure_mix(nb):
    out = nb.decompose_change(mix_table(), "period", "A", "B")
    assert out["total"] == pytest.approx((150 + 70) / 1000 - (50 + 90) / 1000)
    assert out["mix"] == pytest.approx(0.2 * (0.5 - 0.1))
    assert out["rate"] == pytest.approx(0.0, abs=1e-12)


def test_decompose_identity_random(nb):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"period": rng.choice(["p", "q"], 5000), "seg": rng.choice(["s1", "s2", "s3"], 5000),
                       "y": rng.random(5000) < 0.3})
    out = nb.decompose_change(df, "period", "p", "q", segment="seg", target="y")
    assert out["mix"] + out["rate"] == pytest.approx(out["total"])
    assert set(out) == {"total", "mix", "rate"}


def test_real_olist(nb):
    if not (RAW / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    table = nb.order_table(
        pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=dates),
        pd.read_csv(RAW / "olist_order_items_dataset.csv"),
        pd.read_csv(RAW / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"]),
        pd.read_csv(RAW / "olist_customers_dataset.csv"),
        pd.read_csv(RAW / "olist_sellers_dataset.csv"),
    )
    assert len(table) == 95824
    assert table.late.mean() == pytest.approx(0.0799, abs=5e-4)
    assert table.bad.mean() == pytest.approx(0.1281, abs=5e-4)
    states = nb.rate_by(table, "customer_state")
    assert states.index[0] == "AL" and states.loc["AL", "n"] == 394
    assert states.index[-1] == "AP" and states.loc["AP", "n"] == 66   # "tốt nhất" nhưng CI rất rộng
    assert states.loc["AP", "ci_high"] - states.loc["AP", "ci_low"] > 0.1
    jan, mar = pd.Period("2018-01", "M"), pd.Period("2018-03", "M")
    out = nb.decompose_change(table, "purchase_month", jan, mar)
    assert out["total"] == pytest.approx(0.0747, abs=5e-4)
    assert out["mix"] == pytest.approx(0.0769, abs=5e-4)
    assert out["rate"] == pytest.approx(-0.0022, abs=5e-4)


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo
    words = len(memo.split())
    assert 250 <= words <= 700, f"Memo một trang: 250–700 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Tiêu đề là kết luận, có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
