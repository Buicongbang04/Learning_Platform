import csv

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def gw():
    return ex.module("gateway.py")


@pytest.fixture(scope="module")
def models(gw):
    # Giá GIẢ ĐỊNH (USD / 1 triệu token)
    return gw.ModelSpec("small", 0.10, 0.40), gw.ModelSpec("large", 2.00, 10.00), gw.ModelSpec("fallback", 0.30, 2.50)


def req(i, t, user="u1", key="faq_1", personal=False, conf=0.9, ok=True, ls=0.5, ll=2.0, lf=1.5,
        in_tok=1000, out_tok=100):
    return {"id": i, "t": t, "user": user, "key": key, "personal": personal, "in_tok": in_tok, "out_tok": out_tok,
            "small_conf": conf, "large_ok": ok, "lat_small": ls, "lat_large": ll, "lat_fallback": lf}


def run(gw, models, trace, **cfg):
    return gw.simulate(trace, gw.GatewayConfig(**cfg), *models)


LARGE = (1000 * 2.0 + 100 * 10.0) / 1e6  # 0.003 USD mỗi lần gọi large
SMALL = (1000 * 0.1 + 100 * 0.4) / 1e6  # 0.00014
FALLBACK = (1000 * 0.3 + 100 * 2.5) / 1e6  # 0.00055


def test_call_cost(gw, models):
    assert gw.call_cost(models[1], 1000, 100) == pytest.approx(LARGE)


def test_large_only(gw, models):
    m = run(gw, models, [req(0, 0, ll=1.0), req(1, 1, key="faq_2", ll=2.0), req(2, 2, key="faq_3", ll=3.0)])
    assert m["requests"] == 3 and m["served"] == 3 and m["availability"] == 1.0
    assert m["cost_usd"] == pytest.approx(3 * LARGE)
    assert m["cost_per_1k"] == pytest.approx(1000 * LARGE)
    assert m["p50_s"] == pytest.approx(2.0)
    assert m["calls"] == {"small": 0, "large": 3, "fallback": 0}


def test_failure_and_fallback(gw, models):
    trace = [req(0, 0), req(1, 1, key="faq_2", ok=False)]
    m = run(gw, models, trace)
    assert m["served"] == 1 and m["availability"] == 0.5
    assert m["cost_usd"] == pytest.approx(LARGE)  # gọi lỗi không mất tiền
    m = run(gw, models, trace, fallback=True, timeout_s=4.0)
    assert m["availability"] == 1.0
    assert m["cost_usd"] == pytest.approx(LARGE + FALLBACK)
    assert m["p95_s"] == pytest.approx(2.0 + 0.95 * (4.0 + 1.5 - 2.0))  # 4 s chờ timeout + 1.5 s fallback
    assert m["calls"] == {"small": 0, "large": 2, "fallback": 1}


def test_user_cache_and_ttl(gw, models):
    trace = [req(0, 0), req(1, 10), req(2, 20, user="u2"), req(3, 200)]
    m = run(gw, models, trace, cache_ttl_s=100, cache_latency_s=0.01)
    # t=10: trúng (cùng user, trong TTL); t=20: user khác -> trượt; t=200: hết TTL -> trượt
    assert m["cache_hits"] == 1 and m["cache_hit_rate"] == 0.25
    assert m["cost_usd"] == pytest.approx(3 * LARGE)
    assert m["calls"]["large"] == 3
    assert run(gw, models, trace)["cache_hits"] == 0  # cache_ttl_s = 0: tắt cache


def test_global_cache_leaks_personal_answers(gw, models):
    trace = [req(0, 0, user="u1", key="p_order", personal=True), req(1, 5, user="u2", key="p_order", personal=True),
             req(2, 6, user="u1", key="faq_1"), req(3, 7, user="u3", key="faq_1")]
    m = run(gw, models, trace, cache_ttl_s=100, cache_scope="global")
    assert m["cache_hits"] == 2
    assert m["leaks"] == 1  # u2 nhận câu trả lời về đơn hàng của u1; faq dùng chung không phải rò rỉ
    m = run(gw, models, trace, cache_ttl_s=100, cache_scope="public")
    assert (m["cache_hits"], m["leaks"]) == (1, 0)  # chỉ faq_1 được dùng chung; câu hỏi cá nhân không cache
    m = run(gw, models, trace + [req(4, 8, user="u1", key="p_order", personal=True)], cache_ttl_s=100,
            cache_scope="public")
    assert m["cache_hits"] == 1  # kể cả cùng user: câu hỏi cá nhân không vào cache public


def test_cascade(gw, models):
    trace = [req(0, 0, conf=0.9), req(1, 1, key="faq_2", conf=0.5)]
    m = run(gw, models, trace, cascade_threshold=0.7)
    assert m["calls"] == {"small": 2, "large": 1, "fallback": 0}
    assert m["cost_usd"] == pytest.approx(2 * SMALL + LARGE)
    # request 2 trả giá độ trễ của cả hai model: 0.5 + 2.0
    assert sorted([m["p50_s"]]) == [pytest.approx((0.5 + 2.5) / 2)]
    assert m["p95_s"] == pytest.approx(0.5 + 0.95 * 2.0)
    m = run(gw, models, [req(0, 0, conf=0.7)], cascade_threshold=0.7)  # bằng ngưỡng: small trả lời
    assert m["calls"]["large"] == 0


def test_circuit_breaker(gw, models):
    trace = [req(0, 0, ok=False), req(1, 1, key="f2", ok=False), req(2, 10, key="f3", ok=True),
             req(3, 70, key="f4", ok=True), req(4, 71, key="f5", ok=True)]
    m = run(gw, models, trace, fallback=True, timeout_s=5.0, breaker_failures=2, breaker_cooldown_s=60)
    # 2 lỗi liên tiếp -> ngắt tới t=61: request t=10 đi thẳng fallback, không chờ timeout, không gọi large
    assert m["calls"] == {"small": 0, "large": 4, "fallback": 3}
    assert m["cost_usd"] == pytest.approx(2 * LARGE + 3 * FALLBACK)
    assert m["p50_s"] == pytest.approx(2.0)  # [1.5, 2.0, 2.0, 6.5, 6.5]
    m = run(gw, models, trace, fallback=True, timeout_s=5.0)  # không breaker
    assert m["calls"] == {"small": 0, "large": 5, "fallback": 2}


def test_breaker_resets_on_success(gw, models):
    trace = [req(0, 0, ok=False), req(1, 1, key="f2"), req(2, 2, key="f3", ok=False), req(3, 3, key="f4")]
    m = run(gw, models, trace, fallback=True, breaker_failures=2)
    assert m["calls"]["large"] == 4  # hai lỗi không liên tiếp: không ngắt


def test_sorted_by_time_and_validation(gw, models):
    trace = [req(1, 10), req(0, 0)]  # đến không theo thứ tự trong danh sách
    m = run(gw, models, trace, cache_ttl_s=100)
    assert m["cache_hits"] == 1
    # xử lý sai thứ tự sẽ "trúng" một mục cache được lưu ở tương lai (t=200) cho request t=0
    assert run(gw, models, [req(1, 200), req(0, 0)], cache_ttl_s=100)["cache_hits"] == 0
    with pytest.raises(ValueError):
        run(gw, models, trace, cache_scope="team")
    with pytest.raises(ValueError):
        run(gw, models, [])


@pytest.fixture(scope="module")
def trace():
    with open(ex.fixtures / "trace.csv") as f:
        return [{**r, "t": float(r["t"]), "personal": r["personal"] == "1", "in_tok": int(r["in_tok"]),
                 "out_tok": int(r["out_tok"]), "small_conf": float(r["small_conf"]), "large_ok": r["large_ok"] == "1",
                 "lat_small": float(r["lat_small"]), "lat_large": float(r["lat_large"]),
                 "lat_fallback": float(r["lat_fallback"])} for r in csv.DictReader(f)]


def test_fixture_trace(gw, models, trace):
    base = run(gw, models, trace)
    assert base["availability"] == pytest.approx(0.837)  # 1 674 / 2 000
    assert base["cost_per_1k"] == pytest.approx(5.156, abs=1e-3)
    fb = run(gw, models, trace, fallback=True)
    assert fb["p95_s"] > 12  # timeout 10 s trong sự cố đẩy p95 lên
    br = run(gw, models, trace, fallback=True, breaker_failures=3)
    assert br["p95_s"] < 5
    pub = run(gw, models, trace, fallback=True, breaker_failures=3, cache_ttl_s=3600, cache_scope="public")
    assert pub["cache_hit_rate"] == pytest.approx(0.478, abs=1e-3) and pub["leaks"] == 0
    assert pub["cost_per_1k"] == pytest.approx(2.882, abs=1e-3)
    glob = run(gw, models, trace, fallback=True, breaker_failures=3, cache_ttl_s=3600, cache_scope="global")
    assert glob["leaks"] == 925
