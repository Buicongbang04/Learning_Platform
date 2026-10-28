import math

import pytest

from testkit import Exercise

ex = Exercise(__file__)

HOUR = 3600.0
T0 = 1_533_081_600.0  # 2018-08-01 00:00 UTC


def mod():
    return ex.module("monitor.py")


def make(**kw):
    m = mod()
    return m, m.PipelineMonitor(**kw)


def healthy_orders(m, mon, n=10, rows=3000):
    for i in range(n):
        mon.record(m.Run("orders", T0 + i * HOUR, 60.0 + i, rows + (i % 3 - 1) * 50, "success"))


def test_last_success_and_freshness():
    m, mon = make(freshness_sla={"orders": 2 * HOUR})
    assert mon.last_success("orders") is None
    assert math.isinf(mon.freshness("orders", T0))
    mon.record(m.Run("orders", T0 + 2 * HOUR, 100, 10, "success"))
    mon.record(m.Run("orders", T0, 50, 10, "success"))  # tới muộn, cũ hơn
    mon.record(m.Run("orders", T0 + 3 * HOUR, 30, 0, "failed"))
    assert mon.last_success("orders") == T0 + 2 * HOUR + 100
    assert mon.freshness("orders", T0 + 3 * HOUR) == HOUR - 100
    assert mon.freshness("orders", T0) == 0


def test_p95_nearest_rank():
    m, mon = make(freshness_sla={})
    assert mon.p95_duration("orders") is None
    for i, d in enumerate([5, 1, 4, 2, 3, 100, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]):
        mon.record(m.Run("orders", T0 + i, d, 1, "success"))
    # 20 phần tử, ceil(0.95*20)=19 -> phần tử thứ 19 sau khi sắp = 19
    assert mon.p95_duration("orders") == 19
    mon.record(m.Run("orders", T0 + 100, 200, 1, "failed"))
    # 21 phần tử, ceil(19.95)=20 -> 100
    assert mon.p95_duration("orders") == 100


def test_error_rate_window():
    m, mon = make(freshness_sla={}, error_window=4)
    assert mon.error_rate("orders") == 0.0
    statuses = ["failed", "failed", "success", "success", "failed", "success"]
    for i, s in enumerate(statuses):
        mon.record(m.Run("orders", T0 + i * HOUR, 10, 1, s))
    # 4 run gần nhất: success, success, failed, success
    assert mon.error_rate("orders") == pytest.approx(0.25)


def test_volume_zscore():
    m, mon = make(freshness_sla={}, min_history=3)
    for i, rows in enumerate([100, 200, 300]):
        mon.record(m.Run("orders", T0 + i, 1, rows, "success"))
    assert mon.volume_zscore("orders") is None  # chỉ có 2 run trước run mới nhất
    mon.record(m.Run("orders", T0 + 10, 1, 400, "success"))
    # trước đó [100,200,300]: mean 200, pstdev 81.65 -> z = 2.449
    assert mon.volume_zscore("orders") == pytest.approx(200 / 81.6496580927726)
    mon.record(m.Run("orders", T0 + 11, 1, 999999, "failed"))  # run lỗi không tính
    assert mon.volume_zscore("orders") == pytest.approx(200 / 81.6496580927726)


def test_volume_zscore_zero_std():
    m, mon = make(freshness_sla={}, min_history=2)
    for i in range(3):
        mon.record(m.Run("p", T0 + i, 1, 50, "success"))
    assert mon.volume_zscore("p") == 0.0
    mon.record(m.Run("p", T0 + 9, 1, 10, "success"))
    m2, mon2 = make(freshness_sla={}, min_history=2)
    for i, r in enumerate([50, 50, 10]):
        mon2.record(m2.Run("p", T0 + i, 1, r, "success"))
    assert mon2.volume_zscore("p") == -math.inf


def test_no_alerts_when_healthy():
    m, mon = make(freshness_sla={"orders": 2 * HOUR}, p95_threshold={"orders": 600})
    healthy_orders(m, mon)
    assert mon.evaluate(T0 + 10 * HOUR) == []


def test_alert_kinds():
    m, mon = make(
        freshness_sla={"orders": 2 * HOUR, "reviews": HOUR},
        error_rate_threshold=0.2,
        p95_threshold={"orders": 600},
    )
    healthy_orders(m, mon)
    mon.record(m.Run("orders", T0 + 10 * HOUR, 900, 120, "success"))  # volume tụt + chậm
    mon.record(m.Run("orders", T0 + 11 * HOUR, 30, 0, "failed"))
    mon.record(m.Run("orders", T0 + 12 * HOUR, 30, 0, "failed"))
    mon.record(m.Run("orders", T0 + 13 * HOUR, 30, 0, "failed"))
    alerts = mon.evaluate(T0 + 14 * HOUR)
    kinds = [(a.pipeline, a.kind) for a in alerts]
    assert kinds == [
        ("orders", "error_rate"),  # 3/14 > 0.2
        ("orders", "freshness"),   # lần OK cuối kết thúc T0+10h+900s, now T0+14h
        ("orders", "latency"),     # p95 = 900 > 600
        ("orders", "volume"),
        ("reviews", "freshness"),  # chưa từng chạy
    ]
    assert all(isinstance(a.message, str) and a.message for a in alerts)


def test_prometheus_text():
    m, mon = make(freshness_sla={"orders": 2 * HOUR, "reviews": HOUR})
    healthy_orders(m, mon, n=3)
    mon.record(m.Run("orders", T0 + 3 * HOUR, 10, 0, "failed"))
    text = mon.to_prometheus(T0 + 4 * HOUR)
    assert text.endswith("\n")
    for name, kind in [
        ("pipeline_freshness_seconds", "gauge"),
        ("pipeline_runs_total", "counter"),
        ("pipeline_duration_p95_seconds", "gauge"),
        ("pipeline_last_run_rows", "gauge"),
    ]:
        assert f"# TYPE {name} {kind}" in text
        assert f"# HELP {name} " in text
    lines = text.splitlines()
    assert 'pipeline_runs_total{pipeline="orders",status="success"} 3' in lines
    assert 'pipeline_runs_total{pipeline="orders",status="failed"} 1' in lines
    assert 'pipeline_last_run_rows{pipeline="orders"} 0' in lines
    assert 'pipeline_freshness_seconds{pipeline="reviews"} +Inf' in lines


def test_prometheus_parse():
    parser = pytest.importorskip("prometheus_client.parser")
    m, mon = make(freshness_sla={"orders": 2 * HOUR})
    healthy_orders(m, mon, n=3)
    mon.record(m.Run('we"ird', T0, 1, 1, "success"))
    fams = {f.name: f for f in parser.text_string_to_metric_families(mon.to_prometheus(T0 + 3 * HOUR))}
    fresh = {s.labels["pipeline"]: s.value for s in fams["pipeline_freshness_seconds"].samples}
    assert fresh["orders"] == pytest.approx(T0 + 3 * HOUR - (T0 + 2 * HOUR + 62))
    assert 'we"ird' in fresh
    assert fams["pipeline_runs"].type == "counter"
