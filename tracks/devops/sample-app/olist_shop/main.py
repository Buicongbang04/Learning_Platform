import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from sqlalchemy import Engine, select
from sqlalchemy.exc import SQLAlchemyError

from olist_shop import db, log
from olist_shop.jobs import QUEUE, RECOMPUTE_REVENUE
from olist_shop.settings import Settings

logger = logging.getLogger("olist_shop.api")


def create_app(settings: Settings | None = None, engine: Engine | None = None,
               redis_client: redis.Redis | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = engine or db.make_engine(settings.database_url)
    redis_client = redis_client or redis.Redis.from_url(
        settings.redis_url, socket_connect_timeout=1, socket_timeout=1)

    registry = CollectorRegistry()
    requests_total = Counter("http_requests_total", "Số request HTTP",
                             ["method", "path", "status"], registry=registry)
    request_duration = Histogram("http_request_duration_seconds", "Thời gian xử lý request",
                                 ["method", "path"], registry=registry)
    jobs_enqueued = Counter("jobs_enqueued_total", "Số job đã đẩy vào hàng đợi", registry=registry)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        log.configure(settings.log_level)
        try:
            db.init(engine)
        except SQLAlchemyError:
            logger.exception("không tạo được bảng, /readyz sẽ báo db lỗi")
        yield
        engine.dispose()

    app = FastAPI(title="Olist Shop", version=settings.app_version, lifespan=lifespan)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = log.request_id.set(rid)
        start = time.perf_counter()
        status = 500
        try:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("lỗi không xử lý được")
                response = JSONResponse({"error": "internal server error"}, status_code=500)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            path = route.path if route is not None else "unmatched"
            requests_total.labels(request.method, path, str(status)).inc()
            request_duration.labels(request.method, path).observe(elapsed)
            logger.info("request", extra={"method": request.method, "path": path, "status": status,
                                          "duration_ms": round(elapsed * 1000, 2)})
            log.request_id.reset(token)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": settings.app_version}

    @app.get("/readyz")
    def readyz():
        result = {"db": "ok", "redis": "ok"}
        try:
            db.ping(engine)
        except SQLAlchemyError:
            logger.warning("db không sẵn sàng", exc_info=True)
            result["db"] = "error"
        try:
            redis_client.ping()
        except redis.RedisError:
            logger.warning("redis không sẵn sàng", exc_info=True)
            result["redis"] = "error"
        ok = all(v == "ok" for v in result.values())
        return JSONResponse(result, status_code=200 if ok else 503)

    @app.get("/orders/{order_id}")
    def get_order(order_id: str):
        with engine.connect() as conn:
            order = conn.execute(
                select(db.orders, db.customers.c.customer_state)
                .join(db.customers, db.customers.c.customer_id == db.orders.c.customer_id, isouter=True)
                .where(db.orders.c.order_id == order_id)
            ).mappings().first()
            if order is None:
                raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
            items = conn.execute(
                select(db.order_items).where(db.order_items.c.order_id == order_id)
                .order_by(db.order_items.c.order_item_id)
            ).mappings().all()
        total = round(sum(i["price"] + i["freight_value"] for i in items), 2)
        return {**order, "items": [dict(i) for i in items], "total": total}

    @app.get("/stats/revenue-by-state")
    def revenue_by_state():
        with engine.connect() as conn:
            rows = conn.execute(
                select(db.revenue_by_state.c.state, db.revenue_by_state.c.revenue)
                .order_by(db.revenue_by_state.c.revenue.desc())
            ).all()
        return [{"state": state, "revenue": round(revenue, 2)} for state, revenue in rows]

    @app.post("/jobs/recompute", status_code=202)
    def recompute():
        job_id = uuid.uuid4().hex
        try:
            redis_client.rpush(QUEUE, json.dumps({"job_id": job_id, "type": RECOMPUTE_REVENUE}))
        except redis.RedisError:
            logger.warning("không đẩy được job vào redis", exc_info=True)
            return JSONResponse({"error": "redis unavailable"}, status_code=503)
        jobs_enqueued.inc()
        logger.info("job enqueued", extra={"job_id": job_id, "job_type": RECOMPUTE_REVENUE})
        return {"job_id": job_id}

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
