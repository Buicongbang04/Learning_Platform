import datetime as dt
from decimal import Decimal

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

REQUIRED = {
    "dim_date": {"date_key", "full_date", "year", "quarter", "month", "day", "day_of_week", "is_weekend"},
    "dim_customer": {"customer_key", "customer_id", "city", "state"},
    "dim_product": {"product_key", "product_id", "category_name"},
    "dim_seller": {"seller_key", "seller_id", "city", "state"},
    "fact_order_items": {
        "order_id", "order_item_id", "purchase_date_key", "customer_key",
        "product_key", "seller_key", "price", "freight_value",
    },
}


@pytest.fixture()
def con():
    con = duckdb.connect()
    con.execute(ex.read("schema.sql"))
    yield con
    con.close()


def load_sample(con):
    con.execute("INSERT INTO dim_customer VALUES (1, 'c1', 'sao paulo', 'SP'), (2, 'c2', 'rio de janeiro', 'RJ'), (3, 'c3', 'campinas', 'SP')")
    con.execute("INSERT INTO dim_product VALUES (1, 'p1', 'perfumaria'), (2, 'p2', 'informatica')")
    con.execute("INSERT INTO dim_seller VALUES (1, 's1', 'curitiba', 'PR')")
    con.execute(
        """
        INSERT INTO fact_order_items VALUES
          ('o1', 1, 20180105, 1, 1, 1, 50.00, 5.00),
          ('o1', 2, 20180105, 1, 2, 1, 100.00, 5.00),
          ('o2', 1, 20180120, 2, 1, 1, 80.00, 9.00),
          ('o3', 1, 20180131, 3, 2, 1, 20.00, 3.00),
          ('o4', 1, 20180201, 2, 2, 1, 300.00, 12.00)
        """
    )


@pytest.mark.parametrize("table", list(REQUIRED))
def test_tables_and_columns(con, table):
    cols = {
        r[0]
        for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?", [table]
        ).fetchall()
    }
    assert REQUIRED[table] <= cols, f"{table} thiếu cột {REQUIRED[table] - cols}"


def test_primary_and_foreign_keys(con):
    rows = con.execute(
        "SELECT table_name, constraint_type, constraint_column_names FROM duckdb_constraints()"
    ).fetchall()
    pks = {t: sorted(c) for t, kind, c in rows if kind == "PRIMARY KEY"}
    assert pks.get("fact_order_items") == ["order_id", "order_item_id"]
    assert pks.get("dim_date") == ["date_key"]
    assert pks.get("dim_customer") == ["customer_key"]
    fk_cols = {c for t, kind, cols in rows if kind == "FOREIGN KEY" and t == "fact_order_items" for c in cols}
    assert {"purchase_date_key", "customer_key", "product_key", "seller_key"} <= fk_cols


def test_dim_date_content(con):
    assert con.execute("SELECT COUNT(*), MIN(full_date), MAX(full_date) FROM dim_date").fetchone() == (
        730, dt.date(2017, 1, 1), dt.date(2018, 12, 31),
    )
    row = con.execute(
        "SELECT full_date, year, quarter, month, day, day_of_week, is_weekend FROM dim_date WHERE date_key = 20180804"
    ).fetchone()
    assert row == (dt.date(2018, 8, 4), 2018, 3, 8, 4, 6, True)  # 4/8/2018 là thứ Bảy
    row = con.execute("SELECT day_of_week, is_weekend FROM dim_date WHERE date_key = 20180101").fetchone()
    assert row == (1, False)  # 1/1/2018 là thứ Hai
    assert con.execute("SELECT COUNT(*) FROM dim_date WHERE is_weekend").fetchone()[0] == 209


def test_fk_rejects_unknown_customer(con):
    load_sample(con)
    with pytest.raises(duckdb.ConstraintException):
        con.execute("INSERT INTO fact_order_items VALUES ('o9', 1, 20180105, 999, 1, 1, 1.00, 1.00)")


def test_revenue_query(con):
    load_sample(con)
    rows = con.execute(ex.read("revenue_by_state_month.sql")).fetchall()
    assert [(int(y), int(m), s, Decimal(r)) for y, m, s, r in rows] == [
        (2018, 1, "SP", Decimal("170.00")),
        (2018, 1, "RJ", Decimal("80.00")),
        (2018, 2, "RJ", Decimal("300.00")),
    ]
