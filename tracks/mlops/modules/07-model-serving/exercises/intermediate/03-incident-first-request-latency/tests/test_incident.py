import importlib.util
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
ROWS = [[5.0, 8, 12], [12.0, 17, 100]]
LIMIT = 0.15


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def timed_requests(client, count):
    latencies = []
    for _ in range(count):
        started = time.perf_counter()
        response = client.post("/predict", json={"rows": ROWS})
        latencies.append(time.perf_counter() - started)
        assert response.status_code == 200
    return latencies


def wait_ready(client, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if client.get("/readyz").status_code == 200:
            return
        time.sleep(0.02)
    pytest.fail("/readyz không lên 200")


def p99(values):
    ordered = sorted(values)
    return ordered[max(0, -(-99 * len(ordered) // 100) - 1)]


def test_incident_service_reproduces_the_symptom():
    module = load(FIXTURES / "service_incident.py", "incident_service")
    with TestClient(module.create_app()) as client:
        wait_ready(client)
        latencies = timed_requests(client, 30)
    assert latencies[0] > 0.4, "Bản lúc sự cố phải chậm ở request đầu tiên"
    assert sorted(latencies[1:])[len(latencies) // 2] < 0.05, "...và bình thường từ request thứ hai"
    assert p99(latencies) > 0.4


def test_first_requests_after_ready_are_fast():
    module = load(ex.path("service.py"), "fresh_service")
    with TestClient(module.create_app()) as client:
        wait_ready(client)
        latencies = timed_requests(client, 30)
    assert latencies[0] < LIMIT, f"Request đầu tiên sau khi ready mất {latencies[0] * 1000:.0f} ms (ngưỡng {LIMIT * 1000:.0f} ms)"
    assert p99(latencies) < LIMIT, f"p99 của 30 request đầu: {p99(latencies) * 1000:.0f} ms"


def test_predictions_are_unchanged():
    module = load(ex.path("service.py"), "fresh_service")
    with TestClient(module.create_app()) as client:
        wait_ready(client)
        body = client.post("/predict", json={"rows": ROWS}).json()
    assert body["model_version"] == 3
    assert body["predictions"] == pytest.approx([17.0 + 3.0 + 0.35 * (12 % 7), 35.2 + 3.0 + 0.35 * (100 % 7)])


def test_readyz_is_never_200_before_the_zone_table_is_built(monkeypatch):
    module = load(ex.path("service.py"), "fresh_service")
    state = {"calls": 0, "done": False}
    original = module.build_zone_table

    def spy():
        state["calls"] += 1
        table = original()
        state["done"] = True
        return table

    monkeypatch.setattr(module, "build_zone_table", spy)
    with TestClient(module.create_app()) as client:
        end = time.monotonic() + 5
        while time.monotonic() < end:
            if client.get("/readyz").status_code == 200:
                assert state["done"], "/readyz báo 200 khi bảng zone chưa dựng xong"
                break
            time.sleep(0.02)
        else:
            pytest.fail("/readyz không lên 200")
        timed_requests(client, 10)
    assert state["calls"] == 1, f"build_zone_table phải chạy đúng 1 lần mỗi tiến trình, đã chạy {state['calls']} lần"


def test_the_expensive_table_is_still_built_not_removed(monkeypatch):
    module = load(ex.path("service.py"), "fresh_service")
    calls = []
    monkeypatch.setattr(module, "build_zone_table", lambda: calls.append(1) or {12: 1.75, 100: 0.7})
    with TestClient(module.create_app()) as client:
        wait_ready(client)
        timed_requests(client, 3)
    assert calls == [1], "Bảng zone vẫn phải do build_zone_table dựng (không được bỏ hay thay bằng giá trị cứng)"
