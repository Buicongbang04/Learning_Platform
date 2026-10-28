import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

FLAT_ROWS = [
    # order_id, item, customer, c_city, c_state, status, ts, product, category, seller, s_city, s_state, price, freight
    ("o1", 1, "c1", "sao paulo", "SP", "delivered", "2018-01-02 10:00:00", "p1", "perfumaria", "s1", "campinas", "SP", 50.00, 8.50),
    ("o1", 2, "c1", "sao paulo", "SP", "delivered", "2018-01-02 10:00:00", "p2", "esporte_lazer", "s2", "curitiba", "PR", 30.00, 8.50),
    ("o2", 1, "c2", "rio de janeiro", "RJ", "shipped", "2018-01-03 09:30:00", "p1", "perfumaria", "s1", "campinas", "SP", 52.00, 12.00),
    ("o3", 1, "c1", "sao paulo", "SP", "delivered", "2018-02-10 15:45:00", "p3", "informatica", "s3", "belo horizonte", "MG", 199.90, 20.10),
    ("o3", 2, "c1", "sao paulo", "SP", "delivered", "2018-02-10 15:45:00", "p3", "informatica", "s3", "belo horizonte", "MG", 199.90, 20.10),
    ("o4", 1, "c3", "salvador", "BA", "canceled", "2018-02-11 08:00:00", "p2", "esporte_lazer", "s2", "curitiba", "PR", 29.00, 15.00),
    ("o5", 1, "c4", "recife", "PE", "delivered", "2018-03-01 12:00:00", "p4", "beleza_saude", "s1", "campinas", "SP", 75.00, 18.30),
    ("o5", 2, "c4", "recife", "PE", "delivered", "2018-03-01 12:00:00", "p1", "perfumaria", "s4", "porto alegre", "RS", 48.00, 18.30),
]

EXPECTED_COLUMNS = {
    "customers": {"customer_id", "customer_city", "customer_state"},
    "sellers": {"seller_id", "seller_city", "seller_state"},
    "products": {"product_id", "product_category_name"},
    "orders": {"order_id", "customer_id", "order_status", "order_purchase_timestamp"},
    "order_items": {"order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"},
}

EXPECTED_PK = {
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
}


@pytest.fixture(scope="module")
def con():
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE orders_flat (
            order_id VARCHAR, order_item_id INTEGER, customer_id VARCHAR, customer_city VARCHAR,
            customer_state VARCHAR, order_status VARCHAR, order_purchase_timestamp TIMESTAMP,
            product_id VARCHAR, product_category_name VARCHAR, seller_id VARCHAR,
            seller_city VARCHAR, seller_state VARCHAR, price DECIMAL(10, 2), freight_value DECIMAL(10, 2)
        )
        """
    )
    con.executemany("INSERT INTO orders_flat VALUES (" + ",".join(["?"] * 14) + ")", FLAT_ROWS)
    con.execute(ex.read("normalize.sql"))
    yield con
    con.close()


def columns(con, table):
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?", [table]
    ).fetchall()
    return {r[0] for r in rows}


@pytest.mark.parametrize("table", list(EXPECTED_COLUMNS))
def test_table_has_exact_columns(con, table):
    assert columns(con, table) == EXPECTED_COLUMNS[table], f"Bảng {table} sai tập cột"


@pytest.mark.parametrize("table", list(EXPECTED_PK))
def test_primary_keys(con, table):
    rows = con.execute(
        "SELECT constraint_column_names FROM duckdb_constraints() "
        "WHERE table_name = ? AND constraint_type = 'PRIMARY KEY'",
        [table],
    ).fetchall()
    assert rows, f"Bảng {table} chưa có PRIMARY KEY"
    assert sorted(rows[0][0]) == sorted(EXPECTED_PK[table])


def test_foreign_keys(con):
    fks = con.execute(
        "SELECT table_name, constraint_column_names FROM duckdb_constraints() "
        "WHERE constraint_type = 'FOREIGN KEY'"
    ).fetchall()
    fk_cols = {(t, c) for t, cols in fks for c in cols}
    assert ("orders", "customer_id") in fk_cols
    assert ("order_items", "order_id") in fk_cols
    assert ("order_items", "product_id") in fk_cols
    assert ("order_items", "seller_id") in fk_cols


def test_row_counts(con):
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in EXPECTED_COLUMNS}
    assert counts == {"customers": 4, "sellers": 4, "products": 4, "orders": 5, "order_items": 8}


def test_lossless_join(con):
    rebuilt = """
        SELECT o.order_id, i.order_item_id, c.customer_id, c.customer_city, c.customer_state,
               o.order_status, o.order_purchase_timestamp, p.product_id, p.product_category_name,
               s.seller_id, s.seller_city, s.seller_state, i.price, i.freight_value
        FROM order_items i
        JOIN orders o USING (order_id)
        JOIN customers c ON c.customer_id = o.customer_id
        JOIN products p ON p.product_id = i.product_id
        JOIN sellers s ON s.seller_id = i.seller_id
    """
    missing = con.execute(f"SELECT * FROM orders_flat EXCEPT ALL ({rebuilt})").fetchall()
    extra = con.execute(f"({rebuilt}) EXCEPT ALL SELECT * FROM orders_flat").fetchall()
    assert missing == [] and extra == []
