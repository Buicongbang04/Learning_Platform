def cache_plan(qps: float, hit_rate: float, cache_ms: float, cache_p99_ms: float, model_ms: float, model_p99_ms: float,
               model_cost_per_1k: float, cache_cost_per_hour: float) -> dict:
    """{"mean_ms", "p99_ms", "model_calls_per_hour", "cost_per_hour"} theo công thức trong README."""
    # TODO
    raise NotImplementedError


def batch_vs_realtime(entities: int, refreshes_per_day: int, batch_cost_per_1k: float, requests_per_day: int,
                      realtime_cost_per_1k: float, realtime_fixed_per_day: float) -> dict:
    """{"batch_cost_per_day", "realtime_cost_per_day", "batch_max_staleness_h", "cheaper"}."""
    # TODO
    raise NotImplementedError


def distillation_breakeven_days(teacher_cost_per_1k: float, student_cost_per_1k: float, one_off_cost: float,
                                requests_per_day: int) -> float:
    """Số ngày để tiền tiết kiệm bù chi phí distill một lần; math.inf khi student không rẻ hơn."""
    # TODO
    raise NotImplementedError


def choose(options: list[dict], max_p99_ms: float, max_quality_drop: float) -> str | None:
    """Tên phương án rẻ nhất thoả cả hai ràng buộc; hoà chi phí thì p99 thấp hơn; None khi không có."""
    # TODO
    raise NotImplementedError
