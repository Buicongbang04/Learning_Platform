import sqlite3
from datetime import datetime

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

SEED = [
    ("o1", "c1", "created", "2018-01-01 10:00:00"),
    ("o2", "c2", "created", "2018-01-01 11:00:00"),
    ("o3", "c3", "created", "2018-01-01 12:00:00"),
]


@pytest.fixture
def env(tmp_path):
    src_path = str(tmp_path / "oltp.sqlite")
    src = sqlite3.connect(src_path)
    src.execute(
        "CREATE TABLE orders (order_id TEXT PRIMARY KEY, customer_id TEXT, order_status TEXT, updated_at TEXT)"
    )
    src.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", SEED)
    src.commit()
    yield src, src_path, str(tmp_path / "wh.duckdb")
    src.close()


def target(dst_path):
    con = duckdb.connect(dst_path)
    try:
        rows = con.execute("SELECT order_id, order_status FROM stg_orders ORDER BY order_id").fetchall()
        wm = con.execute("SELECT watermark FROM etl_state WHERE source = 'orders'").fetchone()
        return dict(rows), (wm[0] if wm else None)
    finally:
        con.close()


def test_extract_since_respects_watermark_and_lookback(env):
    m = ex.module("incremental.py")
    src, _, _ = env
    assert [r[0] for r in m.extract_since(src, None)] == ["o1", "o2", "o3"]
    wm = datetime(2018, 1, 1, 12, 0, 0)
    assert m.extract_since(src, wm, lookback_minutes=0) == []
    assert [r[0] for r in m.extract_since(src, wm, lookback_minutes=90)] == ["o2", "o3"]


def test_first_run_loads_everything(env):
    m = ex.module("incremental.py")
    _, src_path, dst = env
    out = m.run_incremental(src_path, dst)
    assert out["extracted"] == 3
    assert out["watermark"] == datetime(2018, 1, 1, 12, 0, 0)
    rows, wm = target(dst)
    assert rows == {"o1": "created", "o2": "created", "o3": "created"}
    assert wm == datetime(2018, 1, 1, 12, 0, 0)


def test_second_run_only_new_and_updated(env):
    m = ex.module("incremental.py")
    src, src_path, dst = env
    m.run_incremental(src_path, dst)
    src.execute("UPDATE orders SET order_status='delivered', updated_at='2018-01-02 08:00:00' WHERE order_id='o1'")
    src.execute("INSERT INTO orders VALUES ('o4', 'c4', 'created', '2018-01-02 09:00:00')")
    src.commit()
    out = m.run_incremental(src_path, dst, lookback_minutes=10)
    # o1 cập nhật + o4 mới + o3 (updated_at = watermark, nằm trong cửa sổ lookback, upsert nên không trùng)
    assert out["extracted"] == 3
    rows, wm = target(dst)
    assert rows == {"o1": "delivered", "o2": "created", "o3": "created", "o4": "created"}
    assert wm == datetime(2018, 1, 2, 9, 0, 0)


def test_rerun_is_idempotent_and_lookback_catches_late_rows(env):
    m = ex.module("incremental.py")
    src, src_path, dst = env
    m.run_incremental(src_path, dst)
    # Dòng đến muộn: commit sau lần chạy trước nhưng updated_at nhỏ hơn watermark 5 phút
    src.execute("INSERT INTO orders VALUES ('o9', 'c9', 'created', '2018-01-01 11:55:00')")
    src.commit()
    m.run_incremental(src_path, dst, lookback_minutes=10)
    m.run_incremental(src_path, dst, lookback_minutes=10)
    rows, wm = target(dst)
    assert set(rows) == {"o1", "o2", "o3", "o9"}
    assert wm == datetime(2018, 1, 1, 12, 0, 0)  # watermark không lùi


def test_upsert_never_overwrites_with_older_version(env):
    m = ex.module("incremental.py")
    _, src_path, dst = env
    m.run_incremental(src_path, dst)
    con = duckdb.connect(dst)
    try:
        m.upsert(con, [("o2", "c2", "delivered", "2018-01-03 00:00:00")])
        m.upsert(con, [("o2", "c2", "approved", "2018-01-02 00:00:00")])  # bản cũ hơn đến sau
        status = con.execute("SELECT order_status FROM stg_orders WHERE order_id='o2'").fetchone()[0]
        assert status == "delivered"
        assert con.execute("SELECT count(*) FROM stg_orders").fetchone()[0] == 3
    finally:
        con.close()


def test_failed_load_does_not_advance_watermark(env, monkeypatch):
    m = ex.module("incremental.py")
    src, src_path, dst = env
    m.run_incremental(src_path, dst)
    src.execute("INSERT INTO orders VALUES ('o5', 'c5', 'created', '2018-01-05 00:00:00')")
    src.commit()

    def boom(con, rows):
        raise RuntimeError("warehouse down")

    monkeypatch.setattr(m, "upsert", boom)
    with pytest.raises(RuntimeError):
        m.run_incremental(src_path, dst)
    rows, wm = target(dst)
    assert "o5" not in rows
    assert wm == datetime(2018, 1, 1, 12, 0, 0)
    monkeypatch.undo()
    m.run_incremental(src_path, dst)
    rows, wm = target(dst)
    assert "o5" in rows and wm == datetime(2018, 1, 5)
