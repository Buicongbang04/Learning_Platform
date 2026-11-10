import json
import logging
import os
import warnings
from contextlib import contextmanager

ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"
CARRIER = "otel"


class _NoSpan:
    def is_recording(self) -> bool:
        return False

    def set_attribute(self, key: str, value) -> None:
        pass

    def update_name(self, name: str) -> None:
        pass


NO_SPAN = _NoSpan()


class Tracer:
    """Trace và log OTLP (gRPC) của một tiến trình. Chỉ bật khi có `OTEL_EXPORTER_OTLP_ENDPOINT`; không có biến này
    thì span là no-op, không import OpenTelemetry, không mở kết nối nào."""

    def __init__(self, service_name: str, version: str = "dev", *, enabled: bool | None = None) -> None:
        self.enabled = bool(os.environ.get(ENDPOINT)) if enabled is None else enabled
        self._tracer = None
        self._providers: list = []
        self._handler: logging.Handler | None = None
        if self.enabled:
            self._start(service_name, version)

    def _start(self, service_name: str, version: str) -> None:
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        from olist_shop.log import JsonFormatter

        attributes = {"service.version": version}
        if not os.environ.get("OTEL_SERVICE_NAME"):
            attributes["service.name"] = service_name
        resource = Resource.create(attributes)
        traces = TracerProvider(resource=resource)
        traces.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        logs = LoggerProvider(resource=resource)
        logs.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            handler = LoggingHandler(logger_provider=logs)
        handler.setFormatter(JsonFormatter())
        handler.addFilter(lambda record: not record.name.startswith("opentelemetry"))
        self._tracer = traces.get_tracer("olist_shop", version)
        self._providers = [traces, logs]
        self._handler = handler

    def attach_logs(self) -> None:
        if self._handler is not None and self._handler not in logging.getLogger().handlers:
            logging.getLogger().addHandler(self._handler)

    @contextmanager
    def span(self, name: str, *, kind: str = "internal", parent=None, attributes: dict | None = None):
        if self._tracer is None:
            yield NO_SPAN
            return
        with self._tracer.start_as_current_span(name, context=parent, kind=_kind(kind), attributes=attributes) as span:
            yield span

    def inject(self) -> dict[str, str]:
        carrier: dict[str, str] = {}
        if self._tracer is not None:
            from opentelemetry import propagate

            propagate.inject(carrier)
        return carrier

    def extract(self, carrier):
        if self._tracer is None or not carrier:
            return None
        from opentelemetry import propagate

        return propagate.extract(carrier)

    def extract_job(self, raw: bytes | str):
        try:
            job = json.loads(raw)
        except (TypeError, ValueError):
            return None
        carrier = job.get(CARRIER) if isinstance(job, dict) else None
        return self.extract(carrier) if isinstance(carrier, dict) else None

    def instrument_engine(self, engine) -> None:
        if self._tracer is None:
            return
        from sqlalchemy import event

        dialect = engine.dialect.name
        namespace = engine.url.database if dialect != "sqlite" else "main"
        base = {"db.system.name": dialect, "db.namespace": namespace}
        if engine.url.host:
            base.update({"server.address": engine.url.host, "server.port": engine.url.port or 5432})

        def before(conn, cursor, statement, parameters, context, executemany):
            operation = statement.split(None, 1)[0].upper() if statement.strip() else "QUERY"
            context._olist_span = self._tracer.start_span(
                f"{operation} {namespace}", kind=_kind("client"),
                attributes={**base, "db.operation.name": operation, "db.query.text": statement})

        def after(conn, cursor, statement, parameters, context, executemany):
            span = getattr(context, "_olist_span", None)
            if span is not None:
                span.end()

        def errored(exception_context):
            span = getattr(exception_context.execution_context, "_olist_span", None)
            if span is not None:
                failed(span, exception_context.original_exception)
                span.end()

        event.listen(engine, "before_cursor_execute", before)
        event.listen(engine, "after_cursor_execute", after)
        event.listen(engine, "handle_error", errored)

    def shutdown(self) -> None:
        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)
        for provider in self._providers:
            provider.shutdown()
        self._providers = []


def _kind(name: str):
    from opentelemetry.trace import SpanKind

    return SpanKind[name.upper()]


DISABLED = Tracer("olist-shop", enabled=False)


def setup(service_name: str, version: str = "dev") -> Tracer:
    return Tracer(service_name, version)


def failed(span, error: BaseException | None = None) -> None:
    if not span.is_recording():
        return
    from opentelemetry.trace import Status, StatusCode

    if error is not None:
        span.record_exception(error)
    span.set_status(Status(StatusCode.ERROR, type(error).__name__ if error is not None else None))
