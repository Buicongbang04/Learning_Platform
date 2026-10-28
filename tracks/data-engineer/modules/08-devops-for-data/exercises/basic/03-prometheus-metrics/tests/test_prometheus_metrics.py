import math
import re
from datetime import datetime, timedelta, timezone

import pytest

from testkit import Exercise

ex = Exercise(__file__)

STATS = [
    {"pipeline": "orders", "rows_processed": 98666, "last_success": 1730102400.0, "duration_seconds": 42.5},
    {"pipeline": "payments", "rows_processed": 103886, "last_success": 1730098800.0, "duration_seconds": 12.0},
]


def m():
    return ex.module("metrics.py")


def test_escape_label_value():
    esc = m().escape_label_value
    assert esc("orders") == "orders"
    assert esc('a"b') == 'a\\"b'
    assert esc("a\\b") == "a\\\\b"
    assert esc("a\nb") == "a\\nb"
    assert esc('x\\"') == 'x\\\\\\"'


def test_help_and_type_before_samples():
    text = m().render_metrics(STATS)
    assert text.endswith("\n")
    lines = text.splitlines()
    expected = {
        "pipeline_rows_processed_total": "counter",
        "pipeline_last_success_timestamp_seconds": "gauge",
        "pipeline_duration_seconds": "gauge",
    }
    for name, kind in expected.items():
        helps = [i for i, line in enumerate(lines) if line.startswith(f"# HELP {name} ")]
        types = [i for i, line in enumerate(lines) if line == f"# TYPE {name} {kind}"]
        samples = [i for i, line in enumerate(lines) if line.startswith(name + "{")]
        assert len(helps) == 1 and len(types) == 1, f"{name}: cần đúng một HELP và một TYPE"
        assert len(samples) == 2
        assert helps[0] < types[0] < min(samples)


def parse_samples(text):
    pattern = re.compile(r'^(\w+)\{pipeline="((?:[^"\\]|\\.)*)"\} (\S+)$')
    out = {}
    for line in text.splitlines():
        if line.startswith("#") or not line:
            continue
        match = pattern.match(line)
        assert match, f"Dòng mẫu sai định dạng: {line!r}"
        out[(match[1], match[2])] = float(match[3])
    return out


def test_sample_values():
    samples = parse_samples(m().render_metrics(STATS))
    assert samples[("pipeline_rows_processed_total", "orders")] == 98666
    assert samples[("pipeline_rows_processed_total", "payments")] == 103886
    assert samples[("pipeline_last_success_timestamp_seconds", "orders")] == 1730102400.0
    assert samples[("pipeline_duration_seconds", "payments")] == 12.0


def test_escaped_label_in_output():
    text = m().render_metrics([{**STATS[0], "pipeline": 'weird"name'}])
    assert 'pipeline="weird\\"name"' in text


def test_empty():
    assert m().render_metrics([]) == ""


def test_parse_with_prometheus_client():
    parser = pytest.importorskip("prometheus_client.parser")
    families = {f.name: f for f in parser.text_string_to_metric_families(m().render_metrics(STATS))}
    # prometheus_client bỏ hậu tố _total khỏi tên family của counter
    assert families["pipeline_rows_processed"].type == "counter"
    assert families["pipeline_last_success_timestamp_seconds"].type == "gauge"
    values = {s.labels["pipeline"]: s.value for s in families["pipeline_duration_seconds"].samples}
    assert values == {"orders": 42.5, "payments": 12.0}


def test_freshness_numbers():
    f = m().freshness_seconds
    assert f(1730106000.0, 1730102400.0) == 3600
    assert f(100, 200) == 0
    assert math.isinf(f(100, None))


def test_freshness_datetime():
    now = datetime(2018, 8, 1, 12, tzinfo=timezone.utc)
    assert m().freshness_seconds(now, now - timedelta(hours=2, minutes=30)) == 9000
