import json
import logging
import signal
import time

import redis
from prometheus_client import CollectorRegistry, Counter, start_http_server
from sqlalchemy import Engine, delete, func, insert, select
from sqlalchemy.exc import SQLAlchemyError

from olist_shop import db, log
from olist_shop.jobs import QUEUE, RECOMPUTE_REVENUE
from olist_shop.settings import Settings

logger = logging.getLogger("olist_shop.worker")

BLPOP_TIMEOUT = 5
REGISTRY = CollectorRegistry()
JOBS_PROCESSED = Counter("jobs_processed_total", "Số job xử lý xong", registry=REGISTRY)
JOBS_FAILED = Counter("jobs_failed_total", "Số job lỗi", registry=REGISTRY)


def recompute_revenue(engine: Engine) -> None:
    revenue = func.sum(db.order_items.c.price + db.order_items.c.freight_value)
    query = (
        select(db.customers.c.customer_state, revenue)
        .select_from(db.order_items)
        .join(db.orders, db.orders.c.order_id == db.order_items.c.order_id)
        .join(db.customers, db.customers.c.customer_id == db.orders.c.customer_id)
        .group_by(db.customers.c.customer_state)
    )
    with engine.begin() as conn:
        conn.execute(delete(db.revenue_by_state))
        conn.execute(insert(db.revenue_by_state).from_select(["state", "revenue"], query))


HANDLERS = {RECOMPUTE_REVENUE: recompute_revenue}


def handle(raw: bytes | str, engine: Engine) -> None:
    token = None
    try:
        job = json.loads(raw)
        token = log.request_id.set(str(job.get("job_id", "-")))
        HANDLERS[job["type"]](engine)
    except Exception:
        JOBS_FAILED.inc()
        logger.exception("job lỗi", extra={"raw": raw})
    else:
        JOBS_PROCESSED.inc()
        logger.info("job done", extra={"job_type": job["type"]})
    finally:
        if token is not None:
            log.request_id.reset(token)


def make_redis(url: str) -> redis.Redis:
    return redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=BLPOP_TIMEOUT + 5)


def ensure_schema(engine: Engine, attempts: int = 10, delay: float = 1.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            db.init(engine)
            return
        except SQLAlchemyError:
            if attempt == attempts:
                raise
            logger.warning("tạo bảng lỗi, thử lại", extra={"attempt": attempt}, exc_info=True)
            time.sleep(delay * attempt)


def run_once(redis_client: redis.Redis, engine: Engine) -> int:
    raw = redis_client.lpop(QUEUE)
    if raw is None:
        return 0
    handle(raw, engine)
    return 1


def main() -> None:
    settings = Settings()
    log.configure(settings.log_level)
    engine = db.make_engine(settings.database_url)
    ensure_schema(engine)
    redis_client = make_redis(settings.redis_url)
    start_http_server(settings.worker_metrics_port, registry=REGISTRY)
    stopping = False

    def stop(signum, _frame):
        nonlocal stopping
        stopping = True
        logger.info("nhận tín hiệu dừng", extra={"signal": signum})

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    logger.info("worker started", extra={"queue": QUEUE})
    while not stopping:
        try:
            item = redis_client.blpop([QUEUE], timeout=BLPOP_TIMEOUT)
        except redis.RedisError:
            logger.warning("mất kết nối redis, thử lại", exc_info=True)
            time.sleep(2)
            continue
        if item is not None:
            handle(item[1], engine)
    engine.dispose()
    logger.info("worker stopped")


if __name__ == "__main__":
    main()
