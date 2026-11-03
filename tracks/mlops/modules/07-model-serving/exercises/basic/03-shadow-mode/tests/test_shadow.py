import threading
import time

import pytest

from testkit import Exercise

ex = Exercise(__file__)


class Model:
    def __init__(self, version, offset=0.0, delay=0.0, error=None, mutate=False):
        self.version = version
        self.offset = offset
        self.delay = delay
        self.error = error
        self.mutate = mutate
        self.seen = []

    def predict(self, rows):
        self.seen.append(rows)
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        if self.mutate:
            rows[0][0] = -1
        return {"model_version": self.version, "predictions": [4 + 2.6 * row[0] + self.offset for row in rows]}


@pytest.fixture(scope="module")
def shadow_mod():
    return ex.module("shadow.py")


def runner(shadow_mod, primary, shadow):
    records = []
    lock = threading.Lock()

    def log(record):
        with lock:
            records.append(record)

    return shadow_mod.ShadowRunner(primary, shadow, log), records


def test_response_is_exactly_the_primary_response(shadow_mod):
    primary, shadow = Model(1), Model(2, offset=50)
    run, _ = runner(shadow_mod, primary, shadow)
    rows = [[5.0, 8, 1], [10.0, 9, 2]]
    assert run.predict("r1", rows) == {"model_version": 1, "predictions": [17.0, 30.0]}
    run.drain()


def test_shadow_prediction_is_logged_with_diff(shadow_mod):
    run, records = runner(shadow_mod, Model(1), Model(2, offset=3))
    run.predict("r1", [[5.0, 8, 1], [10.0, 9, 2]])
    run.drain()
    assert len(records) == 1
    record = records[0]
    assert record["request_id"] == "r1"
    assert record["primary_version"] == 1 and record["shadow_version"] == 2
    assert record["primary"] == pytest.approx([17.0, 30.0])
    assert record["shadow"] == pytest.approx([20.0, 33.0])
    assert record["max_abs_diff"] == pytest.approx(3.0)
    assert record["error"] is None


def test_shadow_error_does_not_fail_the_request(shadow_mod):
    run, records = runner(shadow_mod, Model(1), Model(2, error=ValueError("bad feature")))
    response = run.predict("r1", [[5.0, 8, 1]])
    run.drain()
    assert response["model_version"] == 1
    assert records[0]["shadow"] is None
    assert "ValueError" in records[0]["error"] and "bad feature" in records[0]["error"]


def test_primary_error_is_not_swallowed(shadow_mod):
    run, records = runner(shadow_mod, Model(1, error=RuntimeError("down")), Model(2))
    with pytest.raises(RuntimeError):
        run.predict("r1", [[5.0, 8, 1]])
    run.drain()
    assert records == [], "Primary lỗi thì không có gì để so sánh, đừng ghi log shadow"


def test_slow_shadow_does_not_delay_response(shadow_mod):
    run, records = runner(shadow_mod, Model(1), Model(2, delay=0.6))
    started = time.monotonic()
    run.predict("r1", [[5.0, 8, 1]])
    assert time.monotonic() - started < 0.4, "Shadow chậm không được làm chậm response"
    assert records == []
    run.drain(timeout=5)
    assert len(records) == 1


def test_shadow_cannot_corrupt_the_caller_rows(shadow_mod):
    run, records = runner(shadow_mod, Model(1), Model(2, mutate=True))
    rows = [[5.0, 8, 1]]
    first = run.predict("r1", rows)
    run.drain()
    assert rows == [[5.0, 8, 1]]
    assert first["predictions"] == pytest.approx([17.0])


def test_a_failing_log_sink_does_not_break_requests(shadow_mod):
    def log(record):
        raise OSError("disk full")

    run = shadow_mod.ShadowRunner(Model(1), Model(2), log)
    assert run.predict("r1", [[5.0, 8, 1]])["model_version"] == 1
    run.drain()


def test_many_requests_are_all_logged(shadow_mod):
    run, records = runner(shadow_mod, Model(1), Model(2, offset=1, delay=0.01))
    for index in range(40):
        run.predict(f"r{index}", [[float(index), 8, 1]])
    run.drain(timeout=10)
    assert sorted(record["request_id"] for record in records) == sorted(f"r{i}" for i in range(40))
