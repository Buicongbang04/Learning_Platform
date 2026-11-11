import json
import sys

import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
DRIVER = ex.fixtures / "driver.py"
ORDER = {"path": "/orders/o1", "status": 200}


def scenario(tmp_path, name: str) -> dict:
    result = run_sandboxed([sys.executable, str(DRIVER), str(ex.path("resilient.py")), name], writable=[tmp_path], cwd=tmp_path, env={},
                           timeout=60)
    assert result.returncode == 0, f"Kịch bản {name} không chạy được:\n{result.stderr[-1500:]}"
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert "crash" not in data, f"Kịch bản {name} lỗi: {data['crash']}\n{data.get('trace', '')}"
    return data


def failed(data: dict, error: str, status=None) -> bool:
    return data.get("error") == error and (status is None or data.get("status") == status)


def test_transient_errors_are_retried(tmp_path):
    data = scenario(tmp_path, "transient")
    assert data.get("ok") == ORDER, f"503, 502 rồi 200 phải trả đơn hàng: {data}"
    assert data["requests"] == 3, data
    assert len(data["sleeps"]) == 2 and 0 <= data["sleeps"][0] <= 0.2 and 0 <= data["sleeps"][1] <= 0.4, \
        f"Chờ trước lần thử 1, 2 phải nằm trong [0; 0,2] và [0; 0,4] giây: {data['sleeps']}"


def test_gives_up_after_max_attempts(tmp_path):
    data = scenario(tmp_path, "exhausted")
    assert failed(data, "UpstreamError", 503), f"Hết lượt thử phải ném UpstreamError(503): {data}"
    assert data["requests"] == 4 and len(data["sleeps"]) == 3, data


def test_client_errors_are_not_retried(tmp_path):
    data = scenario(tmp_path, "not_found")
    assert failed(data, "UpstreamError", 404), data
    assert data["requests"] == 1 and data["sleeps"] == [], f"404 không được thử lại: {data}"
    assert data["state"] == "closed", f"404 là upstream vẫn trả lời bình thường, không làm mở breaker: {data}"


def test_server_bug_counts_for_breaker_but_not_retried(tmp_path):
    data = scenario(tmp_path, "server_bug")
    assert failed(data, "UpstreamError", 500), data
    assert data["requests"] == 1 and data["sleeps"] == [], f"500 không thử lại: {data}"
    assert data["state"] == "open", f"500 là lỗi của upstream, breaker ngưỡng 1 phải mở: {data}"


def test_retry_after_is_honoured(tmp_path):
    data = scenario(tmp_path, "retry_after")
    assert data.get("ok") == ORDER and data["requests"] == 2, data
    assert data["sleeps"] == [3.0], f"429 kèm Retry-After: 3 thì chờ đúng 3 giây: {data['sleeps']}"


def test_retry_after_beyond_deadline_gives_up(tmp_path):
    data = scenario(tmp_path, "retry_after_beyond_deadline")
    assert failed(data, "UpstreamError", 503), data
    assert data["requests"] == 1 and data["sleeps"] == [], f"Chờ 10 giây vượt deadline 5 giây: bỏ cuộc ngay, không ngủ: {data}"


def test_timeouts_and_resets_are_retried(tmp_path):
    data = scenario(tmp_path, "network")
    assert data.get("ok") == ORDER, f"Timeout, mất kết nối rồi 200 phải trả đơn hàng: {data}"
    assert data["requests"] == 3 and data["sleeps"] == 2, data


def test_deadline_caps_total_wait(tmp_path):
    data = scenario(tmp_path, "deadline")
    assert failed(data, "UpstreamError", 503), data
    assert data["sleeps"] == [1.0, 2.0] and data["requests"] == 3, \
        f"Deadline 3,5 giây: chờ 1, 2 rồi dừng vì lần chờ 4 giây sẽ vượt deadline: {data}"


def test_get_has_no_idempotency_key(tmp_path):
    data = scenario(tmp_path, "get_headers")
    assert data.get("ok") == ORDER and data["methods"] == ["GET", "GET"], data
    assert data["keys"] == [None, None], f"GET không gửi Idempotency-Key: {data['keys']}"


def test_attempt_timeout_follows_deadline(tmp_path):
    data = scenario(tmp_path, "attempt_timeouts")
    assert failed(data, "UpstreamError", 503) and data["requests"] == 2 and data["sleeps"] == [1.0], data
    assert data["timeouts"] == [2.0, 1.5], \
        f"Timeout mỗi lần thử là min(timeout, phần deadline còn lại): cần [2.0, 1.5], được {data['timeouts']}"


def test_full_jitter(tmp_path):
    data = scenario(tmp_path, "jitter")
    caps = data["caps"]
    for run in data["runs"]:
        assert len(run) == len(caps) and all(0 <= d <= c for d, c in zip(run, caps)), f"Mỗi lần chờ nằm trong [0, mức backoff]: {run}"
    assert data["again"] == data["runs"][0], "Cùng seed phải ra cùng dãy (dùng rng được truyền vào, không dùng random toàn cục)"
    assert data["runs"][0] != data["runs"][1] != data["runs"][2], "Seed khác phải ra dãy khác"
    assert all(abs(d - c) < 1e-6 for d, c in zip(data["top"], caps)), \
        f"Khi rng trả cận trên, delay phải bằng min(cap, base * 2^(attempt-1)): {data['top']} khác {caps}"


def test_breaker_opens_and_recovers(tmp_path):
    data = scenario(tmp_path, "breaker_opens")
    errors = [c.get("error") for c in data["calls"]]
    assert errors[:3] == ["UpstreamError"] * 3 and data["after_failures"] == "open", data
    assert errors[3] == "CircuitOpenError" and data["requests_while_open"] == 3, \
        f"Breaker mở thì không gửi request: {data}"
    assert data["before_reset"] == "open" and errors[4] == "CircuitOpenError", data
    assert data["after_reset"] == "half_open", data
    assert data["calls"][5].get("ok") == ORDER and data["after_trial"] == "closed" and data["requests"] == 4, data


def test_half_open_failure_reopens(tmp_path):
    data = scenario(tmp_path, "half_open_failure")
    errors = [c.get("error") for c in data["calls"]]
    assert errors == ["UpstreamError", "UpstreamError", "UpstreamError", "CircuitOpenError", "CircuitOpenError"], data
    assert data["state"] == "open" and data["requests"] == 3, f"Request thử ở half_open lỗi thì mở lại và đếm lại thời gian: {data}"


def test_half_open_allows_single_trial(tmp_path):
    data = scenario(tmp_path, "half_open_single_trial")
    assert data["first"] is True and data["blocked"] is False, data
    assert data["trials"] == [True, False, False], f"half_open chỉ cho một request thử: {data['trials']}"
    assert data["state"] == "closed" and data["after"] is True, data


def test_breaker_stops_retry_loop(tmp_path):
    data = scenario(tmp_path, "breaker_inside_retry")
    assert failed(data, "CircuitOpenError"), f"Breaker mở giữa vòng retry thì ném CircuitOpenError: {data}"
    assert data["requests"] == 2 and data["sleeps"] == 1 and data["state"] == "open", data


def test_payment_reuses_idempotency_key(tmp_path):
    data = scenario(tmp_path, "payment_idempotency")
    assert data["first"].get("ok") == {"path": "/payments", "status": 200}, data
    assert data["second"].get("ok") == {"path": "/payments", "status": 200}, data
    assert data["methods"] == ["POST"] * 4, data
    keys = data["keys"]
    assert all(keys) and len(set(keys[:3])) == 1, f"Ba lần gửi của một payment phải cùng Idempotency-Key: {keys}"
    assert keys[3] != keys[0], "Payment khác phải có key khác"
    assert data["bodies"][0] == {"order_id": "o1", "amount": 129.9} and data["bodies"][3] == {"order_id": "o2", "amount": 15.0}, data


def test_payment_conflict_not_retried(tmp_path):
    data = scenario(tmp_path, "payment_conflict")
    assert failed(data, "UpstreamError", 409) and data["requests"] == 1 and data["sleeps"] == [], data


@pytest.mark.parametrize("name", ["transient", "breaker_opens"])
def test_scenarios_are_deterministic(tmp_path, name):
    first = scenario(tmp_path, name)
    second = scenario(tmp_path, name)
    assert "NotImplementedError" not in json.dumps(first), f"Kịch bản {name} chưa chạy được: {first}"
    assert first == second, f"Cùng seed và đồng hồ giả phải ra cùng kết quả: {first} khác {second}"
