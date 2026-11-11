import importlib.util
import json
import random
import sys
import traceback
from pathlib import Path

class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(round(float(seconds), 6))
        self.now += float(seconds)


class TopRandom(random.Random):
    def uniform(self, a, b):
        return b

    def random(self):
        return 1.0 - 1e-12


def load(path, name="resilient_under_test"):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FakeOlist = load(Path(__file__).with_name("fake_olist.py"), "fake_olist").FakeOlist


def call(fn, *args):
    try:
        return {"ok": fn(*args)}
    except Exception as error:
        return {"error": type(error).__name__, "status": getattr(error, "status", None)}


def client(m, server, clock, **options):
    options.setdefault("rng", random.Random(7))
    return m.OlistClient(server.url, sleep=clock.sleep, clock=clock, **options)


def scenario_transient(m):
    server, clock = FakeOlist({"/orders/o1": [503, 502, 200]}), FakeClock()
    result = call(client(m, server, clock, max_attempts=4, base_delay=0.2, max_delay=2.0).get_order, "o1")
    return {**result, "requests": server.count("/orders/o1"), "sleeps": clock.sleeps}


def scenario_exhausted(m):
    server, clock = FakeOlist({"/orders/o1": [503]}), FakeClock()
    result = call(client(m, server, clock, max_attempts=4, base_delay=0.2, max_delay=2.0).get_order, "o1")
    return {**result, "requests": server.count("/orders/o1"), "sleeps": clock.sleeps}


def scenario_not_found(m):
    server, clock = FakeOlist({"/orders/missing": [404, 200]}), FakeClock()
    breaker = m.CircuitBreaker(failure_threshold=1, reset_timeout=30, clock=clock)
    result = call(client(m, server, clock, breaker=breaker).get_order, "missing")
    return {**result, "requests": server.count("/orders/missing"), "sleeps": clock.sleeps, "state": breaker.state}


def scenario_server_bug(m):
    server, clock = FakeOlist({"/orders/o1": [500, 200]}), FakeClock()
    breaker = m.CircuitBreaker(failure_threshold=1, reset_timeout=30, clock=clock)
    result = call(client(m, server, clock, breaker=breaker).get_order, "o1")
    return {**result, "requests": server.count("/orders/o1"), "sleeps": clock.sleeps, "state": breaker.state}


def scenario_retry_after(m):
    server, clock = FakeOlist({"/orders/o1": [(429, {"Retry-After": "3"}), 200]}), FakeClock()
    result = call(client(m, server, clock, max_delay=2.0, deadline=5.0).get_order, "o1")
    return {**result, "requests": server.count("/orders/o1"), "sleeps": clock.sleeps}


def scenario_retry_after_beyond_deadline(m):
    server, clock = FakeOlist({"/orders/o1": [(503, {"Retry-After": "10"}), 200]}), FakeClock()
    result = call(client(m, server, clock, deadline=5.0).get_order, "o1")
    return {**result, "requests": server.count("/orders/o1"), "sleeps": clock.sleeps}


def scenario_network(m):
    server, clock = FakeOlist({"/orders/o1": ["slow", "reset", 200]}), FakeClock()
    result = call(client(m, server, clock, timeout=0.2, max_attempts=4).get_order, "o1")
    return {**result, "requests": server.count("/orders/o1"), "sleeps": len(clock.sleeps)}


def scenario_deadline(m):
    server, clock = FakeOlist({"/orders/o1": [503]}), FakeClock()
    options = {"max_attempts": 10, "base_delay": 1.0, "max_delay": 8.0, "deadline": 3.5, "rng": TopRandom()}
    result = call(client(m, server, clock, **options).get_order, "o1")
    return {**result, "requests": server.count("/orders/o1"), "sleeps": clock.sleeps}


def scenario_jitter(m):
    def series(seed):
        rng = random.Random(seed)
        return [m.backoff_delay(attempt, 0.5, 4.0, rng) for attempt in range(1, 9)]

    caps = [min(4.0, 0.5 * 2 ** (attempt - 1)) for attempt in range(1, 9)]
    runs = {seed: series(seed) for seed in (1, 2, 3)}
    return {"caps": caps, "runs": [runs[1], runs[2], runs[3]], "again": series(1),
            "top": [m.backoff_delay(attempt, 0.5, 4.0, TopRandom()) for attempt in range(1, 9)]}


def scenario_breaker_opens(m):
    server, clock = FakeOlist({"/orders/o1": [503, 503, 503, 200]}), FakeClock()
    breaker = m.CircuitBreaker(failure_threshold=3, reset_timeout=10, clock=clock)
    api = client(m, server, clock, breaker=breaker, max_attempts=1)
    calls = [call(api.get_order, "o1") for _ in range(4)]
    seen = {"after_failures": breaker.state, "requests_while_open": server.count("/orders/o1")}
    clock.now += 9.5
    seen["before_reset"] = breaker.state
    calls.append(call(api.get_order, "o1"))
    clock.now += 0.5
    seen["after_reset"] = breaker.state
    calls.append(call(api.get_order, "o1"))
    seen["after_trial"] = breaker.state
    return {"calls": calls, **seen, "requests": server.count("/orders/o1")}


def scenario_half_open_failure(m):
    server, clock = FakeOlist({"/orders/o1": [503]}), FakeClock()
    breaker = m.CircuitBreaker(failure_threshold=2, reset_timeout=5, clock=clock)
    api = client(m, server, clock, breaker=breaker, max_attempts=1)
    calls = [call(api.get_order, "o1") for _ in range(2)]
    clock.now += 5
    calls.append(call(api.get_order, "o1"))
    state = breaker.state
    calls.append(call(api.get_order, "o1"))
    clock.now += 4.9
    calls.append(call(api.get_order, "o1"))
    return {"calls": calls, "state": state, "requests": server.count("/orders/o1")}


def scenario_half_open_single_trial(m):
    clock = FakeClock()
    breaker = m.CircuitBreaker(failure_threshold=1, reset_timeout=5, clock=clock)
    first = breaker.allow()
    breaker.record_failure()
    blocked = breaker.allow()
    clock.now += 5
    trials = [breaker.allow(), breaker.allow(), breaker.allow()]
    breaker.record_success()
    return {"first": first, "blocked": blocked, "trials": trials, "state": breaker.state, "after": breaker.allow()}


def scenario_breaker_inside_retry(m):
    server, clock = FakeOlist({"/orders/o1": [503]}), FakeClock()
    breaker = m.CircuitBreaker(failure_threshold=2, reset_timeout=30, clock=clock)
    result = call(client(m, server, clock, breaker=breaker, max_attempts=4).get_order, "o1")
    return {**result, "requests": server.count("/orders/o1"), "sleeps": len(clock.sleeps), "state": breaker.state}


def scenario_payment_idempotency(m):
    server, clock = FakeOlist({"/payments": [503, "reset", 200, 200]}), FakeClock()
    api = client(m, server, clock, timeout=0.5, max_attempts=4)
    first = call(api.create_payment, "o1", 129.9)
    second = call(api.create_payment, "o2", 15.0)
    keys = [r["idempotency_key"] for r in server.requests]
    bodies = [json.loads(r["body"] or "null") for r in server.requests]
    return {"first": first, "second": second, "methods": [r["method"] for r in server.requests], "keys": keys, "bodies": bodies}


def scenario_payment_conflict(m):
    server, clock = FakeOlist({"/payments": [409, 200]}), FakeClock()
    result = call(client(m, server, clock).create_payment, "o1", 10.0)
    return {**result, "requests": server.count("/payments"), "sleeps": clock.sleeps}


def main():
    module = load(sys.argv[1])
    name = sys.argv[2]
    try:
        result = globals()[f"scenario_{name}"](module)
    except Exception as error:
        result = {"crash": f"{type(error).__name__}: {error}", "trace": traceback.format_exc()[-800:]}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
