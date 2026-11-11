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
        self.failures = 0
        self.opened_at = None
        self.trial_in_flight = False

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if self.clock() - self.opened_at >= self.reset_timeout:
            return "half_open"
        return "open"

    def allow(self) -> bool:
        state = self.state
        if state == "closed":
            return True
        if state == "open" or self.trial_in_flight:
            return False
        self.trial_in_flight = True
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None
        self.trial_in_flight = False

    def record_failure(self) -> None:
        self.trial_in_flight = False
        if self.opened_at is not None:
            self.opened_at = self.clock()
            return
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = self.clock()


def backoff_delay(attempt: int, base: float, cap: float, rng: random.Random) -> float:
    return rng.uniform(0, min(cap, base * 2 ** (attempt - 1)))


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
        start = self.clock()
        status = 0
        for attempt in range(1, self.max_attempts + 1):
            if self.breaker is not None and not self.breaker.allow():
                raise CircuitOpenError(f"{method} {path}: circuit open")
            remaining = self.deadline - (self.clock() - start)
            retry_after = None
            try:
                status, answer_headers, payload = self._send(method, path, body, headers or {}, min(self.timeout, remaining))
            except OSError:
                status, answer_headers, payload = 0, {}, b""
            if 200 <= status < 300:
                if self.breaker is not None:
                    self.breaker.record_success()
                return json.loads(payload or b"null")
            if 400 <= status < 500 and status != 429:
                if self.breaker is not None:
                    self.breaker.record_success()
                raise UpstreamError(status, payload.decode(errors="replace")[:200])
            if self.breaker is not None:
                self.breaker.record_failure()
            if status and status not in RETRYABLE_STATUS:
                raise UpstreamError(status, payload.decode(errors="replace")[:200])
            if attempt == self.max_attempts:
                break
            if self.breaker is not None and self.breaker.state != "closed":
                raise CircuitOpenError(f"{method} {path}: circuit opened after attempt {attempt}")
            header = {k.lower(): v for k, v in answer_headers.items()}.get("retry-after", "")
            if status in (429, 503) and header.strip().isdigit():
                retry_after = float(header.strip())
            delay = retry_after if retry_after is not None else backoff_delay(attempt, self.base_delay, self.max_delay, self.rng)
            if self.clock() - start + delay >= self.deadline:
                break
            self.sleep(delay)
        raise UpstreamError(status, f"{method} {path}: gave up")

    def get_order(self, order_id: str) -> dict:
        return self._call("GET", f"/orders/{order_id}")

    def create_payment(self, order_id: str, amount: float) -> dict:
        key = uuid.uuid4().hex
        return self._call("POST", "/payments", {"order_id": order_id, "amount": amount}, {"Idempotency-Key": key})
