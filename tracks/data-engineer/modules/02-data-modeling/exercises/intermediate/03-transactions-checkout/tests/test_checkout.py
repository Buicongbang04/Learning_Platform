import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

import testkit
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture()
def co():
    return ex.module("checkout.py")


@pytest.fixture()
def con(co):
    con = sqlite3.connect(":memory:")
    co.create_schema(con)
    con.executemany("INSERT INTO stock VALUES (?, ?)", [("p1", 5), ("p2", 1), ("p3", 0)])
    con.commit()
    yield con
    con.close()


def snapshot(con):
    return (
        con.execute("SELECT * FROM stock ORDER BY product_id").fetchall(),
        con.execute("SELECT * FROM orders ORDER BY order_id").fetchall(),
        con.execute("SELECT * FROM order_items ORDER BY order_id, product_id").fetchall(),
    )


def test_happy_path(co, con):
    total = co.place_order(con, "o1", "c1", [("p1", 2, 10.5), ("p2", 1, 99.99)])
    assert total == pytest.approx(120.99)
    stock, orders, items = snapshot(con)
    assert stock == [("p1", 3), ("p2", 0), ("p3", 0)]
    assert orders == [("o1", "c1", pytest.approx(120.99))]
    assert sorted(items) == [("o1", "p1", 2, 10.5), ("o1", "p2", 1, 99.99)]


def test_out_of_stock_rolls_back_everything(co, con):
    before = snapshot(con)
    with pytest.raises(co.OutOfStock):
        co.place_order(con, "o2", "c1", [("p1", 2, 10.0), ("p2", 2, 50.0)])  # p2 chỉ còn 1
    assert snapshot(con) == before


def test_unknown_product(co, con):
    before = snapshot(con)
    with pytest.raises(co.OutOfStock):
        co.place_order(con, "o3", "c1", [("p1", 1, 10.0), ("zzz", 1, 1.0)])
    assert snapshot(con) == before


def test_duplicate_order_id_restores_stock(co, con):
    co.place_order(con, "o1", "c1", [("p1", 1, 10.0)])
    before = snapshot(con)
    with pytest.raises(sqlite3.IntegrityError):
        co.place_order(con, "o1", "c2", [("p1", 1, 10.0)])
    assert snapshot(con) == before


@pytest.mark.parametrize("items", [[], [("p1", 0, 10.0)], [("p1", -1, 10.0)]])
def test_invalid_input(co, con, items):
    before = snapshot(con)
    with pytest.raises(ValueError):
        co.place_order(con, "o9", "c1", items)
    assert snapshot(con) == before


def test_reserve_pg_concurrent(co):
    ex.require_service("postgres")
    import psycopg

    dsn = testkit.POSTGRES_DSN
    try:
        setup = psycopg.connect(dsn, autocommit=True)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Không kết nối được PostgreSQL bằng {dsn}: {exc}")
    with setup as conn:
        conn.execute("DROP TABLE IF EXISTS ex_stock")
        conn.execute("CREATE TABLE ex_stock (product_id TEXT PRIMARY KEY, qty INTEGER NOT NULL)")
        conn.execute("INSERT INTO ex_stock VALUES ('p1', 10)")
    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(lambda _: co.reserve_pg(dsn, "p1", 1), range(20)))
        assert results.count(True) == 10
        with psycopg.connect(dsn) as conn:
            assert conn.execute("SELECT qty FROM ex_stock WHERE product_id = 'p1'").fetchone()[0] == 0
        assert co.reserve_pg(dsn, "p1", 1) is False
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("DROP TABLE IF EXISTS ex_stock")
