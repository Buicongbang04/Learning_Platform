import duckdb
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

T = pd.Timestamp
NaT = pd.NaT
# order_id, status, purchase, approved, carrier, delivered
ORDERS = pd.DataFrame(
    [
        ("o1", "delivered", T("2018-01-01 10:00"), T("2018-01-01 11:00"), T("2018-01-02"), T("2018-01-05")),
        ("o2", "delivered", T("2018-01-01 10:00"), T("2018-01-01 11:00"), T("2018-01-02"), T("2018-01-06")),
        ("o3", "delivered", T("2018-01-02 10:00"), T("2018-01-02 12:00"), T("2018-01-03"), T("2018-01-07")),
        ("o4", "shipped", T("2018-01-02 10:00"), T("2018-01-02 12:00"), T("2018-01-04"), NaT),
        ("o5", "canceled", T("2018-01-03 10:00"), T("2018-01-03 12:00"), NaT, NaT),
        ("o6", "created", T("2018-01-03 10:00"), NaT, NaT, NaT),
        ("o7", "delivered", T("2018-01-04 10:00"), NaT, T("2018-01-05"), T("2018-01-08")),   # thiếu mốc duyệt
        ("o8", "delivered", T("2018-01-04 10:00"), T("2018-01-06 09:00"), T("2018-01-05"), T("2018-01-09")),  # giao hãng trước khi duyệt
        ("o9", "delivered", T("2018-01-05 10:00"), T("2018-01-05 11:00"), T("2018-01-06"), NaT),  # status delivered nhưng thiếu ngày giao
    ],
    columns=["order_id", "order_status", "order_purchase_timestamp", "order_approved_at",
             "order_delivered_carrier_date", "order_delivered_customer_date"],
)
ORDERS["customer_id"] = "c" + ORDERS["order_id"]
ORDERS["order_estimated_delivery_date"] = T("2018-01-20")
REVIEWS = pd.DataFrame(
    [
        ("r1", "o1", 5, T("2018-01-06")),
        ("r2a", "o2", 5, T("2018-01-07")),
        ("r2b", "o2", 1, T("2018-01-08")),   # review mới nhất của o2 là 1 sao
        ("r6", "o6", 5, T("2018-01-08")),    # o6 chưa được duyệt: không được tính
        ("r8", "o8", 4, T("2018-01-10")),
    ],
    columns=["review_id", "order_id", "review_score", "review_answer_timestamp"],
)
COLUMNS = ["step", "step_name", "orders", "pct_of_prev", "pct_of_first"]
NAMES = ["purchased", "approved", "shipped", "delivered", "reviewed", "good_review"]


def fixture_con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.register("orders_df", ORDERS)
    con.register("reviews_df", REVIEWS)
    con.execute("CREATE TABLE orders AS SELECT * FROM orders_df")
    con.execute("CREATE TABLE order_reviews AS SELECT * FROM reviews_df")
    return con


def run(name: str, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.sql(ex.read(name)).df()


@pytest.mark.parametrize("name", ["funnel.sql", "funnel_strict.sql"])
def test_shape(name):
    out = run(name, fixture_con())
    assert list(out.columns) == COLUMNS
    assert out["step"].tolist() == [1, 2, 3, 4, 5, 6]
    assert out["step_name"].tolist() == NAMES


def test_funnel_counts_are_sequential():
    out = run("funnel.sql", fixture_con())
    # o7 có ngày giao nhưng không có mốc duyệt: dừng ở bước 1; review của o6 không được tính
    assert out["orders"].tolist() == [9, 7, 6, 4, 3, 2]


def test_funnel_rates():
    out = run("funnel.sql", fixture_con())
    assert out["pct_of_prev"].tolist() == pytest.approx([1.0, 7 / 9, 6 / 7, 4 / 6, 3 / 4, 2 / 3])
    assert out["pct_of_first"].tolist() == pytest.approx([1.0, 7 / 9, 6 / 9, 4 / 9, 3 / 9, 2 / 9])


def test_funnel_strict_respects_time_order():
    out = run("funnel_strict.sql", fixture_con())
    # o8 giao cho hãng trước khi được duyệt: dừng ở bước 2
    assert out["orders"].tolist() == [9, 7, 5, 3, 2, 1]
    assert out["pct_of_prev"].tolist() == pytest.approx([1.0, 7 / 9, 5 / 7, 3 / 5, 2 / 3, 1 / 2])


def real_con() -> duckdb.DuckDBPyConnection:
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    con = duckdb.connect()
    for table in ["orders", "order_reviews"]:
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_csv_auto('{raw / f'olist_{table}_dataset.csv'}')")
    return con


def test_real_olist():
    con = real_con()
    assert run("funnel.sql", con)["orders"].tolist() == [99441, 99281, 97644, 96455, 95809, 75623]
    assert run("funnel_strict.sql", con)["orders"].tolist() == [99441, 99281, 96285, 95082, 94443, 74480]
