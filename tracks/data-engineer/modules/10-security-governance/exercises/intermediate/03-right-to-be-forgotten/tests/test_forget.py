import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)
KEY = b"erasure-test-key"


@pytest.fixture(scope="module")
def fg():
    return ex.module("forget.py")


@pytest.fixture()
def con(fg):
    c = duckdb.connect()
    c.execute("""CREATE TABLE customers AS SELECT * FROM (VALUES
        ('c1', 'U1', 'ana@gmail.com', '0912345678', 'SP'),
        ('c2', 'U1', 'ana@gmail.com', '0912345678', 'SP'),
        ('c3', 'U2', 'joao@uol.com.br', '0987654321', 'RJ')
    ) t(customer_id, customer_unique_id, email, phone, customer_state)""")
    c.execute("""CREATE TABLE orders AS SELECT * FROM (VALUES
        ('o1', 'c1', 'delivered', TIMESTAMP '2018-01-01 10:00'),
        ('o2', 'c2', 'delivered', TIMESTAMP '2018-02-01 10:00'),
        ('o3', 'c3', 'shipped',   TIMESTAMP '2018-03-01 10:00')
    ) t(order_id, customer_id, order_status, order_purchase_timestamp)""")
    c.execute("""CREATE TABLE reviews AS SELECT * FROM (VALUES
        ('r1', 'o1', 5, 'otimo, liga 0912345678'),
        ('r2', 'o2', 4, 'bom'),
        ('r3', 'o3', 1, 'atrasou')
    ) t(review_id, order_id, review_score, review_comment_message)""")
    fg.ensure_tables(c)
    fg.store_pii(c, "U1", {"cpf": "529.982.247-25", "address": "Rua A, 10"})
    fg.store_pii(c, "U2", {"cpf": "123.456.789-09", "address": "Rua B, 20"})
    yield c
    c.close()


def test_subject_hash(fg):
    h = fg.subject_hash("U1", KEY)
    assert len(h) == 64 and h == fg.subject_hash("U1", KEY) and h != fg.subject_hash("U1", b"k2")


def test_find_customer_ids(fg, con):
    assert fg.find_customer_ids(con, "U1") == ["c1", "c2"]
    assert fg.find_customer_ids(con, "nobody") == []


def test_erase(fg, con):
    result = fg.erase_customer(con, "req-001", "U1", KEY)
    assert result == {"customers": 2, "orders": 2, "reviews": 2, "user_keys": 1}

    assert con.execute("SELECT customer_unique_id FROM customers").fetchall() == [("U2",)]
    orders = dict(con.execute("SELECT order_id, customer_id FROM orders").fetchall())
    assert len(orders) == 3 and orders["o3"] == "c3"
    assert orders["o1"].startswith("anon_") and orders["o2"].startswith("anon_")
    assert orders["o1"] != orders["o2"]
    assert len(orders["o1"]) == len("anon_") + 32
    assert fg.subject_hash("c1", KEY)[:16] not in orders["o1"]

    reviews = dict(con.execute("SELECT review_id, review_comment_message FROM reviews").fetchall())
    assert reviews == {"r1": None, "r2": None, "r3": "atrasou"}
    assert con.execute("SELECT sum(review_score) FROM reviews").fetchone()[0] == 10

    # crypto-shredding: payload vẫn còn trong "backup" nhưng không đọc được
    assert con.execute("SELECT count(*) FROM pii_vault WHERE customer_unique_id = 'U1'").fetchone()[0] == 1
    assert fg.read_vault(con, "U1") is None
    assert fg.read_vault(con, "U2")["cpf"] == "123.456.789-09"
    assert fg.verify_erased(con, "U1") == []
    assert fg.verify_erased(con, "U2") != []


def test_audit_log_has_no_pii(fg, con):
    fg.erase_customer(con, "req-001", "U1", KEY)
    rows = con.execute("SELECT request_id, subject_hash, table_name, rows_affected FROM erasure_log").fetchall()
    assert len(rows) == 4
    assert {r[2] for r in rows} == {"customers", "orders", "reviews", "user_keys"}
    assert {r[1] for r in rows} == {fg.subject_hash("U1", KEY)}
    dump = repr(con.execute("SELECT * FROM erasure_log").fetchall())
    for raw in ["U1", "c1", "c2", "ana@gmail.com", "0912345678"]:
        assert raw not in dump.replace(fg.subject_hash("U1", KEY), "")


def test_idempotent(fg, con):
    first = fg.erase_customer(con, "req-001", "U1", KEY)
    orders_after_first = con.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
    second = fg.erase_customer(con, "req-001", "U1", KEY)
    assert second == first
    assert con.execute("SELECT count(*) FROM erasure_log").fetchone()[0] == 4
    assert con.execute("SELECT * FROM orders ORDER BY order_id").fetchall() == orders_after_first


def test_atomic_on_failure(fg, con):
    con.execute("DROP TABLE reviews")
    with pytest.raises(Exception):
        fg.erase_customer(con, "req-002", "U1", KEY)
    assert con.execute("SELECT count(*) FROM customers WHERE customer_unique_id = 'U1'").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM orders WHERE customer_id IN ('c1','c2')").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM erasure_log").fetchone()[0] == 0
    assert fg.read_vault(con, "U1") is not None
