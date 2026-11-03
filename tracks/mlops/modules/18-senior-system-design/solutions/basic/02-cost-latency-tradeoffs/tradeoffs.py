import math


def cache_plan(qps: float, hit_rate: float, cache_ms: float, cache_p99_ms: float, model_ms: float, model_p99_ms: float,
               model_cost_per_1k: float, cache_cost_per_hour: float) -> dict:
    """{"mean_ms", "p99_ms", "model_calls_per_hour", "cost_per_hour"} theo công thức trong README."""
    if not 0 <= hit_rate <= 1:
        raise ValueError("hit_rate phải nằm trong [0, 1]")
    miss = 1 - hit_rate
    calls = qps * 3600 * miss
    return {
        "mean_ms": cache_ms + miss * model_ms,
        "p99_ms": cache_ms + model_p99_ms if miss > 0.01 else cache_p99_ms,
        "model_calls_per_hour": calls,
        "cost_per_hour": calls / 1000 * model_cost_per_1k + cache_cost_per_hour,
    }


def batch_vs_realtime(entities: int, refreshes_per_day: int, batch_cost_per_1k: float, requests_per_day: int,
                      realtime_cost_per_1k: float, realtime_fixed_per_day: float) -> dict:
    """{"batch_cost_per_day", "realtime_cost_per_day", "batch_max_staleness_h", "cheaper"}."""
    if refreshes_per_day <= 0:
        raise ValueError("refreshes_per_day phải dương")
    batch = entities * refreshes_per_day / 1000 * batch_cost_per_1k
    realtime = requests_per_day / 1000 * realtime_cost_per_1k + realtime_fixed_per_day
    return {
        "batch_cost_per_day": batch,
        "realtime_cost_per_day": realtime,
        "batch_max_staleness_h": 24 / refreshes_per_day,
        "cheaper": "batch" if batch <= realtime else "realtime",
    }


def distillation_breakeven_days(teacher_cost_per_1k: float, student_cost_per_1k: float, one_off_cost: float,
                                requests_per_day: int) -> float:
    """Số ngày để tiền tiết kiệm bù chi phí distill một lần; math.inf khi student không rẻ hơn."""
    saving_per_day = (teacher_cost_per_1k - student_cost_per_1k) * requests_per_day / 1000
    return one_off_cost / saving_per_day if saving_per_day > 0 else math.inf


def choose(options: list[dict], max_p99_ms: float, max_quality_drop: float) -> str | None:
    """Tên phương án rẻ nhất thoả cả hai ràng buộc; hoà chi phí thì p99 thấp hơn; None khi không có."""
    feasible = [o for o in options if o["p99_ms"] <= max_p99_ms and o["quality_drop"] <= max_quality_drop]
    if not feasible:
        return None
    return min(feasible, key=lambda o: (o["cost_per_day"], o["p99_ms"]))["name"]
