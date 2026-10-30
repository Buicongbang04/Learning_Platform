import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Bảng giá GIẢ ĐỊNH (USD/MTok), chỉ để test; giá thật xem mục 5 lý thuyết (có ngày kiểm).
BIG = {"input": 4.0, "output": 20.0, "cached_input": 0.2}
SMALL = {
    "input": 0.1, "output": 0.5, "cached_input": 0.01,
    "long_context": {"threshold": 100_000, "input": 0.5, "output": 2.5, "cached_input": 0.05},
}
NO_CACHE_PRICE = {"input": 1.0, "output": 5.0}


@pytest.fixture(scope="module")
def cost():
    return ex.module("cost.py")


# ---------- request_cost ----------


def test_request_cost_basic(cost):
    # 2 000 token input, 500 token output: (2000 * 4 + 500 * 20) / 1e6
    assert cost.request_cost(2000, 500, BIG) == pytest.approx(0.018, abs=1e-12)
    assert cost.request_cost(0, 0, BIG) == 0.0
    # output đắt gấp 5 lần input: 1 token output bằng 5 token input
    assert cost.request_cost(0, 1000, BIG) == pytest.approx(cost.request_cost(5000, 0, BIG), abs=1e-15)


def test_request_cost_cached_is_part_of_input(cost):
    # 2 000 token input, trong đó 1 500 token đọc từ cache: 500 * 4 + 1500 * 0.2 + 500 * 20
    assert cost.request_cost(2000, 500, BIG, n_cached=1500) == pytest.approx(0.0123, abs=1e-12)
    # mọi token input đều từ cache
    assert cost.request_cost(2000, 0, BIG, n_cached=2000) == pytest.approx(0.0004, abs=1e-12)


def test_request_cost_cached_without_cached_rate(cost):
    # bảng giá không có cached_input: token cache tính như input thường
    assert cost.request_cost(1000, 100, NO_CACHE_PRICE, n_cached=800) == pytest.approx(
        cost.request_cost(1000, 100, NO_CACHE_PRICE), abs=1e-15
    )


def test_request_cost_long_context_whole_request(cost):
    # đúng bằng ngưỡng: vẫn giá thường
    assert cost.request_cost(100_000, 1000, SMALL) == pytest.approx((100_000 * 0.1 + 1000 * 0.5) / 1e6, abs=1e-12)
    # vượt ngưỡng 1 token: CẢ request tính giá dài, không chỉ phần vượt
    assert cost.request_cost(100_001, 1000, SMALL) == pytest.approx((100_001 * 0.5 + 1000 * 2.5) / 1e6, abs=1e-12)
    # cache trong request dài dùng cached_input của bảng giá dài
    assert cost.request_cost(150_000, 0, SMALL, n_cached=100_000) == pytest.approx(
        (50_000 * 0.5 + 100_000 * 0.05) / 1e6, abs=1e-12
    )


def test_request_cost_rejects_bad_input(cost):
    with pytest.raises(ValueError):
        cost.request_cost(-1, 10, BIG)
    with pytest.raises(ValueError):
        cost.request_cost(10, -1, BIG)
    with pytest.raises(ValueError):
        cost.request_cost(100, 10, BIG, n_cached=101)


# ---------- monthly_cost ----------


def test_monthly_cost(cost):
    # 10 000 request/ngày × 30 ngày × 0.018 USD
    assert cost.monthly_cost(10_000, 2000, 500, BIG) == pytest.approx(5400.0, rel=1e-12)
    assert cost.monthly_cost(10_000, 2000, 500, BIG, days=7) == pytest.approx(1260.0, rel=1e-12)


def test_monthly_cost_cache_hit(cost):
    # 80% token input từ cache: mỗi request 400 * 4 + 1600 * 0.2 + 500 * 20 = 11 920 micro-USD
    assert cost.monthly_cost(10_000, 2000, 500, BIG, cache_hit=0.8) == pytest.approx(3576.0, rel=1e-12)
    # cache_hit không cần ra số token nguyên: 1 001 * 0.5 = 500.5 token cache
    assert cost.monthly_cost(1, 1001, 0, BIG, cache_hit=0.5, days=1) == pytest.approx(
        (500.5 * 4 + 500.5 * 0.2) / 1e6, rel=1e-12
    )
    with pytest.raises(ValueError):
        cost.monthly_cost(10, 100, 10, BIG, cache_hit=1.5)


def test_monthly_cost_long_context(cost):
    # mỗi request 120 000 token: toàn bộ ở bảng giá dài
    assert cost.monthly_cost(100, 120_000, 1000, SMALL) == pytest.approx(
        100 * 30 * (120_000 * 0.5 + 1000 * 2.5) / 1e6, rel=1e-12
    )


# ---------- self_hosted_cost_per_mtok ----------


def test_self_hosted(cost):
    # 1 USD/giờ, 1 000 token/giây, bận 100%: 3.6 triệu token mỗi giờ
    assert cost.self_hosted_cost_per_mtok(1.0, 1000) == pytest.approx(1 / 3.6, rel=1e-12)
    # bận 30% và 5%: số trong mục 5 lý thuyết
    assert cost.self_hosted_cost_per_mtok(1.0, 1000, 0.3) == pytest.approx(0.9259259, rel=1e-6)
    assert cost.self_hosted_cost_per_mtok(1.0, 1000, 0.05) == pytest.approx(5.5555556, rel=1e-6)
    # GPU đắt gấp đôi, nhanh gấp đôi: như cũ
    assert cost.self_hosted_cost_per_mtok(2.0, 2000, 0.3) == pytest.approx(0.9259259, rel=1e-6)


def test_self_hosted_rejects_bad_input(cost):
    for args in [(0, 100, 1.0), (1.0, 0, 1.0), (1.0, 100, 0.0), (1.0, 100, 1.2), (-1.0, 100, 0.5)]:
        with pytest.raises(ValueError):
            cost.self_hosted_cost_per_mtok(*args)


# ---------- choose_model ----------

CANDIDATES = [
    {"name": "big", "price": BIG, "quality": 0.92, "ttft_s": 0.8, "tokens_per_s": 60},
    {"name": "small", "price": SMALL, "quality": 0.78, "ttft_s": 0.3, "tokens_per_s": 150},
    {"name": "local-3b", "price": {"input": 0.05, "output": 0.05}, "quality": 0.70, "ttft_s": 0.2, "tokens_per_s": 25},
]


def test_choose_cheapest_meeting_quality(cost):
    # yêu cầu chất lượng thấp, độ trễ thoải mái: local rẻ nhất
    assert cost.choose_model(CANDIDATES, 2000, 300, 1000, min_quality=0.6, max_latency_s=30) == "local-3b"
    # cần chất lượng 0.75: bỏ local
    assert cost.choose_model(CANDIDATES, 2000, 300, 1000, min_quality=0.75, max_latency_s=30) == "small"
    # cần 0.9: chỉ còn big
    assert cost.choose_model(CANDIDATES, 2000, 300, 1000, min_quality=0.9, max_latency_s=30) == "big"
    # không ai đạt
    assert cost.choose_model(CANDIDATES, 2000, 300, 1000, min_quality=0.95, max_latency_s=30) is None


def test_choose_respects_latency(cost):
    # 300 token output: local 0.2 + 12 = 12.2 s, small 2.3 s, big 5.8 s
    assert cost.choose_model(CANDIDATES, 2000, 300, 1000, min_quality=0.6, max_latency_s=10) == "small"
    assert cost.choose_model(CANDIDATES, 2000, 300, 1000, min_quality=0.9, max_latency_s=5.8) == "big"  # bằng ngưỡng vẫn đạt
    assert cost.choose_model(CANDIDATES, 2000, 300, 1000, min_quality=0.9, max_latency_s=5.7) is None


def test_choose_uses_long_context_price(cost):
    # prompt 150 000 token: small sang bảng giá dài (0.5/2.5) nhưng vẫn rẻ hơn big
    two = CANDIDATES[:2]
    assert cost.choose_model(two, 150_000, 100, 10, min_quality=0.7, max_latency_s=60) == "small"
    pricey_long = dict(CANDIDATES[1], price={**SMALL, "long_context": {"threshold": 100_000, "input": 5.0, "output": 25.0}})
    assert cost.choose_model([CANDIDATES[0], pricey_long], 150_000, 100, 10, min_quality=0.7, max_latency_s=60) == "big"


def test_choose_tie_keeps_first(cost):
    a = {"name": "a", "price": NO_CACHE_PRICE, "quality": 0.8, "ttft_s": 0.1, "tokens_per_s": 100}
    b = dict(a, name="b")
    assert cost.choose_model([a, b], 1000, 100, 100, min_quality=0.5, max_latency_s=10) == "a"
    assert cost.choose_model([b, a], 1000, 100, 100, min_quality=0.5, max_latency_s=10) == "b"
