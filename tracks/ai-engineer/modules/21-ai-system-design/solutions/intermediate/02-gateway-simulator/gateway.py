"""Mô phỏng LLM gateway trên một trace request: cache, cascade small -> large, fallback khi model chính lỗi.

Mỗi request của trace là một dict (xem README bài):
    id, t (giây đến), user, key (câu hỏi đã chuẩn hoá), personal (bool), in_tok, out_tok,
    small_conf (độ tự tin của model nhỏ, 0..1), large_ok (bool), lat_small, lat_large, lat_fallback (giây).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ModelSpec:
    name: str
    input_price: float  # USD / 1 triệu token
    output_price: float


@dataclass(frozen=True)
class GatewayConfig:
    cache_ttl_s: float = 0.0  # 0: tắt cache
    # "user": khoá (user, key); "global": khoá là key; "public": chỉ cache request không cá nhân, khoá là key
    cache_scope: str = "user"
    cascade_threshold: float | None = None  # None: luôn gọi large; số: gọi small trước, small_conf < ngưỡng thì gọi thêm large
    fallback: bool = False  # large lỗi thì gọi model fallback
    timeout_s: float = 10.0  # thời gian chờ large trước khi coi là lỗi
    breaker_failures: int = 0  # 0: tắt circuit breaker; k: sau k lần large lỗi liên tiếp thì ngắt
    breaker_cooldown_s: float = 60.0  # thời gian ngắt: không gọi large, đi thẳng fallback (hoặc lỗi)
    cache_latency_s: float = 0.005


def call_cost(model: ModelSpec, in_tok: int, out_tok: int) -> float:
    """Chi phí USD một lần gọi model."""
    return (in_tok * model.input_price + out_tok * model.output_price) / 1_000_000


def simulate(
    trace: list[dict], config: GatewayConfig, small: ModelSpec, large: ModelSpec, fallback: ModelSpec
) -> dict:
    """Chạy trace qua gateway theo thứ tự thời gian đến, trả các chỉ số (xem README bài)."""
    if not trace:
        raise ValueError("trace rỗng")
    if config.cache_scope not in ("user", "global", "public"):
        raise ValueError("cache_scope là 'user', 'global' hoặc 'public'")
    cache: dict = {}  # khoá -> (thời điểm lưu, user đã tạo câu trả lời)
    latencies: list[float] = []
    cost = 0.0
    hits = leaks = 0
    calls = {"small": 0, "large": 0, "fallback": 0}
    fails_in_row = 0
    open_until = float("-inf")
    for r in sorted(trace, key=lambda r: r["t"]):
        ck = (r["user"], r["key"]) if config.cache_scope == "user" else r["key"]
        cacheable = config.cache_ttl_s > 0 and not (config.cache_scope == "public" and r["personal"])
        if cacheable and ck in cache and r["t"] - cache[ck][0] <= config.cache_ttl_s:
            hits += 1
            if r["personal"] and cache[ck][1] != r["user"]:
                leaks += 1
            latencies.append(config.cache_latency_s)
            continue
        lat = 0.0
        served = False
        if config.cascade_threshold is not None:
            calls["small"] += 1
            cost += call_cost(small, r["in_tok"], r["out_tok"])
            lat += r["lat_small"]
            served = r["small_conf"] >= config.cascade_threshold
        if not served:
            large_failed = True
            if r["t"] >= open_until:  # breaker đóng (hoặc hết thời gian ngắt): thử large
                calls["large"] += 1
                if r["large_ok"]:
                    cost += call_cost(large, r["in_tok"], r["out_tok"])
                    lat += r["lat_large"]
                    served, large_failed = True, False
                    fails_in_row = 0
                else:
                    lat += config.timeout_s
                    fails_in_row += 1
                    if config.breaker_failures and fails_in_row >= config.breaker_failures:
                        open_until = r["t"] + config.breaker_cooldown_s
            if large_failed:
                if config.fallback:
                    calls["fallback"] += 1
                    cost += call_cost(fallback, r["in_tok"], r["out_tok"])
                    lat += r["lat_fallback"]
                    served = True
        if served:
            latencies.append(lat)
            if cacheable:
                cache[ck] = (r["t"], r["user"])
    n = len(trace)
    lat_arr = np.array(latencies) if latencies else np.array([np.nan])
    return {
        "requests": n,
        "served": len(latencies),
        "availability": len(latencies) / n,
        "cache_hits": hits,
        "cache_hit_rate": hits / n,
        "leaks": leaks,
        "cost_usd": cost,
        "cost_per_1k": cost / n * 1000,
        "p50_s": float(np.percentile(lat_arr, 50)),
        "p95_s": float(np.percentile(lat_arr, 95)),
        "calls": calls,
    }


if __name__ == "__main__":
    import csv
    from pathlib import Path

    module_dir = next(p for p in Path(__file__).resolve().parents if (p / "exercises").is_dir())
    path = module_dir / "exercises/intermediate/02-gateway-simulator/tests/fixtures/trace.csv"
    with open(path) as f:
        trace = [
            {**r, "t": float(r["t"]), "personal": r["personal"] == "1", "in_tok": int(r["in_tok"]),
             "out_tok": int(r["out_tok"]), "small_conf": float(r["small_conf"]), "large_ok": r["large_ok"] == "1",
             "lat_small": float(r["lat_small"]), "lat_large": float(r["lat_large"]),
             "lat_fallback": float(r["lat_fallback"])}
            for r in csv.DictReader(f)
        ]
    # Giá GIẢ ĐỊNH (USD / 1 triệu token), cùng tỉ lệ với một model nhỏ, một model lớn và một model dự phòng
    small = ModelSpec("small", 0.10, 0.40)
    large = ModelSpec("large", 2.00, 10.00)
    fb = ModelSpec("fallback", 0.30, 2.50)
    configs = {
        "chỉ large": GatewayConfig(),
        "+ fallback": GatewayConfig(fallback=True),
        "+ breaker 3/60s": GatewayConfig(fallback=True, breaker_failures=3, breaker_cooldown_s=60),
        "+ cache public": GatewayConfig(fallback=True, breaker_failures=3, cache_ttl_s=3600, cache_scope="public"),
        "+ cascade 0.7": GatewayConfig(fallback=True, breaker_failures=3, cache_ttl_s=3600, cache_scope="public",
                                       cascade_threshold=0.7),
        "cache user": GatewayConfig(fallback=True, breaker_failures=3, cache_ttl_s=3600, cache_scope="user"),
        "cache global (lỗi)": GatewayConfig(fallback=True, breaker_failures=3, cache_ttl_s=3600, cache_scope="global"),
    }
    print(f"{'cấu hình':20} {'avail':>7} {'hit':>6} {'leak':>5} {'USD/1k':>8} {'p50':>6} {'p95':>6}")
    for name, cfg in configs.items():
        m = simulate(trace, cfg, small, large, fb)
        print(f"{name:20} {m['availability']:7.3f} {m['cache_hit_rate']:6.3f} {m['leaks']:5d} "
              f"{m['cost_per_1k']:8.3f} {m['p50_s']:6.2f} {m['p95_s']:6.2f}")
