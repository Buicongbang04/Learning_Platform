"""Xuất metric pipeline theo Prometheus text exposition format."""

from __future__ import annotations

from datetime import datetime

FAMILIES = [
    # (tên metric, loại, help, khoá trong dict stats)
    ("pipeline_rows_processed_total", "counter", "Rows processed by the pipeline.", "rows_processed"),
    ("pipeline_last_success_timestamp_seconds", "gauge", "Unix time of the last successful run.", "last_success"),
    ("pipeline_duration_seconds", "gauge", "Duration of the last run in seconds.", "duration_seconds"),
]


def escape_label_value(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _fmt(value: float) -> str:
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, int):
        return str(value)
    return repr(float(value))


def render_metrics(stats: list[dict]) -> str:
    if not stats:
        return ""
    lines: list[str] = []
    for name, kind, help_text, key in FAMILIES:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {kind}")
        for row in stats:
            label = escape_label_value(row["pipeline"])
            lines.append(f'{name}{{pipeline="{label}"}} {_fmt(row[key])}')
    return "\n".join(lines) + "\n"


def _to_seconds(value: float | datetime) -> float:
    return value.timestamp() if isinstance(value, datetime) else float(value)


def freshness_seconds(now: float | datetime, last_success: float | datetime | None) -> float:
    if last_success is None:
        return float("inf")
    return max(0.0, _to_seconds(now) - _to_seconds(last_success))
