import duckdb
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

T = pd.Timestamp
NaT = pd.NaT
# order_id, status, purchase, delivered
ORDERS = pd.DataFrame(
    [
        ("a1", "delivered", T("2017-01-10"), T("2017-01-20")),
        ("a2", "delivered", T("2017-02-03"), T("2017-02-10")),
        ("a3", "delivered", T("2017-03-15"), T("2017-03-25")),   # đơn có món của cả sA và sD
        ("a5", "delivered", T("2017-05-01"), T("2017-05-09")),
        ("a6", "delivered", T("2017-06-30"), T("2017-07-04")),
        ("a9", "delivered", T("2017-09-12"), T("2017-09-20")),
        ("b1", "delivered", T("2017-04-02"), T("2017-04-10")),
        ("b2", "delivered", T("2017-04-28"), T("2017-05-06")),   # cùng tháng mua với b1
        ("b3", "canceled", T("2017-05-05"), NaT),                 # huỷ: không tính
        ("b4", "delivered", T("2017-06-05"), NaT),                # chưa giao xong: không tính
        ("c1", "delivered", T("2017-12-20"), T("2018-01-03")),
        ("c2", "delivered", T("2018-01-15"), T("2018-01-25")),   # qua năm mới vẫn liên tiếp
        ("c3", "delivered", T("2018-09-05"), T("2018-09-15")),   # mua sau 2018-08-31: bỏ
        ("d2", "delivered", T("2017-11-11"), T("2017-11-20")),
    ],
    columns=["order_id", "order_status", "order_purchase_timestamp", "order_delivered_customer_date"],
)
ITEMS = pd.DataFrame(
    [("a1", "sA"), ("a2", "sA"), ("a3", "sA"), ("a3", "sA"), ("a3", "sD"), ("a5", "sA"), ("a6", "sA"),
     ("a9", "sA"), ("b1", "sB"), ("b2", "sB"), ("b3", "sB"), ("b4", "sB"), ("c1", "sC"), ("c2", "sC"),
     ("c3", "sC"), ("d2", "sD")],
    columns=["order_id", "seller_id"],
)
ITEMS["order_item_id"] = ITEMS.groupby("order_id").cumcount() + 1
ITEMS["price"] = 10.0


def fixture_con():
    con = duckdb.connect()
    con.register("orders_df", ORDERS)
    con.register("items_df", ITEMS)
    con.execute("CREATE TABLE orders AS SELECT * FROM orders_df")
    con.execute("CREATE TABLE order_items AS SELECT * FROM items_df")
    return con


def rows(df: pd.DataFrame, cols: list[str]) -> list[tuple]:
    df = df.copy()
    for c in ["start_month", "end_month"]:
        df[c] = pd.to_datetime(df[c]).dt.strftime("%Y-%m")
    return [tuple(r) for r in df[cols].itertuples(index=False)]


def test_streaks_fixture():
    out = fixture_con().sql(ex.read("streaks.sql")).df()
    assert list(out.columns) == ["seller_id", "start_month", "end_month", "n_months"]
    assert rows(out, ["seller_id", "start_month", "end_month", "n_months"]) == [
        ("sA", "2017-01", "2017-03", 3),
        ("sA", "2017-05", "2017-06", 2),
        ("sA", "2017-09", "2017-09", 1),
        ("sB", "2017-04", "2017-04", 1),
        ("sC", "2017-12", "2018-01", 2),
        ("sD", "2017-03", "2017-03", 1),
        ("sD", "2017-11", "2017-11", 1),
    ]


def test_spells_fixture():
    out = fixture_con().sql(ex.read("spells.sql")).df()
    assert list(out.columns) == ["seller_id", "start_month", "end_month", "active_months", "span_months"]
    # Nghỉ 1 tháng (sA tháng 4) vẫn cùng một đợt; nghỉ 2 tháng (sA tháng 7, 8) mở đợt mới
    assert rows(out, ["seller_id", "start_month", "end_month", "active_months", "span_months"]) == [
        ("sA", "2017-01", "2017-06", 5, 6),
        ("sA", "2017-09", "2017-09", 1, 1),
        ("sB", "2017-04", "2017-04", 1, 1),
        ("sC", "2017-12", "2018-01", 2, 2),
        ("sD", "2017-03", "2017-03", 1, 1),
        ("sD", "2017-11", "2017-11", 1, 1),
    ]


def test_real_olist():
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    con = duckdb.connect()
    for table in ["orders", "order_items"]:
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_csv_auto('{raw / f'olist_{table}_dataset.csv'}')")
    streaks = con.sql(ex.read("streaks.sql")).df()
    assert len(streaks) == 5183 and streaks["seller_id"].nunique() == 2970
    assert (streaks.groupby("seller_id")["n_months"].max() == 20).sum() == 35
    spells = con.sql(ex.read("spells.sql")).df()
    assert len(spells) == 3914
    assert (spells.groupby("seller_id").size() > 1).sum() == 735


def test_analysis_written():
    doc = ex.read("ANALYSIS.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 350
