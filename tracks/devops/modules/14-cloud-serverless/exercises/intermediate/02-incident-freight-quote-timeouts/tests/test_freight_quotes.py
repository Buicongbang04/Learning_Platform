import json
import time
import uuid
from pathlib import Path

import pytest

import testkit
from testkit import DockerLab, Exercise, LambdaLab

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
TIMEOUT = 3
CONTRACT_LIMIT = 8


def record(order_id: str) -> dict:
    body = json.dumps({"order_id": order_id, "customer_zip_code_prefix": "01310"})
    return {"messageId": str(uuid.uuid4()), "receiptHandle": uuid.uuid4().hex, "body": body,
            "attributes": {"ApproximateReceiveCount": "1"}, "messageAttributes": {}, "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:us-east-1:000000000000:freight-quotes", "awsRegion": "us-east-1"}


def batch(size: int = 10) -> list[dict]:
    return [record(uuid.uuid4().hex) for _ in range(size)]


class Quotes:
    def __init__(self, base: str) -> None:
        self.base = base

    def reset(self, **config) -> None:
        import httpx

        response = httpx.post(f"{self.base}/reset", json=config, timeout=5, trust_env=False)
        assert response.status_code == 200, response.text

    def stats(self) -> dict:
        import httpx

        return httpx.get(f"{self.base}/stats", timeout=5, trust_env=False).json()

    def settled(self, timeout: float = 10) -> dict:
        deadline = time.monotonic() + timeout
        stats = self.stats()
        while stats["in_flight"] and time.monotonic() < deadline:
            time.sleep(0.2)
            stats = self.stats()
        return stats


@pytest.fixture(scope="module")
def lab():
    ex.require_image(testkit.LAMBDA_IMAGE, hint=f"Tải bằng: {testkit.LAMBDA_PULL}")
    with DockerLab() as lab:
        lab.start("quotes", testkit.LAMBDA_IMAGE, "/srv/quote_service.py", ports=[8080], mounts=[(FIXTURES, "/srv")],
                  entrypoint="python3")
        lab.wait_log("quotes", "quote service ready", timeout=30)
        quotes = Quotes(f"http://127.0.0.1:{lab.port('quotes', 8080)}")
        lab.wait_http("quotes", f"{quotes.base}/stats", timeout=30)
        yield lab, quotes


def worker(lab, handler_dir: Path, alias: str) -> LambdaLab:
    return LambdaLab(lab, handler_dir, "app.handler", env={"QUOTE_URL": "http://quotes:8080"}, timeout=TIMEOUT,
                     alias=alias, isolated=False)


@pytest.fixture(scope="module")
def fn(lab):
    docker, quotes = lab
    with worker(docker, ex.path("handler"), "freight") as fn:
        yield fn, quotes


def failed_ids(result) -> set[str]:
    assert isinstance(result, dict) and "errorMessage" not in result, f"Lambda lỗi: {str(result)[:400]}"
    assert "batchItemFailures" in result, f"Handler phải trả batchItemFailures, đang trả {str(result)[:400]}"
    return {item["itemIdentifier"] for item in result["batchItemFailures"]}


def order_of(item: dict) -> str:
    return json.loads(item["body"])["order_id"]


def test_incident_fixture_reproduces_symptom(lab):
    docker, quotes = lab
    quotes.reset()
    with worker(docker, FIXTURES / "incident", "incident") as fn:
        result = fn.invoke({"Records": batch()})
    assert "timed out" in str(result.get("errorMessage", "")), f"Bản sự cố phải tái hiện Task timed out: {str(result)[:300]}"
    quotes.settled()


def test_full_batch_finishes_in_time(fn):
    fn, quotes = fn
    quotes.reset()
    records = batch()
    started = time.monotonic()
    result = fn.invoke({"Records": records})
    elapsed = time.monotonic() - started
    assert failed_ids(result) == set(), f"Không record nào được báo lỗi khi dịch vụ báo giá khoẻ: {result}"
    stats = quotes.settled()
    calls = stats["calls"]
    assert {order_of(r) for r in records} == set(calls) and set(calls.values()) == {1}, \
        f"Mỗi đơn phải được hỏi giá đúng một lần trong một lần invoke: {calls}"
    assert stats["max_in_flight"] <= CONTRACT_LIMIT and stats["rejected"] == 0, \
        f"Dịch vụ báo giá nhận tối đa {CONTRACT_LIMIT} request đồng thời: đỉnh {stats['max_in_flight']}, bị từ chối {stats['rejected']}"
    assert elapsed < TIMEOUT - 0.5, f"Batch 10 đơn mất {elapsed:.1f}s, quá sát timeout {TIMEOUT}s"


def test_one_failing_order_does_not_fail_batch(fn):
    fn, quotes = fn
    records = batch()
    broken = order_of(records[3])
    quotes.reset(fail=[broken])
    result = fn.invoke({"Records": records})
    assert failed_ids(result) == {records[3]["messageId"]}, f"Chỉ đơn bị dịch vụ báo giá trả lỗi nằm trong batchItemFailures: {result}"
    quotes.settled()


def test_slow_downstream_returns_before_timeout(fn):
    fn, quotes = fn
    quotes.reset(delay=1.8)
    records = batch()
    result = fn.invoke({"Records": records})
    failed = failed_ids(result)
    ids = {r["messageId"] for r in records}
    stats = quotes.settled()
    assert failed and failed <= ids, f"Đơn chưa kịp báo giá trước timeout phải nằm trong batchItemFailures: {result}"
    unquoted = [r["messageId"] for r in records if r["messageId"] not in failed and order_of(r) not in stats["calls"]]
    assert not unquoted, f"Record báo thành công mà dịch vụ báo giá chưa từng nhận: {unquoted}"
    assert len(failed) < len(ids), "Đơn đã báo giá xong không được đẩy lại hàng đợi"
