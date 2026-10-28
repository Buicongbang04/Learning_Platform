import datetime as dt

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

DAY1 = [
    {"seller_id": "s1", "city": "campinas", "state": "SP"},
    {"seller_id": "s2", "city": "curitiba", "state": "PR"},
]
DAY2 = [
    {"seller_id": "s1", "city": "rio de janeiro", "state": "RJ"},  # đổi
    {"seller_id": "s2", "city": "curitiba", "state": "PR"},        # giữ nguyên
    {"seller_id": "s3", "city": "salvador", "state": "BA"},        # mới
]
DAY3 = [
    {"seller_id": "s1", "city": "niteroi", "state": "RJ"},         # đổi city, không đổi bang
    {"seller_id": "s2", "city": "florianopolis", "state": "SC"},   # đổi bang
]


@pytest.fixture()
def scd():
    return ex.module("scd.py")


@pytest.fixture()
def con(scd):
    con = duckdb.connect()
    scd.create_tables(con)
    yield con
    con.close()


def table(con, name):
    return con.execute(f"SELECT * FROM {name} ORDER BY 1").fetchall()


def test_scd1_insert_then_overwrite(scd, con):
    scd.apply_scd1(con, DAY1)
    assert table(con, "dim_seller") == [("s1", "campinas", "SP"), ("s2", "curitiba", "PR")]
    scd.apply_scd1(con, DAY2)
    assert table(con, "dim_seller") == [
        ("s1", "rio de janeiro", "RJ"),
        ("s2", "curitiba", "PR"),
        ("s3", "salvador", "BA"),
    ]


def test_scd1_idempotent(scd, con):
    scd.apply_scd1(con, DAY2)
    scd.apply_scd1(con, DAY2)
    assert len(table(con, "dim_seller")) == 3


def test_scd1_missing_seller_kept(scd, con):
    scd.apply_scd1(con, DAY2)
    scd.apply_scd1(con, DAY3)
    assert table(con, "dim_seller") == [
        ("s1", "niteroi", "RJ"),
        ("s2", "florianopolis", "SC"),
        ("s3", "salvador", "BA"),
    ]


def test_scd3_tracks_previous_state(scd, con):
    d1, d2, d3 = dt.date(2018, 1, 1), dt.date(2018, 2, 1), dt.date(2018, 3, 1)
    scd.apply_scd3(con, DAY1, d1)
    assert table(con, "dim_seller_scd3") == [("s1", "SP", None, None), ("s2", "PR", None, None)]
    scd.apply_scd3(con, DAY2, d2)
    assert table(con, "dim_seller_scd3") == [
        ("s1", "RJ", "SP", d2),
        ("s2", "PR", None, None),
        ("s3", "BA", None, None),
    ]
    scd.apply_scd3(con, DAY3, d3)
    assert table(con, "dim_seller_scd3") == [
        ("s1", "RJ", "SP", d2),       # chỉ đổi city: không phải thay đổi bang
        ("s2", "SC", "PR", d3),
        ("s3", "BA", None, None),
    ]


def test_scd3_idempotent(scd, con):
    d1, d2 = dt.date(2018, 1, 1), dt.date(2018, 2, 1)
    scd.apply_scd3(con, DAY1, d1)
    scd.apply_scd3(con, DAY2, d2)
    before = table(con, "dim_seller_scd3")
    scd.apply_scd3(con, DAY2, dt.date(2018, 2, 15))
    assert table(con, "dim_seller_scd3") == before
