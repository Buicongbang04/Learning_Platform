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
    # TODO
    raise NotImplementedError


def simulate(
    trace: list[dict], config: GatewayConfig, small: ModelSpec, large: ModelSpec, fallback: ModelSpec
) -> dict:
    """Chạy trace qua gateway theo thứ tự thời gian đến, trả các chỉ số (xem README bài)."""
    # TODO
    raise NotImplementedError


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
