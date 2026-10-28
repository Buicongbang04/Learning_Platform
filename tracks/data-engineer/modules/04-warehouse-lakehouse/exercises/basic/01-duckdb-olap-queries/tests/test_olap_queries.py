import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

ORDERS = [
    ("o1", "SP", "delivered", "2024-01-05 10:00:00"),
    ("o2", "SP", "delivered", "2024-02-10 09:00:00"),
    ("o3", "RJ", "delivered", "2024-01-20 12:00:00"),
    ("o4", "RJ", "canceled", "2024-02-01 08:00:00"),
    ("o5", "MG", "delivered", "2024-03-15 15:00:00"),
    ("o6", "SP", "delivered", "2024-03-02 11:00:00"),
]
ITEMS = [
    ("o1", 1, "p1", 100.0),
    ("o1", 2, "p2", 50.0),
    ("o2", 1, "p1", 100.0),
    ("o3", 1, "p3", 80.0),
    ("o4", 1, "p3", 999.0),
    ("o5", 1, "p4", 30.0),
    ("o5", 2, "p2", 50.0),
    ("o6", 1, "p5", 150.0),
]
PRODUCTS = [
    ("p1", "toys"),
    ("p2", "toys"),
    ("p3", "books"),
    ("p4", "books"),
    ("p5", "toys"),
]


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE orders (order_id VARCHAR, customer_state VARCHAR, order_status VARCHAR,"
        " order_purchase_timestamp TIMESTAMP)"
    )
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", ORDERS)
    con.execute("CREATE TABLE order_items (order_id VARCHAR, order_item_id INTEGER, product_id VARCHAR, price DOUBLE)")
    con.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?)", ITEMS)
    con.execute("CREATE TABLE products (product_id VARCHAR, product_category_name VARCHAR)")
    con.executemany("INSERT INTO products VALUES (?, ?)", PRODUCTS)
    yield con
    con.close()


def run(con, name):
    rel = con.sql(ex.read(name))
    return rel.columns, rel.fetchall()


def test_revenue_rollup(con):
    cols, rows = run(con, "revenue_rollup.sql")
    assert cols == ["customer_state", "order_month", "revenue"]
    assert rows == [
        ("MG", "2024-03", 80.0),
        ("MG", None, 80.0),
        ("RJ", "2024-01", 80.0),
        ("RJ", None, 80.0),
        ("SP", "2024-01", 150.0),
        ("SP", "2024-02", 100.0),
        ("SP", "2024-03", 150.0),
        ("SP", None, 400.0),
        (None, None, 560.0),
    ]


def test_top_products(con):
    cols, rows = run(con, "top_products.sql")
    assert cols == ["category", "product_id", "revenue", "rnk"]
    # toys: p1=200, p5=150, p2=100 -> lấy p1, p5. books: p3=80 (o4 bị huỷ), p4=30.
    assert rows == [
        ("books", "p3", 80.0, 1),
        ("books", "p4", 30.0, 2),
        ("toys", "p1", 200.0, 1),
        ("toys", "p5", 150.0, 2),
    ]


def test_top_products_tie_break(con):
    con.execute("INSERT INTO orders VALUES ('o7', 'SP', 'delivered', '2024-03-20 10:00:00')")
    con.execute("INSERT INTO order_items VALUES ('o7', 1, 'p2', 50.0), ('o7', 2, 'p0', 150.0)")
    con.execute("INSERT INTO products VALUES ('p0', 'toys')")
    _, rows = run(con, "top_products.sql")
    toys = [r for r in rows if r[0] == "toys"]
    # p1=200, p0=150, p5=150, p2=150 -> p1 rồi p0 (hoà thì product_id nhỏ hơn)
    assert toys == [("toys", "p1", 200.0, 1), ("toys", "p0", 150.0, 2)]


def test_monthly_running(con):
    cols, rows = run(con, "monthly_running.sql")
    assert cols == ["order_month", "revenue", "cumulative_revenue", "mom_growth_pct"]
    assert [r[:3] for r in rows] == [
        ("2024-01", 230.0, 230.0),
        ("2024-02", 100.0, 330.0),
        ("2024-03", 230.0, 560.0),
    ]
    assert rows[0][3] is None
    assert rows[1][3] == pytest.approx(-56.52)
    assert rows[2][3] == pytest.approx(130.0)
