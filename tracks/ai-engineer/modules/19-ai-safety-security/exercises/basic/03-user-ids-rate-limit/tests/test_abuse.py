import hashlib
import hmac
import json
import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
SECRET = b"bi-mat-cua-server"


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def tick(self, dt):
        self.t += dt


@pytest.fixture(scope="module")
def ab():
    return ex.module("abuse.py")


# ---------- end-user ID ----------


def test_user_key_format_and_keyed(ab):
    k = ab.user_key("an.nguyen@vidu.vn", SECRET)
    assert re.fullmatch(r"u_[0-9a-f]{24}", k)
    expected = "u_" + hmac.new(SECRET, b"an.nguyen@vidu.vn", hashlib.sha256).hexdigest()[:24]
    assert k == expected
    assert ab.user_key("  AN.Nguyen@VIDU.vn ", SECRET) == k, "cùng người dùng viết khác hoa thường, khoảng trắng"
    assert ab.user_key("an.nguyen@vidu.vn", b"khac") != k
    assert hashlib.sha256(b"an.nguyen@vidu.vn").hexdigest()[:24] not in k, "băm có khoá, không phải SHA-256 trần"


def test_user_key_rejects_empty(ab):
    with pytest.raises(ValueError):
        ab.user_key("a@b.vn", b"")
    with pytest.raises(ValueError):
        ab.user_key("   ", SECRET)


# ---------- token bucket ----------


def test_bucket_burst_then_refill(ab):
    clock = Clock()
    b = ab.TokenBucket(rate_per_s=0.5, capacity=3, clock=clock)
    assert [b.allow("u1") for _ in range(4)] == [True, True, True, False]
    assert b.retry_after("u1") == pytest.approx(2.0)
    clock.tick(1.9)
    assert not b.allow("u1")
    clock.tick(0.1)
    assert b.allow("u1")
    assert not b.allow("u1")


def test_bucket_keys_are_independent_and_capped(ab):
    clock = Clock()
    b = ab.TokenBucket(rate_per_s=1, capacity=2, clock=clock)
    assert b.allow("a") and b.allow("a") and not b.allow("a")
    assert b.allow("b"), "mỗi người dùng một bucket"
    clock.tick(3600)
    assert [b.allow("a") for _ in range(3)] == [True, True, False], "nghỉ lâu cũng chỉ đầy tới capacity"


def test_bucket_cost_and_failed_request_does_not_consume(ab):
    clock = Clock()
    b = ab.TokenBucket(rate_per_s=1, capacity=5, clock=clock)
    assert b.allow("u", cost=4)
    assert not b.allow("u", cost=2)
    assert b.allow("u", cost=1), "lần bị từ chối không được trừ token"
    assert b.retry_after("u", cost=10) == float("inf")
    with pytest.raises(ValueError):
        ab.TokenBucket(rate_per_s=0, capacity=1, clock=clock)


# ---------- abuse tracker ----------


def test_tracker_bans_after_strikes_in_window(ab):
    clock = Clock()
    t = ab.AbuseTracker(strikes=3, window_s=60, ban_s=100, clock=clock)
    t.record("u", "input:harassment")
    clock.tick(10)
    t.record("u", "input:harassment")
    assert not t.banned("u")
    assert t.history("u") == ["input:harassment", "input:harassment"]
    clock.tick(10)
    t.record("u", "output:violence")
    assert t.banned("u")
    assert t.history("u") == [], "bắt đầu bị cấm thì xoá đếm"
    clock.tick(99)
    assert t.banned("u")
    clock.tick(1)
    assert not t.banned("u")


def test_tracker_window_expires(ab):
    clock = Clock()
    t = ab.AbuseTracker(strikes=3, window_s=60, ban_s=100, clock=clock)
    t.record("u", "a")
    clock.tick(30)
    t.record("u", "b")
    clock.tick(30)
    t.record("u", "c")
    assert not t.banned("u"), "lần đầu đã quá 60 giây"
    assert t.history("u") == ["b", "c"]


def test_tracker_escalates(ab):
    clock = Clock()
    t = ab.AbuseTracker(strikes=2, window_s=60, ban_s=100, clock=clock)
    t.record("u", "a"); t.record("u", "b")
    clock.tick(100)
    assert not t.banned("u")
    t.record("u", "a"); t.record("u", "b")
    clock.tick(199)
    assert t.banned("u"), "lần cấm thứ hai dài gấp đôi"
    clock.tick(1)
    assert not t.banned("u")
    assert not t.banned("người-khác")


# ---------- pipeline ----------


def make(ab, clock, moderate, replies=None):
    calls = []

    def llm(messages, user):
        calls.append((messages, user))
        return (replies or {}).get(messages[-1]["content"], "Đây là câu trả lời.")

    return calls, dict(secret=SECRET, llm=llm, moderate=moderate,
                       limiter=ab.TokenBucket(rate_per_s=0.1, capacity=5, clock=clock),
                       tracker=ab.AbuseTracker(strikes=2, window_s=600, ban_s=300, clock=clock), log=[])


def moderate(text):
    return ["harassment"] if "đồ ngu" in text else (["violence"] if "đánh chết" in text else [])


def test_pipeline_ok_passes_hashed_user(ab):
    clock = Clock()
    calls, kw = make(ab, clock, moderate)
    r = ab.handle("minh@vidu.vn", "Giờ mở cửa?", **kw)
    assert r.status == "ok" and r.reply == "Đây là câu trả lời." and r.flags == []
    assert calls == [([{"role": "user", "content": "Giờ mở cửa?"}], ab.user_key("minh@vidu.vn", SECRET))]
    assert "minh@vidu.vn" not in json.dumps(kw["log"], ensure_ascii=False), "log không chứa định danh thật"
    assert kw["log"] == [{"user": ab.user_key("minh@vidu.vn", SECRET), "status": "ok", "flags": []}]


def test_pipeline_blocks_input_without_calling_llm(ab):
    clock = Clock()
    calls, kw = make(ab, clock, moderate)
    r = ab.handle("x@vidu.vn", "mày là đồ ngu", **kw)
    assert r.status == "blocked_input" and r.flags == ["harassment"] and r.reply == ab.REFUSAL
    assert calls == []
    assert kw["tracker"].history(ab.user_key("x@vidu.vn", SECRET)) == ["input:harassment"]


def test_pipeline_blocks_output(ab):
    clock = Clock()
    calls, kw = make(ab, clock, moderate, replies={"kể chuyện": "rồi hắn đánh chết con mèo"})
    r = ab.handle("y@vidu.vn", "kể chuyện", **kw)
    assert r.status == "blocked_output" and r.flags == ["violence"]
    assert r.reply == ab.REFUSAL, "không trả câu trả lời bị chặn cho người dùng"
    assert len(calls) == 1
    assert kw["tracker"].history(ab.user_key("y@vidu.vn", SECRET)) == ["output:violence"]


def test_pipeline_ban_and_rate_limit(ab):
    clock = Clock()
    calls, kw = make(ab, clock, moderate)
    ab.handle("z@vidu.vn", "đồ ngu", **kw)
    ab.handle("z@vidu.vn", "đồ ngu", **kw)
    r = ab.handle("z@vidu.vn", "Giờ mở cửa?", **kw)
    assert r.status == "banned" and calls == []
    statuses = [ab.handle("w@vidu.vn", f"câu {i}", **kw).status for i in range(6)]
    assert statuses == ["ok"] * 5 + ["rate_limited"]
    assert len(calls) == 5
    clock.tick(301)
    assert ab.handle("z@vidu.vn", "Giờ mở cửa?", **kw).status == "ok"
    assert [e["status"] for e in kw["log"]] == ["blocked_input", "blocked_input", "banned"] + ["ok"] * 5 + ["rate_limited", "ok"]


def test_banned_user_does_not_consume_rate_limit(ab):
    clock = Clock()
    calls, kw = make(ab, clock, moderate)
    key = ab.user_key("q@vidu.vn", SECRET)
    kw["tracker"].record(key, "x"); kw["tracker"].record(key, "y")
    for _ in range(10):
        assert ab.handle("q@vidu.vn", "hi", **kw).status == "banned"
    clock.tick(301)
    assert [ab.handle("q@vidu.vn", "hi", **kw).status for _ in range(5)] == ["ok"] * 5
