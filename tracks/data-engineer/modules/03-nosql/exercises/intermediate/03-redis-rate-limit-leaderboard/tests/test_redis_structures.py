import fakeredis
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Sáu request quanh ranh giới cửa sổ 60s tại 1_000_080: ba trước, ba sau (giá trị biểu diễn chính xác bằng float)
OFFSETS = [-0.75, -0.5, -0.25, 0.0, 0.25, 0.5]


@pytest.fixture
def r():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def lim():
    return ex.module("limiter.py")


def test_fixed_window(r, lim):
    t0 = 1_000_020.0  # cửa sổ 60s: [1_000_020, 1_000_080)
    results = [lim.fixed_window_allow(r, "api-1", 3, 60, t0 + i) for i in range(5)]
    assert results == [True, True, True, False, False]
    assert lim.fixed_window_allow(r, "api-2", 3, 60, t0) is True  # client khác không ảnh hưởng
    assert lim.fixed_window_allow(r, "api-1", 3, 60, t0 + 60) is True  # cửa sổ mới
    key = f"rl:fixed:api-1:{int(t0 // 60)}"
    assert r.get(key) == "5"
    assert 0 < r.ttl(key) <= 60


def test_fixed_window_boundary_leak(r, lim):
    # 3 request cuối cửa sổ + 3 request đầu cửa sổ sau: fixed window cho qua cả 6 trong 2 giây
    edge = 1_000_080.0
    allowed = [lim.fixed_window_allow(r, "burst", 3, 60, edge + off) for off in OFFSETS]
    assert allowed == [True] * 6


def test_sliding_window(r, lim):
    edge = 1_000_080.0
    allowed = [
        lim.sliding_window_allow(r, "burst", 3, 60, edge + off, f"req-{i}") for i, off in enumerate(OFFSETS)
    ]
    assert allowed == [True, True, True, False, False, False]
    assert r.zcard("rl:sliding:burst") == 3  # request bị từ chối không chiếm chỗ
    assert 0 < r.ttl("rl:sliding:burst") <= 60
    # 60 giây sau request đầu tiên, nó rời cửa sổ -> có chỗ cho một request
    assert lim.sliding_window_allow(r, "burst", 3, 60, edge - 0.75 + 60, "req-late") is True
    assert lim.sliding_window_allow(r, "burst", 3, 60, edge - 0.75 + 60.125, "req-late-2") is False


def test_leaderboard(r, lim):
    for product, qty in [("p1", 2), ("p2", 5), ("p3", 1), ("p1", 4), ("p4", 3)]:
        lim.record_sale(r, product, qty, "2018-05-01")
    assert lim.top_sellers(r, "2018-05-01", 3) == [("p1", 6), ("p2", 5), ("p4", 3)]
    assert all(isinstance(q, int) for _, q in lim.top_sellers(r, "2018-05-01"))
    assert 7 * 86_400 < r.ttl("top:2018-05-01") <= 8 * 86_400
    assert lim.top_sellers(r, "1999-01-01") == []


def test_leaderboard_over_days(r, lim):
    lim.record_sale(r, "p1", 6, "2018-05-01")
    lim.record_sale(r, "p2", 5, "2018-05-01")
    lim.record_sale(r, "p2", 4, "2018-05-02")
    lim.record_sale(r, "p3", 3, "2018-05-02")
    lim.record_sale(r, "p1", 1, "2018-05-03")
    before = set(r.keys("*"))
    result = lim.top_sellers_over(r, ["2018-05-01", "2018-05-02", "2018-05-03"], 2)
    assert result == [("p2", 9), ("p1", 7)]
    assert set(r.keys("*")) == before, "Không được để lại key tạm"


def test_unique_visitors(r, lim):
    for day, visitor in [("d1", "a"), ("d1", "b"), ("d1", "a"), ("d2", "b"), ("d2", "c"), ("d3", "d")]:
        lim.track_visit(r, day, visitor)
    assert lim.count_visitors(r, ["d1"]) == 2
    assert lim.count_visitors(r, ["d1", "d2"]) == 3
    assert lim.count_visitors(r, ["d1", "d2", "d3"]) == 4
