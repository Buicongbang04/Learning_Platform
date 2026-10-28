"""Giám sát pipeline: freshness, volume anomaly, p95 latency, error rate."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class Run:
    pipeline: str
    started_at: float
    duration_seconds: float
    rows: int
    status: str  # "success" | "failed"

    @property
    def finished_at(self) -> float:
        return self.started_at + self.duration_seconds


@dataclass(frozen=True)
class Alert:
    pipeline: str
    kind: str  # "freshness" | "volume" | "error_rate" | "latency"
    message: str


class PipelineMonitor:
    def __init__(
        self,
        freshness_sla: dict[str, float],
        z_threshold: float = 3.0,
        min_history: int = 5,
        error_rate_threshold: float = 0.2,
        error_window: int = 20,
        p95_threshold: dict[str, float] | None = None,
    ):
        self.freshness_sla = freshness_sla
        self.z_threshold = z_threshold
        self.min_history = min_history
        self.error_rate_threshold = error_rate_threshold
        self.error_window = error_window
        self.p95_threshold = p95_threshold or {}
        # TODO: cấu trúc lưu run

    def record(self, run: Run) -> None:
        raise NotImplementedError  # TODO

    def last_success(self, pipeline: str) -> float | None:
        raise NotImplementedError  # TODO

    def freshness(self, pipeline: str, now: float) -> float:
        raise NotImplementedError  # TODO

    def p95_duration(self, pipeline: str) -> float | None:
        raise NotImplementedError  # TODO

    def error_rate(self, pipeline: str) -> float:
        raise NotImplementedError  # TODO

    def volume_zscore(self, pipeline: str) -> float | None:
        raise NotImplementedError  # TODO

    def evaluate(self, now: float) -> list[Alert]:
        raise NotImplementedError  # TODO

    def to_prometheus(self, now: float) -> str:
        raise NotImplementedError  # TODO


_ = (math, statistics)
