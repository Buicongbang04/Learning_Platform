import datetime as dt
import sys
import uuid

import duckdb
import pytest

import testkit
from testkit import Exercise

ex = Exercise(__file__)
sys.path.insert(0, str(testkit.ROOT / "setup" / "bi"))

BI_START = (
    "docker compose -f setup/docker-compose.yml --profile bi up -d postgres metabase superset "
    "&& uv run python setup/bi/load_da.py && uv run python setup/bi/init_bi.py"
)


# ---------- Metabase giả trong bộ nhớ: chấm logic gọi API khi không bật Docker ----------

class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code, self._payload = status_code, payload
        self.ok = status_code < 400

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeMetabase:
    """Hỗ trợ đúng các endpoint đề bài cho dùng: GET /api/database, GET /api/database/<id>/metadata,
    GET/POST /api/card, PUT /api/card/<id>."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.cards = {
            5: {"id": 5, "name": "DA10 · Doanh thu theo tháng", "archived": True, "display": "bar"},
            6: {"id": 6, "name": "Câu hỏi của người khác", "archived": False, "display": "table"},
        }
        self.next_id = 100

    def _field(self, fid, name):
        return {"id": fid, "name": name}

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        if url == "/api/database":
            return FakeResponse(200, {"data": [{"id": 1, "name": "Sample Database"}, {"id": 2, "name": "de"}], "total": 2})
        if url == "/api/database/2/metadata":
            cols = ["invoice", "stockcode", "description", "quantity", "invoicedate", "price", "customer_id", "country", "revenue"]
            return FakeResponse(200, {"id": 2, "tables": [
                {"id": 7, "schema": "public", "name": "online_retail_ii", "fields": [self._field(i, c) for i, c in enumerate(cols, 200)]},
                {"id": 10, "schema": "da", "name": "bike_hour", "fields": [self._field(70, "cnt")]},
                {"id": 11, "schema": "da", "name": "online_retail_ii", "fields": [self._field(i, c) for i, c in enumerate(cols, 90)]},
            ]})
        if url == "/api/card":
            return FakeResponse(200, [dict(c) for c in self.cards.values()])
        return FakeResponse(404, {"message": f"không có endpoint {url} trong bài này"})

    def post(self, url, json=None, **kwargs):
        self.calls.append(("POST", url))
        if url == "/api/card":
            card = dict(json, id=self.next_id, archived=False)
            self.cards[self.next_id] = card
            self.next_id += 1
            return FakeResponse(200, card)
        return FakeResponse(404, {})

    def put(self, url, json=None, **kwargs):
        self.calls.append(("PUT", url))
        card_id = int(url.rsplit("/", 1)[1])
        if url.startswith("/api/card/") and card_id in self.cards:
            self.cards[card_id].update(json)
            return FakeResponse(200, self.cards[card_id])
        return FakeResponse(404, {})


@pytest.fixture
def mq():
    return ex.module("metabase_questions.py")


def test_find_table_dung_schema_da(mq):
    ids = mq.find_table(FakeMetabase())
    assert ids["database_id"] == 2
    assert ids["table_id"] == 11, "Có hai bảng online_retail_ii (public và da): phải lấy đúng schema `da`"
    assert ids["fields"]["revenue"] == 98 and ids["fields"]["country"] == 97


def tiny_db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE SCHEMA da")
    con.execute(
        "CREATE TABLE da.online_retail_ii (invoice VARCHAR, stockcode VARCHAR, description VARCHAR, quantity BIGINT, "
        "invoicedate TIMESTAMP, price DOUBLE, customer_id BIGINT, country VARCHAR, revenue DOUBLE)"
    )
    rows = [
        ("1", "A", "x", 2, "2011-01-03 10:00", 5.0, 1, "France", 10.0),
        ("1", "B", "y", 1, "2011-01-03 10:00", 20.0, 1, "France", 20.0),   # cùng hoá đơn: 1 đơn
        ("2", "A", "x", 1, "2011-01-20 11:00", 30.0, None, "United Kingdom", 30.0),  # khách vãng lai
        ("3", "A", "x", 4, "2011-02-01 00:00", 10.0, 2, "Germany", 40.0),
        ("4", "C", "z", 1, "2011-02-28 23:59", 25.5, 2, "Germany", 25.5),
    ]
    con.executemany("INSERT INTO da.online_retail_ii VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    return con


def test_monthly_card_la_sql_chay_dung(mq):
    card = mq.monthly_revenue_card(2, "Doanh thu theo tháng")
    assert card["name"] == "Doanh thu theo tháng"
    assert card["display"] == "line"
    q = card["dataset_query"]
    assert q["type"] == "native" and q["database"] == 2
    rel = tiny_db().execute(q["native"]["query"])
    cols = [d[0] for d in rel.description]
    assert cols == ["month", "revenue", "orders", "customers", "aov"]
    rows = rel.fetchall()
    assert [r[0] for r in rows] == [dt.date(2011, 1, 1), dt.date(2011, 2, 1)], "month là ngày đầu tháng, kiểu DATE, sắp tăng dần"
    jan, feb = rows
    assert float(jan[1]) == pytest.approx(60.0) and float(feb[1]) == pytest.approx(65.5)
    assert (jan[2], jan[3]) == (2, 1), "orders = số hoá đơn khác nhau; customers bỏ khách vãng lai (NULL)"
    assert (feb[2], feb[3]) == (2, 1)
    assert float(jan[4]) == pytest.approx(30.0) and float(feb[4]) == pytest.approx(32.75), "aov = revenue / orders"


def test_country_card_la_mbql(mq):
    ids = {"database_id": 2, "table_id": 11, "fields": {"revenue": 98, "country": 97, "invoice": 90}}
    card = mq.country_revenue_card(ids, "Top 10 quốc gia")
    assert card["display"] == "row"
    q = card["dataset_query"]
    assert q["type"] == "query" and q["database"] == 2, "Question query builder: type `query` (MBQL), không phải SQL"
    mbql = q["query"]
    assert mbql["source-table"] == 11
    assert mbql["aggregation"] == [["sum", ["field", 98, None]]]
    assert mbql["breakout"] == [["field", 97, None]]
    assert mbql["order-by"] == [["desc", ["aggregation", 0]]]
    assert mbql["limit"] == 10


def test_upsert_card_idempotent(mq):
    fake = FakeMetabase()
    card = mq.monthly_revenue_card(2, "DA10 · Doanh thu theo tháng")
    first = mq.upsert_card(fake, card)
    assert first not in (5, 6), "Card trùng tên đã archive không tính là có sẵn: tạo card mới"
    second = mq.upsert_card(fake, dict(card, description="sửa mô tả"))
    assert second == first, "Chạy lại không tạo thêm card trùng tên"
    live = [c for c in fake.cards.values() if c["name"] == card["name"] and not c["archived"]]
    assert len(live) == 1 and live[0]["description"] == "sửa mô tả", "Lần hai phải cập nhật (PUT) card đã có"
    assert ("PUT", f"/api/card/{first}") in fake.calls
    assert fake.cards[6]["name"] == "Câu hỏi của người khác", "Không đụng card khác"


# ---------- Metabase thật: chạy khi BI đang bật, tự skip khi tắt ----------

@pytest.fixture(scope="module")
def metabase():
    for name in ("postgres", "metabase"):
        if not testkit.service_up(name):
            pytest.skip(f"Dịch vụ {name} chưa chạy. Bật BI bằng: {BI_START}")
        ex.require_service(name)
    import clients

    try:
        return clients.metabase_session()
    except RuntimeError as e:
        pytest.skip(str(e))


@pytest.fixture(scope="module")
def run(metabase):
    """Tên riêng cho lần chạy test (không đụng question của bạn); dọn mọi card mang tên đó khi xong."""
    state = {"prefix": f"test-{uuid.uuid4().hex[:8]} · "}
    yield state
    for card in metabase.get("/api/card").json():
        if card["name"].startswith(state["prefix"]):
            metabase.delete(f"/api/card/{card['id']}")


def published(metabase, run):
    """Gọi publish hai lần (lần hai phải không tạo thêm gì). Gọi trong test để lỗi của bài là FAIL."""
    if "ids" not in run:
        mq = ex.module("metabase_questions.py")
        first = mq.publish(metabase, prefix=run["prefix"])
        run["second"] = mq.publish(metabase, prefix=run["prefix"])
        run["ids"] = first
    return run["ids"]


def run_card(metabase, card_id):
    res = metabase.post(f"/api/card/{card_id}/query", json={}).json()
    assert res.get("status") == "completed", res.get("error")
    return [c["name"] for c in res["data"]["cols"]], res["data"]["rows"]


def test_real_publish_idempotent(metabase, run):
    first = published(metabase, run)
    prefix, second = run["prefix"], run["second"]
    assert set(first) == {"monthly", "country"}
    assert first == second, "Chạy publish lần hai phải trả cùng id, không tạo thêm question"
    names = [c["name"] for c in metabase.get("/api/card").json() if c["name"].startswith(prefix)]
    assert len(names) == 2


def test_real_monthly_numbers(metabase, run):
    ids = published(metabase, run)
    cols, rows = run_card(metabase, ids["monthly"])
    assert cols == ["month", "revenue", "orders", "customers", "aov"]
    assert len(rows) == 25
    by_month = {r[0][:7]: r for r in rows}
    nov = by_month["2011-11"]
    assert float(nov[1]) == pytest.approx(1_509_496.33, abs=0.01)
    assert (nov[2], nov[3]) == (2769, 1664)
    assert float(nov[4]) == pytest.approx(545.14, abs=0.01)
    assert sum(float(r[1]) for r in rows) == pytest.approx(20_533_741.92, abs=0.1)


def test_real_country_top10(metabase, run):
    ids = published(metabase, run)
    _, rows = run_card(metabase, ids["country"])
    assert len(rows) == 10
    assert [r[0] for r in rows[:4]] == ["United Kingdom", "EIRE", "Netherlands", "Germany"]
    assert rows[0][1] == pytest.approx(17_465_896.34, abs=0.05)
