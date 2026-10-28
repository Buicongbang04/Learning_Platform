import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def mod():
    return ex.module("serving.py")


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE agg_daily_sales (order_date DATE, customer_state VARCHAR, orders BIGINT, revenue DOUBLE);
        INSERT INTO agg_daily_sales VALUES
            ('2018-08-01', 'SP', 2, 250.0), ('2018-08-01', 'RJ', 1, 80.0),
            ('2018-08-02', 'SP', 1, 30.0),  ('2018-08-02', 'RJ', 1, 400.0),
            ('2018-08-03', 'RJ', 1, 50.0),  ('2018-08-04', 'MG', 3, 120.0),
            ('2018-08-05', 'SP', 4, 610.5), ('2018-09-01', 'SP', 1, 99.9);
    """)
    yield con
    con.close()


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def service(mod, con, clock):
    return mod.MetricsService(con, mod.TTLCache(ttl=60, clock=clock))


def test_ttl_cache(mod, clock):
    cache = mod.TTLCache(ttl=10, clock=clock)
    assert cache.get("k") is None
    cache.set("k", 1)
    clock.now = 9.9
    assert cache.get("k") == 1
    clock.now = 10.1
    assert cache.get("k", "gone") == "gone"
    assert (cache.hits, cache.misses) == (1, 2)


def test_query_and_pagination(service):
    page = service.get_daily_sales(start="2018-08-01", end="2018-08-31", limit=3, offset=0)
    assert page["total"] == 7
    assert (page["limit"], page["offset"], page["data_version"]) == (3, 0, "v1")
    assert page["data"] == [
        {"order_date": "2018-08-01", "customer_state": "RJ", "orders": 1, "revenue": 80.0},
        {"order_date": "2018-08-01", "customer_state": "SP", "orders": 2, "revenue": 250.0},
        {"order_date": "2018-08-02", "customer_state": "RJ", "orders": 1, "revenue": 400.0},
    ]
    last = service.get_daily_sales(start="2018-08-01", end="2018-08-31", limit=3, offset=6)
    assert [r["order_date"] for r in last["data"]] == ["2018-08-05"]


def test_state_filter_normalized(service):
    page = service.get_daily_sales(state="sp", start="2018-08-01", end="2018-09-30")
    assert page["total"] == 4
    assert {r["customer_state"] for r in page["data"]} == {"SP"}


def test_cache_hit_and_version_invalidation(mod, con, clock):
    version = {"v": "2018-09-01T02:00"}
    svc = mod.MetricsService(con, mod.TTLCache(ttl=60, clock=clock), data_version=lambda: version["v"])
    a = svc.get_daily_sales(state="SP", start="2018-08-01", end="2018-08-31")
    b = svc.get_daily_sales(state="sp", start="2018-08-01", end="2018-08-31")  # cùng key sau chuẩn hoá
    assert a == b
    assert svc.queries_executed == 1
    con.execute("UPDATE agg_daily_sales SET revenue = 999 WHERE customer_state = 'SP'")
    version["v"] = "2018-09-01T03:00"
    c = svc.get_daily_sales(state="SP", start="2018-08-01", end="2018-08-31")
    assert svc.queries_executed == 2
    assert c["data_version"] == "2018-09-01T03:00"
    assert {r["revenue"] for r in c["data"]} == {999.0}


def test_cache_ttl_expiry(service, clock):
    service.get_daily_sales(start="2018-08-01", end="2018-08-02")
    clock.now = 30
    service.get_daily_sales(start="2018-08-01", end="2018-08-02")
    assert service.queries_executed == 1
    clock.now = 61
    service.get_daily_sales(start="2018-08-01", end="2018-08-02")
    assert service.queries_executed == 2


@pytest.mark.parametrize("kwargs", [
    {"start": "2018-08-01"},
    {"start": "2018-08-31", "end": "2018-08-01"},
    {"start": "2018/08/01", "end": "2018-08-31"},
    {"start": "2017-01-01", "end": "2018-08-31"},
    {"state": "SP' OR '1'='1", "start": "2018-08-01", "end": "2018-08-31"},
    {"state": "SPX", "start": "2018-08-01", "end": "2018-08-31"},
    {"start": "2018-08-01", "end": "2018-08-31", "limit": 0},
    {"start": "2018-08-01", "end": "2018-08-31", "limit": 501},
    {"start": "2018-08-01", "end": "2018-08-31", "offset": -1},
    {"start": "2018-08-01", "end": "2018-08-31", "limit": True},
])
def test_validation(mod, service, kwargs):
    with pytest.raises(mod.ValidationError):
        service.get_daily_sales(**kwargs)
    assert service.queries_executed == 0


def test_handle_request(mod, service):
    status, body = mod.handle_request(service, {"state": "RJ", "start": "2018-08-01", "end": "2018-08-31",
                                                "limit": "2", "offset": "1"})
    assert status == 200
    assert body["total"] == 3
    assert [r["order_date"] for r in body["data"]] == ["2018-08-02", "2018-08-03"]

    status, body = mod.handle_request(service, {"start": "2018-08-01", "end": "2018-08-31", "limit": "abc"})
    assert status == 400 and "error" in body
    status, body = mod.handle_request(service, {"start": "2018-08-31", "end": "2018-08-01"})
    assert status == 400 and "error" in body
