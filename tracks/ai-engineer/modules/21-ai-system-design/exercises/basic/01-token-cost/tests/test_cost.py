import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def c():
    return ex.module("cost.py")


# Giá giả định cho test (USD / 1 triệu token), không phải giá thật của model nào.
def price(c, cached=None, write=None):
    return c.Price(input=2.0, output=10.0, cached_input=cached, cache_write=write)


def test_request_cost_basic(c):
    # (2000 * 2 + 300 * 10) / 1e6 = 0.007
    u = c.Usage(input_tokens=2000, output_tokens=300)
    assert c.request_cost(u, price(c)) == pytest.approx(0.007, abs=1e-12)
    assert isinstance(c.request_cost(u, price(c)), float)
    # output đắt gấp 5 lần input: 300 token output tốn hơn 1 000 token input
    assert c.request_cost(c.Usage(0, 300), price(c)) > c.request_cost(c.Usage(1000, 0), price(c))


def test_cached_tokens_are_part_of_input(c):
    # 1 500 trong 2 000 token input đọc từ cache: 500 * 2 + 1500 * 0.1 + 300 * 10 = 4150 -> 0.00415
    u = c.Usage(input_tokens=2000, output_tokens=300, cached_tokens=1500)
    assert c.request_cost(u, price(c, cached=0.1)) == pytest.approx(0.00415, abs=1e-12)


def test_cache_write_price(c):
    # ghi 1 500 token vào cache giá 2.5: 500 * 2 + 1500 * 2.5 + 3000 = 7750 -> 0.00775
    u = c.Usage(input_tokens=2000, output_tokens=300, cache_write_tokens=1500)
    assert c.request_cost(u, price(c, cached=0.1, write=2.5)) == pytest.approx(0.00775, abs=1e-12)
    # cache_write = None: ghi cache tính như input thường
    assert c.request_cost(u, price(c, cached=0.1)) == pytest.approx(0.007, abs=1e-12)


def test_per_1k_and_monthly(c):
    u = c.Usage(input_tokens=2000, output_tokens=300)
    assert c.cost_per_1k_requests(u, price(c)) == pytest.approx(7.0, abs=1e-9)
    # 10 000 request/ngày, 30 ngày: 0.007 * 300 000 = 2 100 USD
    assert c.monthly_cost(u, price(c), requests_per_day=10_000) == pytest.approx(2100.0, abs=1e-6)
    assert c.monthly_cost(u, price(c), requests_per_day=10_000, days=31) == pytest.approx(2170.0, abs=1e-6)


def test_invalid_usage(c):
    with pytest.raises(ValueError):  # cache hit trên model không có prompt caching
        c.request_cost(c.Usage(2000, 300, cached_tokens=100), price(c))
    with pytest.raises(ValueError):  # cached + write vượt input
        c.request_cost(c.Usage(2000, 300, cached_tokens=1500, cache_write_tokens=600), price(c, cached=0.1))
    with pytest.raises(ValueError):
        c.request_cost(c.Usage(-1, 300), price(c))
    with pytest.raises(ValueError):
        c.monthly_cost(c.Usage(10, 10), price(c), requests_per_day=-5)


def test_agent_loop_grows_quadratically(c):
    # P_i = 3000 + (i - 1) * 1000: 3000, 4000, 5000, 6000, 7000
    u = c.agent_loop_usage(prefix_tokens=3000, step_output_tokens=200, tool_result_tokens=800, steps=5)
    assert (u.input_tokens, u.output_tokens, u.cached_tokens, u.cache_write_tokens) == (25000, 1000, 0, 0)
    # prefix 0, mỗi bước thêm 1 token: 0 + 1 + ... + 19 = 190 (không phải 20 hay 400)
    u = c.agent_loop_usage(prefix_tokens=0, step_output_tokens=1, tool_result_tokens=0, steps=20)
    assert u.input_tokens == 190
    assert c.agent_loop_usage(500, 50, 0, 1).input_tokens == 500


def test_agent_loop_with_prefix_cache(c):
    u = c.agent_loop_usage(3000, 200, 800, 5, cache_prefix=True)
    # đọc P_1..P_4 từ cache = 18 000; ghi P_1 + 4 * 1000 = 7 000
    assert (u.input_tokens, u.output_tokens, u.cached_tokens, u.cache_write_tokens) == (25000, 1000, 18000, 7000)
    p = price(c, cached=0.1, write=2.5)
    no_cache = c.request_cost(c.agent_loop_usage(3000, 200, 800, 5), p)
    with_cache = c.request_cost(u, p)
    assert no_cache == pytest.approx(0.06, abs=1e-12)
    assert with_cache == pytest.approx(0.0293, abs=1e-12)
    one = c.agent_loop_usage(500, 50, 0, 1, cache_prefix=True)
    assert (one.cached_tokens, one.cache_write_tokens) == (0, 500)


def test_agent_loop_rejects_bad_input(c):
    with pytest.raises(ValueError):
        c.agent_loop_usage(100, 10, 10, 0)
    with pytest.raises(ValueError):
        c.agent_loop_usage(-1, 10, 10, 3)
