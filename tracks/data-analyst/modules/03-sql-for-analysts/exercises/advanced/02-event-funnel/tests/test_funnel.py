import re
from pathlib import Path

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Bản chuẩn của loader ecommerce-events: exercises/advanced/02-event-funnel/tests/test_funnel.py.
# Bản trong starter/run_query.py chép y hệt; sửa thì sửa cả hai.
def load_events(con: duckdb.DuckDBPyConnection, folder: Path) -> None:
    """Bảng `events`: mỗi dòng một sự kiện view / addtocart / transaction của một visitor."""
    path = str(folder / "clean_events.csv").replace("'", "''")
    con.execute(f"""
        CREATE TABLE events AS
        SELECT visitorid AS visitor_id, event, itemid AS item_id,
               make_timestamp("timestamp" * 1000) AS event_time,  -- epoch mili giây -> TIMESTAMP (UTC)
               nullif(transactionid, 'NA') AS transaction_id
        FROM read_csv('{path}', header = true, types = {{'transactionid': 'VARCHAR'}})""")


def e(visitor, event, ts):
    return (visitor, event, 1, ts, "T1" if event == "transaction" else None)


SMALL = [
    e(1, "view", "2015-06-01 10:00"), e(1, "addtocart", "2015-06-01 10:05"), e(1, "transaction", "2015-06-01 10:10"),
    e(2, "addtocart", "2015-06-01 10:00"), e(2, "view", "2015-06-01 10:01"),        # giỏ trước khi xem: không tính
    e(3, "view", "2015-06-01 10:00"), e(3, "addtocart", "2015-06-01 10:20"),
    e(3, "transaction", "2015-06-02 09:00"),                                       # mua ở phiên khác
    e(4, "view", "2015-06-01 10:00"), e(4, "view", "2015-06-01 10:31"),            # cách 31 phút: phiên mới
    e(4, "addtocart", "2015-06-01 10:40"),
    e(5, "transaction", "2015-06-01 12:00"),                                       # không xem: ngoài funnel
    e(6, "view", "2015-06-01 10:00"), e(6, "addtocart", "2015-06-01 10:30"),       # cách đúng 30 phút: cùng phiên
    e(6, "transaction", "2015-06-01 11:00"),
    e(7, "view", "2015-06-01 10:00"), e(7, "transaction", "2015-06-01 10:03"),     # mua không qua giỏ
]


@pytest.fixture
def small():
    con = duckdb.connect()
    con.execute("CREATE TABLE events (visitor_id BIGINT, event VARCHAR, item_id BIGINT, event_time TIMESTAMP, "
                "transaction_id VARCHAR)")
    con.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?)", SMALL)
    yield con
    con.close()


@pytest.fixture(scope="module")
def real():
    folder = ex.dataset("ecommerce-events")
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    load_events(con, folder)
    yield con
    con.close()


def run(con, name):
    rel = con.execute(ex.read(name))
    return [d[0] for d in rel.description], rel.fetchall()


def check_funnel(rows, counts):
    assert [(int(s), ev) for s, ev, *_ in rows] == [(1, "view"), (2, "addtocart"), (3, "transaction")]
    assert [int(row[2]) for row in rows] == counts
    assert rows[0][3] is None
    assert [float(row[3]) for row in rows[1:]] == pytest.approx(
        [counts[1] / counts[0], counts[2] / counts[1]], abs=1e-4)
    assert [float(row[4]) for row in rows] == pytest.approx([1.0, counts[1] / counts[0], counts[2] / counts[0]], abs=1e-4)


def test_visitor_funnel_small(small):
    cols, rows = run(small, "visitor_funnel.sql")
    assert cols == ["step", "event", "visitors", "conv_from_prev", "conv_from_first"]
    check_funnel(rows, [6, 4, 3])


def test_session_funnel_small(small):
    cols, rows = run(small, "session_funnel.sql")
    assert cols == ["step", "event", "sessions", "conv_from_prev", "conv_from_first"]
    check_funnel(rows, [7, 4, 2])


def test_real_visitor_funnel(real):
    _, rows = run(real, "visitor_funnel.sql")
    check_funnel(rows, [1_404_179, 32_934, 9_952])


def test_real_session_funnel(real):
    _, rows = run(real, "session_funnel.sql")
    check_funnel(rows, [1_755_781, 36_677, 10_722])


MEMO_HEADINGS = ["## Trả lời ngắn", "## Funnel theo visitor", "## Funnel theo phiên", "## Nên tối ưu bước nào",
                 "## Định nghĩa và giới hạn", "## Việc cần làm"]


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 600, f"Memo ngắn: 200-600 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
    assert re.search(r"\d+([.,]\d+)?\s*%", memo), "Memo cần tỉ lệ chuyển đổi dạng phần trăm"
