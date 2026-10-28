import copy
import sqlite3
from decimal import Decimal

import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.mark.parametrize("value", ["", "abc", "-0.01", "NaN", "Infinity", "1,50", None])
def test_invalid_price(value):
    with pytest.raises(ValueError):
        ex.module("basics.py").parse_price(value)


def test_exact_money():
    m = ex.module("basics.py")
    assert m.parse_price(" 0.10 ") + m.parse_price("0.20") == Decimal("0.30")
    assert m.parse_price("0") == Decimal("0")


def test_rejects_bad_rows_and_duplicate_without_mutation():
    rows = [
        {"order_id": "o1", "price": "bad"},
        {"order_id": " o1 ", "price": "10.50"},
        {"order_id": "o1", "price": "20"},
        {"order_id": "", "price": "1"},
        {"order_id": "o2", "price": "-1"},
        {"order_id": "o3", "price": "0"},
        {"order_id": "o4"},
    ]
    before = copy.deepcopy(rows)
    valid, rejected = ex.module("basics.py").clean_orders(rows)
    assert valid == [("o1", Decimal("10.50")), ("o3", Decimal("0"))]
    assert [r[0] for r in rejected] == [1, 3, 4, 5, 7]
    assert all(isinstance(reason, str) and reason for _, reason in rejected)
    assert rows == before


def test_empty_input():
    assert ex.module("basics.py").clean_orders([]) == ([], [])


def test_sql_keeps_customer_without_orders():
    con = sqlite3.connect(":memory:")
    try:
        con.executescript("""
            CREATE TABLE customers(customer_id TEXT PRIMARY KEY);
            CREATE TABLE orders(order_id TEXT PRIMARY KEY, customer_id TEXT, amount_cents INTEGER);
            INSERT INTO customers VALUES ('c2'), ('c1'), ('c3');
            INSERT INTO orders VALUES ('o1', 'c1', 1050), ('o2', 'c1', 250), ('o3', 'c3', 0);
        """)
        assert ex.module("basics.py").customer_totals(con) == [
            ("c1", 2, 1300), ("c2", 0, 0), ("c3", 1, 0)
        ]
    finally:
        con.close()
