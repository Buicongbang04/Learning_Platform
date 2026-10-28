import csv
import logging
import sqlite3
from datetime import datetime

import pytest

from testkit import Exercise

ex = Exercise(__file__)

HEADER = "order_id,customer_id,order_status,order_purchase_timestamp,extra\n"
DAY1 = HEADER + (
    "o1,c1,delivered,2018-01-02 10:00:00,x\n"
    "o2,c2,shipped,2018-01-03 09:30:00,x\n"
    ",c3,delivered,2018-01-04 08:00:00,x\n"          # thiếu order_id
    "o4,c4,lost,2018-01-05 08:00:00,x\n"             # status sai
    "o5,c5,invoiced,05/01/2018 08:00,x\n"            # timestamp sai định dạng
    "o6,c6,canceled,2018-01-06 11:00:00,x\n"
    "o7,,created,2018-01-07 11:00:00,x\n"            # thiếu customer_id
    "o8,c8,approved,2018-01-08 12:00:00,x\n"
    "o2,c2,delivered,2018-01-03 09:30:00,x\n"        # o2 lặp, bản sau thắng
)
DAY2 = HEADER + (
    "o1,c1,delivered,2018-01-02 10:00:00,y\n"
    "o8,c8,canceled,2018-01-08 12:00:00,y\n"
    "o9,c9,processing,2018-01-09 12:00:00,y\n"
)


@pytest.fixture(scope="module")
def ingest():
    return ex.module("ingest.py")


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def db_rows(db):
    with sqlite3.connect(db) as conn:
        return dict(conn.execute("SELECT order_id, order_status FROM orders").fetchall())


def test_validate_ok(ingest):
    order = ingest.validate(
        {"order_id": " o1 ", "customer_id": "c1", "order_status": "delivered",
         "order_purchase_timestamp": "2018-01-02 10:00:00"}
    )
    assert order.order_id == "o1"
    assert order.order_status == "delivered"
    assert order.order_purchase_timestamp == datetime(2018, 1, 2, 10, 0, 0)


@pytest.mark.parametrize(
    "patch",
    [
        {"order_id": ""},
        {"customer_id": "  "},
        {"order_status": "lost"},
        {"order_purchase_timestamp": "2018-01-02"},
        {"order_purchase_timestamp": "2018-13-02 10:00:00"},
    ],
)
def test_validate_rejects(ingest, patch):
    row = {"order_id": "o1", "customer_id": "c1", "order_status": "delivered",
           "order_purchase_timestamp": "2018-01-02 10:00:00", **patch}
    with pytest.raises(ValueError):
        ingest.validate(row)


def test_upsert_is_idempotent(ingest):
    conn = sqlite3.connect(":memory:")
    ingest.ensure_schema(conn)
    ingest.ensure_schema(conn)  # gọi lại không lỗi
    o = ingest.Order("o1", "c1", "shipped", datetime(2018, 1, 1, 0, 0, 0))
    assert ingest.upsert(conn, [o]) == 1
    assert ingest.upsert(conn, [o]) == 1
    o2 = ingest.Order("o1", "c1", "delivered", datetime(2018, 1, 1, 0, 0, 0))
    ingest.upsert(conn, [o2])
    assert conn.execute("SELECT COUNT(*), MAX(order_status), MAX(order_purchase_timestamp) FROM orders").fetchone() == (
        1, "delivered", "2018-01-01 00:00:00"
    )
    pk = [r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall() if r[5]]
    assert pk == ["order_id"]


def test_main_loads_and_rejects(ingest, tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="ingest")
    src = write(tmp_path, "orders.csv", DAY1)
    db = tmp_path / "olist.db"
    rejects = tmp_path / "rejects.csv"
    code = ingest.main([str(src), "--db", str(db), "--rejects", str(rejects), "--batch-size", "2"])
    assert code == 0
    assert db_rows(db) == {"o1": "delivered", "o2": "delivered", "o6": "canceled", "o8": "approved"}

    with open(rejects, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["order_id", "customer_id", "order_status",
                                     "order_purchase_timestamp", "extra", "reason"]
        bad = list(reader)
    assert [r["order_id"] for r in bad] == ["", "o4", "o5", "o7"]
    assert all(r["reason"] for r in bad)

    warnings = [r for r in caplog.records if r.name == "ingest" and r.levelno == logging.WARNING]
    assert len(warnings) == 4
    infos = [r.getMessage() for r in caplog.records if r.name == "ingest" and r.levelno == logging.INFO]
    assert any("loaded=5 rejected=4" in m for m in infos), infos


def test_main_rerun_and_update(ingest, tmp_path):
    db = tmp_path / "olist.db"
    day1 = write(tmp_path, "day1.csv", DAY1)
    day2 = write(tmp_path, "day2.csv", DAY2)
    assert ingest.main([str(day1), "--db", str(db)]) == 0
    assert ingest.main([str(day1), "--db", str(db)]) == 0
    assert len(db_rows(db)) == 4
    assert (tmp_path / "day1.csv.rejects.csv").exists()   # đường dẫn reject mặc định
    assert ingest.main([str(day2), "--db", str(db)]) == 0
    assert db_rows(db) == {"o1": "delivered", "o2": "delivered", "o6": "canceled",
                           "o8": "canceled", "o9": "processing"}


def test_main_missing_file(ingest, tmp_path, caplog):
    db = tmp_path / "olist.db"
    assert ingest.main([str(tmp_path / "nope.csv"), "--db", str(db)]) == 1
    assert not db.exists()
    assert any(r.levelno == logging.ERROR for r in caplog.records if r.name == "ingest")


def test_main_missing_column(ingest, tmp_path):
    src = write(tmp_path, "bad.csv", "order_id,customer_id\no1,c1\n")
    assert ingest.main([str(src), "--db", str(tmp_path / "x.db")]) == 1
