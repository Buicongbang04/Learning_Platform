import json
import random
import time
import urllib.error
import urllib.request
import uuid

RETRYABLE_STATUS = {429, 502, 503, 504}


class CircuitOpenError(Exception):
    pass


class UpstreamError(Exception):
    def __init__(self, status: int, message: str = ""):
        super().__init__(f"upstream {status}: {message}")
        self.status = status


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0, clock=time.monotonic):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.clock = clock

    @property
    def state(self) -> str:
        # TODO: "closed", "open" hay "half_open" theo bảng trạng thái trong README
        raise NotImplementedError

    def allow(self) -> bool:
        # TODO: half_open chỉ cho đúng một request thử
        raise NotImplementedError

    def record_success(self) -> None:
        # TODO
        raise NotImplementedError

    def record_failure(self) -> None:
        # TODO
        raise NotImplementedError


def backoff_delay(attempt: int, base: float, cap: float, rng: random.Random) -> float:
    # TODO: full jitter
    raise NotImplementedError


class OlistClient:
    def __init__(self, base_url: str, *, breaker: CircuitBreaker | None = None, max_attempts: int = 4, base_delay: float = 0.2,
                 max_delay: float = 2.0, timeout: float = 1.0, deadline: float = 5.0, sleep=time.sleep, clock=time.monotonic,
                 rng: random.Random | None = None):
        self.base_url = base_url.rstrip("/")
        self.breaker = breaker
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.deadline = deadline
        self.sleep = sleep
        self.clock = clock
        self.rng = rng or random.Random()

    def _send(self, method: str, path: str, body: dict | None, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, method=method,
                                         headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as answer:
                return answer.status, dict(answer.headers), answer.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def _call(self, method: str, path: str, body: dict | None = None, headers: dict | None = None) -> dict:
        # TODO: vòng thử theo luật trong README (breaker, phân loại kết quả, Retry-After, backoff, deadline)
        raise NotImplementedError

    def get_order(self, order_id: str) -> dict:
        return self._call("GET", f"/orders/{order_id}")

    def create_payment(self, order_id: str, amount: float) -> dict:
        # TODO: POST /payments, body {"order_id", "amount"}, header Idempotency-Key
        raise NotImplementedError
