import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def c():
    return ex.module("cost.py")


def price(c, **kw):
    base = dict(input=3.0, output=15.0, cache_write=3.75, cache_read=0.30)
    base.update(kw)
    return c.Price(**base)


def test_request_cost_plain(c):
    p = price(c)
    # 2 000 token vào x $3/MTok + 500 token ra x $15/MTok = 0.006 + 0.0075
    assert c.request_cost(c.Usage(2000, 500), p) == pytest.approx(0.0135, abs=1e-12)
    assert isinstance(c.request_cost(c.Usage(2000, 500), p), float)
    assert c.request_cost(c.Usage(0, 0), p) == 0.0


def test_request_cost_cache_and_batch(c):
    p = price(c)
    u = c.Usage(input_tokens=1000, output_tokens=200, cache_write_tokens=10_000, cache_read_tokens=50_000)
    expected = (1000 * 3 + 200 * 15 + 10_000 * 3.75 + 50_000 * 0.30) / 1e6     # 0.0585
    assert c.request_cost(u, p) == pytest.approx(expected, abs=1e-12)
    assert c.request_cost(u, p, batch=True) == pytest.approx(expected * 0.5, abs=1e-12)
    assert c.request_cost(u, price(c, batch_discount=0.2), batch=True) == pytest.approx(expected * 0.8, abs=1e-12)


def test_request_cost_rejects_bad_input(c):
    with pytest.raises(ValueError):
        c.request_cost(c.Usage(-1, 10), price(c))
    with pytest.raises(ValueError):
        c.request_cost(c.Usage(10, 10, cache_read_tokens=5), c.Price(input=1.0, output=2.0))
    with pytest.raises(ValueError):
        c.request_cost(c.Usage(10, 10, cache_write_tokens=5), c.Price(input=1.0, output=2.0, cache_read=0.1))
    assert c.request_cost(c.Usage(10, 10), c.Price(input=1.0, output=2.0)) == pytest.approx(30 / 1e6)


def test_workload_without_cache(c):
    p = price(c)
    # 100 000 request x (1 500 vào, 100 ra): 150M x 3 + 10M x 15 = 450 + 150 = 600 USD
    assert c.workload_cost(100_000, 1500, 100, p) == pytest.approx(600.0, rel=1e-12)
    assert c.workload_cost(100_000, 1500, 100, p, batch=True) == pytest.approx(300.0, rel=1e-12)


def test_workload_with_cached_prefix(c):
    p = price(c)
    # prefix 1 200 token chung (system + few-shot), 300 token riêng mỗi request, 90% request trúng cache
    per_hit = (300 * 3 + 100 * 15 + 1200 * 0.30) / 1e6
    per_miss = (300 * 3 + 100 * 15 + 1200 * 3.75) / 1e6
    expected = 100_000 * (0.9 * per_hit + 0.1 * per_miss)      # 317.4
    got = c.workload_cost(100_000, 1500, 100, p, cached_prefix_tokens=1200, cache_hit_rate=0.9)
    assert got == pytest.approx(expected, rel=1e-12)
    assert got == pytest.approx(317.4, rel=1e-9)
    all_hit = c.workload_cost(10, 1500, 100, p, cached_prefix_tokens=1200, cache_hit_rate=1.0)
    assert all_hit == pytest.approx(10 * per_hit, rel=1e-12)


def test_workload_hit_rate_edges_do_not_need_unused_price(c):
    no_read = c.Price(input=3.0, output=15.0, cache_write=3.75)
    got = c.workload_cost(10, 1500, 100, no_read, cached_prefix_tokens=1200, cache_hit_rate=0.0)
    assert got == pytest.approx(10 * (300 * 3 + 100 * 15 + 1200 * 3.75) / 1e6, rel=1e-12)


def test_workload_rejects_bad_input(c):
    p = price(c)
    with pytest.raises(ValueError):
        c.workload_cost(10, 1000, 10, p, cached_prefix_tokens=1001, cache_hit_rate=0.5)
    with pytest.raises(ValueError):
        c.workload_cost(10, 1000, 10, p, cached_prefix_tokens=100, cache_hit_rate=1.5)


def test_cache_breakeven(c):
    # ghi 1.25x, đọc 0.1x: hoà vốn sau 1 lần đọc; ghi 2x: sau 2 lần đọc (đúng như trang giá Anthropic nói)
    assert c.cache_breakeven(c.Price(input=4.0, output=20.0, cache_write=5.0, cache_read=0.4)) == 1
    assert c.cache_breakeven(c.Price(input=4.0, output=20.0, cache_write=8.0, cache_read=0.4)) == 2
    # ghi 3x, đọc 0.5x: (3 - 1) / (1 - 0.5) = 4 lần đọc, đúng biên
    assert c.cache_breakeven(c.Price(input=1.0, output=2.0, cache_write=3.0, cache_read=0.5)) == 4
    # ghi không đắt hơn input thường: có lời ngay
    assert c.cache_breakeven(c.Price(input=1.0, output=2.0, cache_write=1.0, cache_read=0.25)) == 0
    with pytest.raises(ValueError):
        c.cache_breakeven(c.Price(input=1.0, output=2.0))
    with pytest.raises(ValueError):
        c.cache_breakeven(c.Price(input=1.0, output=2.0, cache_write=1.25, cache_read=1.0))


def test_rank_models(c):
    prices = {
        "lớn": c.Price(input=5.0, output=25.0),
        "vừa": c.Price(input=2.0, output=10.0),
        "nhỏ": c.Price(input=0.1, output=0.5),
        "nhỏ-bản-sao": c.Price(input=0.1, output=0.5),
    }
    ranked = c.rank_models(prices, 1000, 800, 50)
    assert [name for name, _ in ranked] == ["nhỏ", "nhỏ-bản-sao", "vừa", "lớn"], "rẻ nhất trước, hoà thì theo tên"
    assert ranked[-1][1] == pytest.approx(1000 * (800 * 5 + 50 * 25) / 1e6)
    batch = dict(c.rank_models(prices, 1000, 800, 50, batch=True))
    assert batch["lớn"] == pytest.approx(ranked[-1][1] / 2)
