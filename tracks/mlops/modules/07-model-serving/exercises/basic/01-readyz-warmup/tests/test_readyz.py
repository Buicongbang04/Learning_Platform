import threading
import time

import pytest
from fastapi.testclient import TestClient

from testkit import Exercise

ex = Exercise(__file__)


class FakeModel:
    def __init__(self, version=7, delay=0.0):
        self.version = version
        self.delay = delay
        self.calls = 0

    def predict(self, rows):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        return [4 + 2.6 * row[0] for row in rows]


@pytest.fixture
def service():
    return ex.module("service.py")


def gated(model, gate):
    def load():
        gate.wait(3)
        return model

    return load


def wait_ready(client, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if client.get("/readyz").status_code == 200:
            return
        time.sleep(0.02)
    pytest.fail("readyz không lên 200 sau khi model nạp xong")


def test_not_ready_until_model_loaded(service):
    gate = threading.Event()
    app = service.create_app(gated(FakeModel(), gate))
    with TestClient(app) as client:
        assert not gate.is_set()
        assert client.get("/healthz").status_code == 200, "healthz chỉ trả lời 'tiến trình còn sống', luôn 200"
        assert client.get("/readyz").status_code == 503, "readyz phải 503 khi model đang nạp (và khởi động không được chặn)"
        assert client.post("/predict", json={"rows": [[5, 8, 1]]}).status_code == 503
        gate.set()
        wait_ready(client)
        assert client.post("/predict", json={"rows": [[5, 8, 1]]}).status_code == 200


def test_readyz_waits_for_warmup(service):
    model = FakeModel()
    gate = threading.Event()
    gate.set()
    with TestClient(service.create_app(gated(model, gate))) as client:
        wait_ready(client)
        assert model.calls >= 3, f"Cần ít nhất 3 lần predict khởi động trước khi báo ready, mới có {model.calls}"


def test_readyz_stays_503_while_warmup_runs(service):
    model = FakeModel(delay=0.4)
    gate = threading.Event()
    gate.set()
    with TestClient(service.create_app(gated(model, gate))) as client:
        time.sleep(0.5)
        assert model.calls < 3
        assert client.get("/readyz").status_code == 503, "Warmup chưa xong (mới có %d lần) mà đã ready" % model.calls
        wait_ready(client, 10)
        assert model.calls >= 3


def test_load_failure_keeps_not_ready(service):
    def broken():
        raise RuntimeError("không thấy model")

    with TestClient(service.create_app(broken)) as client:
        time.sleep(0.3)
        assert client.get("/healthz").status_code == 200
        response = client.get("/readyz")
        assert response.status_code == 503
        assert "không thấy model" in response.text


def test_response_carries_model_version(service):
    gate = threading.Event()
    gate.set()
    with TestClient(service.create_app(gated(FakeModel(version=7), gate))) as client:
        wait_ready(client)
        assert client.get("/readyz").json()["model_version"] == 7
        body = client.post("/predict", json={"rows": [[5, 8, 1], [10, 9, 2]]}).json()
        assert body["model_version"] == 7
        assert body["predictions"] == pytest.approx([17.0, 30.0])


@pytest.mark.parametrize(
    "rows",
    [[], [[1, 2]], [[1, 2, 3, 4]], [[1, 25, 1]], [[1, -1, 1]], [["a", 8, 1]], [[1, 8, 1]] * 101],
)
def test_invalid_input_is_422(service, rows):
    gate = threading.Event()
    gate.set()
    with TestClient(service.create_app(gated(FakeModel(), gate))) as client:
        wait_ready(client)
        assert client.post("/predict", json={"rows": rows}).status_code == 422


def test_non_finite_numbers_are_422(service):
    gate = threading.Event()
    gate.set()
    with TestClient(service.create_app(gated(FakeModel(), gate))) as client:
        wait_ready(client)
        for literal in ("NaN", "Infinity", "1e999"):
            body = ('{"rows": [[%s, 8, 1]]}' % literal).encode()
            response = client.post("/predict", content=body, headers={"content-type": "application/json"})
            assert response.status_code == 422, literal


def test_predict_timeout_is_504(service):
    model = FakeModel()
    gate = threading.Event()
    gate.set()
    with TestClient(service.create_app(gated(model, gate), predict_timeout=0.2)) as client:
        wait_ready(client)
        model.delay = 1.5
        started = time.monotonic()
        response = client.post("/predict", json={"rows": [[5, 8, 1]]})
        assert response.status_code == 504
        assert time.monotonic() - started < 0.9, "504 phải trả về đúng hạn, không đợi model chạy xong"
