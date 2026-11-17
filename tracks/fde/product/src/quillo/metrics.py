"""Chỉ số Prometheus ở `GET /metrics` (không cần auth, chỉ có số đếm, không có nội dung tài liệu).

`quillo_documents`, `quillo_chunks`, `quillo_model_up{kind}` đo lúc scrape; database không trả lời thì hai số đầu là NaN.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.core import GaugeMetricFamily

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
ASK_BUCKETS = (0.5, 1, 2, 4, 8, 15, 30, 60, 120, 300)
UNMATCHED = "unmatched"


class _State:
    def __init__(self, counts: Callable[[], tuple[int, int] | None], models: dict[str, Callable[[], bool]]) -> None:
        self.counts = counts
        self.models = models

    def collect(self):
        with ThreadPoolExecutor(max_workers=1 + len(self.models)) as pool:
            counts = pool.submit(self.counts)
            up = {kind: pool.submit(check) for kind, check in self.models.items()}
            documents, chunks = counts.result() or (float("nan"), float("nan"))
            model_up = GaugeMetricFamily("quillo_model_up", "1 khi model server trả /health 200", labels=["kind"])
            for kind, future in up.items():
                model_up.add_metric([kind], 1.0 if future.result() else 0.0)
        yield GaugeMetricFamily("quillo_documents", "Số tài liệu trong database", value=documents)
        yield GaugeMetricFamily("quillo_chunks", "Số đoạn (chunk) đã embed", value=chunks)
        yield model_up


class Metrics:
    def __init__(self, counts: Callable[[], tuple[int, int] | None], models: dict[str, Callable[[], bool]]) -> None:
        self.registry = CollectorRegistry(auto_describe=False)
        self.requests = Counter("quillo_requests_total", "Số request theo route và mã trạng thái", ["route", "status"],
                                registry=self.registry)
        self.ask_seconds = Histogram("quillo_ask_seconds", "Thời gian trả lời /api/ask và /ui/ask (giây)",
                                     buckets=ASK_BUCKETS, registry=self.registry)
        self.registry.register(_State(counts, models))

    def observe_request(self, route: str | None, status: int) -> None:
        """`route` là mẫu đường dẫn (vd. `/api/ask`), không phải URL thật, để số chuỗi chỉ số không tăng theo URL lạ."""
        self.requests.labels(route or UNMATCHED, str(status)).inc()

    def render(self) -> bytes:
        return generate_latest(self.registry)
