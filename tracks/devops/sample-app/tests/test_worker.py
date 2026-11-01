import json

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from olist_shop import db, seed, worker

RECOMPUTE = json.dumps({"job_id": "j", "type": "recompute_revenue"})


def _sample(name: str) -> float:
    return worker.REGISTRY.get_sample_value(name) or 0.0


def _revenue(engine) -> list:
    with engine.connect() as conn:
        return sorted(conn.execute(select(db.revenue_by_state)).all())


@pytest.fixture
def computed(fake_redis, engine, olist_dir):
    seed.load(engine, olist_dir)
    fake_redis.rpush(worker.QUEUE, RECOMPUTE)
    assert worker.run_once(fake_redis, engine) == 1
    rows = _revenue(engine)
    assert rows
    return rows


def test_worker_empty_queue(fake_redis, engine):
    assert worker.run_once(fake_redis, engine) == 0


def test_worker_recompute_replaces_previous_result(fake_redis, engine, olist_dir):
    seed.load(engine, olist_dir)
    for _ in range(2):
        fake_redis.rpush(worker.QUEUE, RECOMPUTE)
        assert worker.run_once(fake_redis, engine) == 1
    with engine.connect() as conn:
        rows = conn.execute(select(db.revenue_by_state)).all()
    assert len(rows) == 2


def test_worker_unknown_job_counted_as_failed(fake_redis, engine):
    before = _sample("jobs_failed_total")
    fake_redis.rpush(worker.QUEUE, json.dumps({"job_id": "j", "type": "nope"}))
    assert worker.run_once(fake_redis, engine) == 1
    assert _sample("jobs_failed_total") == before + 1


def test_worker_counts_processed(fake_redis, engine, olist_dir):
    seed.load(engine, olist_dir)
    before = _sample("jobs_processed_total")
    fake_redis.rpush(worker.QUEUE, RECOMPUTE)
    worker.run_once(fake_redis, engine)
    assert _sample("jobs_processed_total") == before + 1


def test_worker_non_json_payload_fails_without_touching_data(fake_redis, engine, computed):
    before = _sample("jobs_failed_total")
    fake_redis.rpush(worker.QUEUE, b"not json {")
    assert worker.run_once(fake_redis, engine) == 1
    assert _sample("jobs_failed_total") == before + 1
    assert _revenue(engine) == computed


def test_worker_recompute_on_broken_db_fails(fake_redis, broken_engine, engine, computed):
    before = _sample("jobs_failed_total")
    fake_redis.rpush(worker.QUEUE, RECOMPUTE)
    assert worker.run_once(fake_redis, broken_engine) == 1
    assert _sample("jobs_failed_total") == before + 1
    assert _revenue(engine) == computed


def test_worker_recompute_rolls_back_midway(fake_redis, engine, computed):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE order_items"))
    before = _sample("jobs_failed_total")
    fake_redis.rpush(worker.QUEUE, RECOMPUTE)
    assert worker.run_once(fake_redis, engine) == 1
    assert _sample("jobs_failed_total") == before + 1
    assert _revenue(engine) == computed


def test_worker_schema_init_retries_then_keeps_going(monkeypatch, fake_redis, engine, olist_dir):
    real_init = db.init
    calls = []

    def flaky_init(e):
        calls.append(e)
        if len(calls) == 1:
            raise IntegrityError("CREATE TABLE", {}, Exception("duplicate key pg_type_typname_nsp_index"))
        real_init(e)

    monkeypatch.setattr(db, "init", flaky_init)
    worker.ensure_schema(engine, attempts=3, delay=0)
    assert len(calls) == 2
    seed.load(engine, olist_dir)
    fake_redis.rpush(worker.QUEUE, RECOMPUTE)
    assert worker.run_once(fake_redis, engine) == 1
    assert _revenue(engine)


def test_worker_schema_init_gives_up_after_attempts(monkeypatch, engine):
    def always_fail(e):
        raise IntegrityError("CREATE TABLE", {}, Exception("boom"))

    monkeypatch.setattr(db, "init", always_fail)
    with pytest.raises(IntegrityError):
        worker.ensure_schema(engine, attempts=2, delay=0)


def test_seed_respects_limit_and_is_idempotent(engine, olist_dir):
    assert seed.load(engine, olist_dir, limit_orders=2) == {"orders": 2, "order_items": 3, "customers": 2}
    assert seed.load(engine, olist_dir, limit_orders=1) == {"orders": 1, "order_items": 2, "customers": 1}
    with engine.connect() as conn:
        assert len(conn.execute(select(db.orders)).all()) == 1


def test_worker_redis_timeout_longer_than_blpop():
    client = worker.make_redis("redis://localhost:1/0")
    assert client.connection_pool.connection_kwargs["socket_timeout"] > worker.BLPOP_TIMEOUT
