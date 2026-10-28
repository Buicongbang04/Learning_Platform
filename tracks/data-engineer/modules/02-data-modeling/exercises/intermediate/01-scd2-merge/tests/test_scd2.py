import datetime as dt

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

D1, D2, D3, D4 = (dt.date(2018, 1, 1), dt.date(2018, 2, 1), dt.date(2018, 3, 1), dt.date(2018, 4, 1))
HIGH = dt.date(9999, 12, 31)

SNAP1 = [
    {"customer_id": "c1", "city": "sao paulo", "state": "SP"},
    {"customer_id": "c2", "city": "rio de janeiro", "state": "RJ"},
    {"customer_id": "c3", "city": None, "state": "MG"},
]
SNAP2 = [
    {"customer_id": "c1", "city": "campinas", "state": "SP"},   # đổi city
    {"customer_id": "c2", "city": "rio de janeiro", "state": "RJ"},
    {"customer_id": "c3", "city": "belo horizonte", "state": "MG"},  # NULL -> giá trị
    {"customer_id": "c4", "city": "recife", "state": "PE"},     # mới
]
SNAP3 = [  # c2 bị xoá ở nguồn
    {"customer_id": "c1", "city": "campinas", "state": "SP"},
    {"customer_id": "c3", "city": "belo horizonte", "state": "MG"},
    {"customer_id": "c4", "city": "olinda", "state": "PE"},
]
SNAP4 = SNAP3 + [{"customer_id": "c2", "city": "niteroi", "state": "RJ"}]  # c2 quay lại


@pytest.fixture()
def scd2():
    return ex.module("scd2.py")


@pytest.fixture()
def con(scd2):
    con = duckdb.connect()
    scd2.create_dim_customer(con)
    yield con
    con.close()


def history(con, customer_id):
    return con.execute(
        "SELECT city, state, valid_from, valid_to, is_current FROM dim_customer "
        "WHERE customer_id = ? ORDER BY valid_from",
        [customer_id],
    ).fetchall()


def test_initial_load(scd2, con):
    assert scd2.apply_scd2(con, SNAP1, D1) == {"inserted": 3, "closed": 0}
    assert history(con, "c1") == [("sao paulo", "SP", D1, HIGH, True)]
    assert history(con, "c3") == [(None, "MG", D1, HIGH, True)]


def test_change_new_and_null(scd2, con):
    scd2.apply_scd2(con, SNAP1, D1)
    assert scd2.apply_scd2(con, SNAP2, D2) == {"inserted": 3, "closed": 2}
    assert history(con, "c1") == [
        ("sao paulo", "SP", D1, D2, False),
        ("campinas", "SP", D2, HIGH, True),
    ]
    assert history(con, "c2") == [("rio de janeiro", "RJ", D1, HIGH, True)]
    assert history(con, "c3") == [
        (None, "MG", D1, D2, False),
        ("belo horizonte", "MG", D2, HIGH, True),
    ]
    assert history(con, "c4") == [("recife", "PE", D2, HIGH, True)]


def test_idempotent_rerun(scd2, con):
    scd2.apply_scd2(con, SNAP1, D1)
    scd2.apply_scd2(con, SNAP2, D2)
    before = con.execute("SELECT * FROM dim_customer ORDER BY customer_key").fetchall()
    assert scd2.apply_scd2(con, SNAP2, D2) == {"inserted": 0, "closed": 0}
    assert con.execute("SELECT * FROM dim_customer ORDER BY customer_key").fetchall() == before


def test_deleted_and_returning_customer(scd2, con):
    scd2.apply_scd2(con, SNAP1, D1)
    scd2.apply_scd2(con, SNAP2, D2)
    assert scd2.apply_scd2(con, SNAP3, D3) == {"inserted": 1, "closed": 2}
    assert history(con, "c2") == [("rio de janeiro", "RJ", D1, D3, False)]
    assert scd2.apply_scd2(con, SNAP4, D4) == {"inserted": 1, "closed": 0}
    assert history(con, "c2")[-1] == ("niteroi", "RJ", D4, HIGH, True)


def test_invariants(scd2, con):
    for snap, day in [(SNAP1, D1), (SNAP2, D2), (SNAP3, D3), (SNAP4, D4)]:
        scd2.apply_scd2(con, snap, day)
    multi_current = con.execute(
        "SELECT customer_id FROM dim_customer WHERE is_current GROUP BY 1 HAVING COUNT(*) > 1"
    ).fetchall()
    assert multi_current == []
    overlaps = con.execute(
        """
        SELECT a.customer_key FROM dim_customer a JOIN dim_customer b
          ON a.customer_id = b.customer_id AND a.customer_key < b.customer_key
         AND a.valid_from < b.valid_to AND b.valid_from < a.valid_to
        """
    ).fetchall()
    assert overlaps == []
    keys = [r[0] for r in con.execute("SELECT customer_key FROM dim_customer").fetchall()]
    assert len(keys) == len(set(keys))


def test_lookup_customer_key(scd2, con):
    scd2.apply_scd2(con, SNAP1, D1)
    scd2.apply_scd2(con, SNAP2, D2)
    scd2.apply_scd2(con, SNAP3, D3)
    rows = dict(
        ((cid, vf), key)
        for key, cid, vf in con.execute("SELECT customer_key, customer_id, valid_from FROM dim_customer").fetchall()
    )
    assert scd2.lookup_customer_key(con, "c1", dt.date(2018, 1, 15)) == rows[("c1", D1)]
    assert scd2.lookup_customer_key(con, "c1", D2) == rows[("c1", D2)]          # biên: thuộc phiên bản mới
    assert scd2.lookup_customer_key(con, "c1", dt.date(2018, 1, 31)) == rows[("c1", D1)]
    assert scd2.lookup_customer_key(con, "c2", dt.date(2018, 2, 28)) == rows[("c2", D1)]
    assert scd2.lookup_customer_key(con, "c2", D3) is None                     # đã bị xoá
    assert scd2.lookup_customer_key(con, "c1", dt.date(2017, 12, 31)) is None  # trước khi tồn tại
    assert scd2.lookup_customer_key(con, "zzz", D2) is None
