import json

from sqlalchemy import select

from olist_shop import db, seed, worker


def test_worker_empty_queue(fake_redis, engine):
    assert worker.run_once(fake_redis, engine) == 0


def test_worker_recompute_replaces_previous_result(fake_redis, engine, olist_dir):
    seed.load(engine, olist_dir)
    for _ in range(2):
        fake_redis.rpush(worker.QUEUE, json.dumps({"job_id": "j", "type": "recompute_revenue"}))
        assert worker.run_once(fake_redis, engine) == 1
    with engine.connect() as conn:
        rows = conn.execute(select(db.revenue_by_state)).all()
    assert len(rows) == 2


def test_worker_unknown_job_counted_as_failed(fake_redis, engine):
    before = worker.JOBS_FAILED._value.get()
    fake_redis.rpush(worker.QUEUE, json.dumps({"job_id": "j", "type": "nope"}))
    assert worker.run_once(fake_redis, engine) == 1
    assert worker.JOBS_FAILED._value.get() == before + 1


def test_worker_counts_processed(fake_redis, engine, olist_dir):
    seed.load(engine, olist_dir)
    before = worker.JOBS_PROCESSED._value.get()
    fake_redis.rpush(worker.QUEUE, json.dumps({"job_id": "j", "type": "recompute_revenue"}))
    worker.run_once(fake_redis, engine)
    assert worker.JOBS_PROCESSED._value.get() == before + 1


def test_seed_respects_limit_and_is_idempotent(engine, olist_dir):
    assert seed.load(engine, olist_dir, limit_orders=2) == {"orders": 2, "order_items": 3, "customers": 2}
    assert seed.load(engine, olist_dir, limit_orders=1) == {"orders": 1, "order_items": 2, "customers": 1}
    with engine.connect() as conn:
        assert len(conn.execute(select(db.orders)).all()) == 1


def test_worker_redis_timeout_longer_than_blpop():
    client = worker.make_redis("redis://localhost:1/0")
    assert client.connection_pool.connection_kwargs["socket_timeout"] > worker.BLPOP_TIMEOUT
