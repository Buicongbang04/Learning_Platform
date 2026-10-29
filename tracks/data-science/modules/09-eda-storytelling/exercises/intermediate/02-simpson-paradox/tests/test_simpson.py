import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)
RAW = ROOT / "data" / "raw"


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("simpson.ipynb")


def from_counts(rows):
    """rows: (group, stratum, successes, n) → DataFrame một dòng mỗi quan sát."""
    parts = []
    for group, stratum, k, n in rows:
        parts.append(pd.DataFrame({"group": group, "stratum": stratum, "y": [1] * k + [0] * (n - k)}))
    return pd.concat(parts, ignore_index=True)


# Ví dụ kinh điển sỏi thận (Charig et al. 1986): A tốt hơn ở cả hai tầng nhưng tệ hơn khi gộp
KIDNEY = from_counts([("A", "small", 81, 87), ("A", "large", 192, 263),
                      ("B", "small", 234, 270), ("B", "large", 55, 80)])


def test_stratified_rates(nb):
    out = nb.stratified_rates(KIDNEY, "group", "stratum", "y")
    assert list(out.columns) == ["stratum", "group", "n", "rate"]
    assert len(out) == 4
    row = out[(out.stratum == "small") & (out.group == "A")].iloc[0]
    assert row["n"] == 87 and row["rate"] == pytest.approx(81 / 87)
    assert out.n.sum() == len(KIDNEY)


def test_standardized_default_weights(nb):
    out = nb.standardized_rates(KIDNEY, "group", "stratum", "y")
    w_small = (87 + 270) / 700
    expected_a = w_small * 81 / 87 + (1 - w_small) * 192 / 263
    expected_b = w_small * 234 / 270 + (1 - w_small) * 55 / 80
    assert out["A"] == pytest.approx(expected_a)
    assert out["B"] == pytest.approx(expected_b)


def test_standardized_custom_weights_and_missing_stratum(nb):
    df = pd.concat([KIDNEY, from_counts([("A", "huge", 1, 4)])], ignore_index=True)   # B không có "huge"
    w = pd.Series({"small": 3.0, "large": 1.0, "huge": 100.0})
    out = nb.standardized_rates(df, "group", "stratum", "y", weights=w)
    assert out["A"] == pytest.approx(0.75 * 81 / 87 + 0.25 * 192 / 263)    # "huge" bị bỏ, trọng số chuẩn hoá lại
    assert out["B"] == pytest.approx(0.75 * 234 / 270 + 0.25 * 55 / 80)


def test_standardized_with_boolean_stratum(nb):
    df = KIDNEY.assign(stratum=KIDNEY.stratum.eq("large"))
    out = nb.standardized_rates(df, "group", "stratum", "y")
    w_large = (263 + 80) / 700
    assert out["A"] == pytest.approx((1 - w_large) * 81 / 87 + w_large * 192 / 263)


def test_simpson_check_kidney(nb):
    out = nb.simpson_check(KIDNEY, "group", "stratum", "y", "A", "B")
    assert out["crude_diff"] == pytest.approx(273 / 350 - 289 / 350)
    assert out["crude_diff"] < 0 < out["adjusted_diff"]
    assert out["n_strata"] == 2 and out["strata_against_crude"] == 2
    assert out["reversal"] is True


def test_simpson_check_no_reversal_and_other_groups_ignored(nb):
    df = from_counts([("A", "s1", 30, 100), ("A", "s2", 60, 100), ("B", "s1", 20, 100),
                      ("B", "s2", 50, 100), ("C", "s1", 0, 500)])
    out = nb.simpson_check(df, "group", "stratum", "y", "A", "B")
    assert out["crude_diff"] == pytest.approx(0.1)
    assert out["adjusted_diff"] == pytest.approx(0.1)        # trọng số chỉ tính trên A và B
    assert out["strata_against_crude"] == 0 and out["reversal"] is False


def test_mix_shift_simulation(nb):
    # Mỗi tầng: B cao hơn A 2 điểm. A dồn vào tầng tỉ lệ thấp → gộp lại A trông tốt hơn.
    for seed in range(5):
        rng = np.random.default_rng(seed)
        n = 40000
        group = rng.choice(["A", "B"], n)
        p_slow = np.where(group == "A", 0.1, 0.6)
        stratum = np.where(rng.random(n) < p_slow, "slow", "fast")
        base = np.where(stratum == "slow", 0.40, 0.08)
        y = rng.random(n) < base + np.where(group == "B", 0.02, 0.0)
        df = pd.DataFrame({"group": group, "stratum": stratum, "y": y})
        out = nb.simpson_check(df, "group", "stratum", "y", "B", "A")
        assert out["crude_diff"] > 0.1
        assert out["adjusted_diff"] == pytest.approx(0.02, abs=0.015)
        assert out["reversal"] is False
        out = nb.simpson_check(df, "group", "stratum", "y", "A", "B")
        assert out["adjusted_diff"] == pytest.approx(-0.02, abs=0.015)


ORDERS = pd.DataFrame({
    "order_id": ["o1", "o2", "o3", "o4", "o5"],
    "customer_id": ["c1", "c2", "c3", "c4", "c5"],
    "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered"],
    "order_purchase_timestamp": pd.to_datetime(["2018-01-01", "2018-01-01", "2018-01-01", "2018-01-01", "2018-01-01"]),
    "order_delivered_customer_date": pd.to_datetime(["2018-01-08 12:00", "2018-01-31 00:00", None, None, "2018-01-10 15:00"]),
    "order_estimated_delivery_date": pd.to_datetime(["2018-01-20", "2018-01-25", "2018-01-20", "2018-01-20", "2018-01-10"]),
})
REVIEWS = pd.DataFrame({
    "order_id": ["o1", "o2", "o2", "o3", "o4"],
    "review_score": [5, 5, 1, 1, 1],
    "review_answer_timestamp": pd.to_datetime(["2018-01-09", "2018-02-01", "2018-02-03", "2018-01-21", "2018-01-03"]),
})
CUSTOMERS = pd.DataFrame({"customer_id": ["c1", "c2", "c3", "c4", "c5"],
                          "customer_state": ["SP", "RJ", "SP", "MG", "BA"]})


def test_build_orders(nb):
    out = nb.build_orders(ORDERS, REVIEWS, CUSTOMERS).set_index("order_id").sort_index()
    assert set(out.columns) >= {"customer_state", "late", "bad", "delivery_days"}
    assert list(out.index) == ["o1", "o2"]                  # o3 thiếu ngày giao, o4 huỷ, o5 không có review
    assert out.loc["o2", "bad"] == True                     # review mới nhất là 1 sao
    assert out.loc["o2", "late"] == True and out.loc["o1", "late"] == False
    assert out.loc["o1", "delivery_days"] == pytest.approx(7.5)
    assert out.loc["o1", "customer_state"] == "SP"


def test_build_orders_same_day_counts_as_late(nb):
    reviews = pd.concat([REVIEWS, pd.DataFrame({"order_id": ["o5"], "review_score": [3],
                                                "review_answer_timestamp": pd.to_datetime(["2018-01-12"])})])
    out = nb.build_orders(ORDERS, reviews, CUSTOMERS).set_index("order_id")
    assert out.loc["o5", "late"] == True                    # 15:00 ngày hẹn > 00:00 ngày hẹn


def test_delivery_bucket(nb):
    out = nb.delivery_bucket(pd.Series([0.0, 6.99, 7.0, 13.5, 14.0, 21.0, 29.99, 30.0, 120.0]))
    assert [str(x) for x in out] == ["0-6", "0-6", "7-13", "7-13", "14-20", "21-29", "21-29", "30+", "30+"]
    assert list(out.cat.categories) == ["0-6", "7-13", "14-20", "21-29", "30+"]
    assert out.cat.ordered


def test_real_olist_sp(nb):
    if not (RAW / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    df = nb.build_orders(
        pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=dates),
        pd.read_csv(RAW / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"]),
        pd.read_csv(RAW / "olist_customers_dataset.csv"),
    )
    assert len(df) == 95824
    assert df.late.mean() == pytest.approx(0.0799, abs=5e-4)
    assert df.bad.mean() == pytest.approx(0.1281, abs=5e-4)
    df["region"] = np.where(df.customer_state == "SP", "SP", "other")
    df["days"] = nb.delivery_bucket(df.delivery_days)
    out = nb.simpson_check(df, "region", "days", "bad", "SP", "other")
    assert out["crude_diff"] == pytest.approx(-0.0366, abs=5e-4)
    assert out["adjusted_diff"] == pytest.approx(0.0292, abs=5e-4)
    assert out["strata_against_crude"] == 4 and out["reversal"] is True
    out = nb.simpson_check(df, "region", "late", "bad", "SP", "other")
    assert out["adjusted_diff"] == pytest.approx(-0.0212, abs=5e-4)
    assert out["reversal"] is False
