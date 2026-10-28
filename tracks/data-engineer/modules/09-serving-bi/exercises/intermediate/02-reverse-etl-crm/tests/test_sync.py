import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def sync():
    return ex.module("sync.py")


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute((ex.fixtures / "olist_small.sql").read_text(encoding="utf-8"))
    yield con
    con.close()


class FakeCRM:
    """CRM giả: lưu contact theo external_id (upsert), giới hạn kích thước batch, có kịch bản lỗi."""

    def __init__(self, sync, max_batch=2, fail_plan=None):
        self.sync = sync
        self.max_batch = max_batch
        self.fail_plan = list(fail_plan or [])
        self.contacts = {}
        self.calls = 0
        self.received = []

    def upsert(self, batch):
        self.calls += 1
        if len(batch) > self.max_batch:
            raise self.sync.PermanentError(f"batch {len(batch)} > {self.max_batch}")
        if self.fail_plan:
            err = self.fail_plan.pop(0)
            if err is not None:
                raise err
        for record in batch:
            self.contacts[record["external_id"]] = dict(record)
            self.received.append(record["external_id"])
        return {"upserted": len(batch)}


class Sleeps(list):
    def __call__(self, seconds):
        self.append(seconds)


PAYLOAD = [
    {"external_id": "u1", "state": "SP", "total_orders": 2, "lifetime_value": 180.0,
     "last_order_date": "2018-08-02", "segment": "repeat"},
    {"external_id": "u2", "state": "SP", "total_orders": 1, "lifetime_value": 100.0,
     "last_order_date": "2018-08-01", "segment": "new"},
    {"external_id": "u3", "state": "RJ", "total_orders": 2, "lifetime_value": 450.0,
     "last_order_date": "2018-08-03", "segment": "vip"},
]


def test_build_customer_payload(con, sync):
    assert sync.build_customer_payload(con) == PAYLOAD


def test_record_hash(sync):
    a = {"x": 1, "y": "b"}
    assert sync.record_hash(a) == sync.record_hash({"y": "b", "x": 1})
    assert sync.record_hash(a) != sync.record_hash({"x": 2, "y": "b"})
    assert len(sync.record_hash(a)) == 64


def test_diff_records(sync):
    state = {"u1": sync.record_hash(PAYLOAD[0]), "u2": "stale-hash"}
    assert [r["external_id"] for r in sync.diff_records(PAYLOAD, state)] == ["u2", "u3"]


def test_batched(sync):
    assert sync.batched([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert sync.batched([], 3) == []
    with pytest.raises(ValueError):
        sync.batched([1], 0)


def test_retry_then_success(sync):
    crm = FakeCRM(sync, fail_plan=[sync.TransientError("429"), sync.TransientError("503"), None])
    sleeps = Sleeps()
    assert sync.send_with_retry(crm, PAYLOAD[:1], max_retries=3, base_delay=0.5, sleep=sleeps) == {"upserted": 1}
    assert sleeps == [0.5, 1.0]
    assert crm.calls == 3


def test_retry_exhausted(sync):
    crm = FakeCRM(sync, fail_plan=[sync.TransientError("429")] * 10)
    sleeps = Sleeps()
    with pytest.raises(sync.TransientError):
        sync.send_with_retry(crm, PAYLOAD[:1], max_retries=3, base_delay=0.5, sleep=sleeps)
    assert sleeps == [0.5, 1.0, 2.0]
    assert crm.calls == 4


def test_permanent_error_not_retried(sync):
    crm = FakeCRM(sync, fail_plan=[sync.PermanentError("400")])
    sleeps = Sleeps()
    with pytest.raises(sync.PermanentError):
        sync.send_with_retry(crm, PAYLOAD[:1], sleep=sleeps)
    assert sleeps == []
    assert crm.calls == 1


def test_run_sync_is_idempotent(sync):
    crm, state = FakeCRM(sync, max_batch=2), {}
    res = sync.run_sync(PAYLOAD, crm, state, batch_size=2, sleep=Sleeps())
    assert res == {"total": 3, "skipped": 0, "sent": 3, "failed": 0, "batches": 2, "failed_ids": []}
    assert crm.contacts["u3"]["segment"] == "vip"
    assert set(state) == {"u1", "u2", "u3"}

    calls = crm.calls
    res = sync.run_sync(PAYLOAD, crm, state, batch_size=2, sleep=Sleeps())
    assert res == {"total": 3, "skipped": 3, "sent": 0, "failed": 0, "batches": 0, "failed_ids": []}
    assert crm.calls == calls


def test_run_sync_only_changed(sync):
    crm, state = FakeCRM(sync), {}
    sync.run_sync(PAYLOAD, crm, state, batch_size=2, sleep=Sleeps())
    crm.received.clear()
    changed = [dict(r) for r in PAYLOAD]
    changed[1]["total_orders"], changed[1]["segment"] = 2, "repeat"
    res = sync.run_sync(changed, crm, state, batch_size=2, sleep=Sleeps())
    assert (res["sent"], res["skipped"]) == (1, 2)
    assert crm.received == ["u2"]
    assert crm.contacts["u2"]["segment"] == "repeat"


def test_partial_failure_resumes(sync):
    crm = FakeCRM(sync, fail_plan=[None, sync.PermanentError("400 bad field")])
    state = {}
    res = sync.run_sync(PAYLOAD, crm, state, batch_size=2, sleep=Sleeps())
    assert (res["sent"], res["failed"], res["failed_ids"]) == (2, 1, ["u3"])
    assert set(state) == {"u1", "u2"}

    crm.received.clear()
    res = sync.run_sync(PAYLOAD, crm, state, batch_size=2, sleep=Sleeps())
    assert (res["sent"], res["skipped"], res["failed"]) == (1, 2, 0)
    assert crm.received == ["u3"]
    assert len(crm.contacts) == 3


def test_transient_failures_recovered_inside_run(sync):
    crm = FakeCRM(sync, fail_plan=[sync.TransientError("429"), None, None])
    sleeps = Sleeps()
    res = sync.run_sync(PAYLOAD, crm, {}, batch_size=2, base_delay=0.1, sleep=sleeps)
    assert (res["sent"], res["failed"]) == (3, 0)
    assert sleeps == [0.1]


def test_end_to_end_from_duckdb(con, sync):
    crm, state = FakeCRM(sync, max_batch=100), {}
    res = sync.run_sync(sync.build_customer_payload(con), crm, state, sleep=Sleeps())
    assert res["sent"] == 3
    assert crm.contacts["u1"]["lifetime_value"] == 180.0
