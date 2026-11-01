import asyncio
import json
import math
import time

import httpx
import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)
URL = "http://llm.test/v1/chat/completions"


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("loadtest.ipynb")


def chunk(content=None, usage=None, role=False):
    delta = {"role": "assistant"} if role else ({"content": content} if content is not None else {})
    event = {"object": "chat.completion.chunk", "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
    if usage is not None:
        event = {"object": "chat.completion.chunk", "choices": [], "usage": usage}
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode()


def sse_server(pieces, delay=0.0, status=200, fail_after=None, seen=None):
    """Server SSE giả: mỗi mảnh chữ là một chunk, cách nhau `delay` giây."""

    async def handler(request):
        if seen is not None:
            seen.append(json.loads(request.content))
        if status >= 400:
            return httpx.Response(status, json={"error": "quá tải"})

        async def body():
            yield chunk(role=True)
            for i, piece in enumerate(pieces):
                if fail_after is not None and i == fail_after:
                    raise httpx.ReadError("mất kết nối giữa chừng")
                await asyncio.sleep(delay)
                yield chunk(piece)
            yield chunk(content="")
            yield chunk(usage={"prompt_tokens": 12, "completion_tokens": len(pieces)})
            yield b"data: [DONE]\n\n"
            yield chunk("sau DONE không được đếm")

        return httpx.Response(status, content=body(), headers={"content-type": "text/event-stream"})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def run(coro):
    return asyncio.run(coro)


# ---------- SSE ----------

def test_parse_sse_line(nb):
    assert nb.parse_sse_line('data: {"a": 1}') == {"a": 1}
    assert nb.parse_sse_line('  data:{"a": 2}  \n') == {"a": 2}
    assert nb.parse_sse_line("data: [DONE]") == "DONE"
    assert nb.parse_sse_line("") is None
    assert nb.parse_sse_line(": keep-alive") is None
    assert nb.parse_sse_line("event: ping") is None
    assert nb.parse_sse_line("data: {hỏng") is None


def test_stream_chat_records_tokens_and_usage(nb):
    seen = []

    async def go():
        async with sse_server(["Xin", " chào", " bạn"], delay=0.03, seen=seen) as client:
            return await nb.stream_chat(client, URL, {"model": "m", "messages": []}, t_arrival=None)

    t_before = time.perf_counter()
    rec = run(go())
    assert rec.ok and rec.error == ""
    assert len(rec.token_times) == 3, "chunk role, chunk rỗng, usage và mọi thứ sau DONE không phải token"
    assert rec.usage == {"prompt_tokens": 12, "completion_tokens": 3}
    assert seen[0]["stream"] is True and seen[0]["model"] == "m", "gửi payload kèm stream=True"
    assert rec.t_arrival == rec.t_send and t_before <= rec.t_send <= rec.t_first <= rec.t_end
    assert rec.t_first == rec.token_times[0]
    gaps = np.diff(rec.token_times)
    assert all(g >= 0.02 for g in gaps), "thời điểm token ghi lúc nhận, không phải lúc kết thúc"
    assert rec.t_first - rec.t_send >= 0.02


def test_stream_chat_keeps_given_arrival(nb):
    async def go():
        async with sse_server(["a"]) as client:
            return await nb.stream_chat(client, URL, {}, t_arrival=123.0)

    rec = run(go())
    assert rec.t_arrival == 123.0, "t_arrival truyền vào được giữ nguyên"


def test_stream_chat_http_error(nb):
    async def go():
        async with sse_server(["a"], status=503) as client:
            return await nb.stream_chat(client, URL, {})

    rec = run(go())
    assert not rec.ok and rec.error == "HTTP 503" and rec.token_times == [] and not math.isnan(rec.t_end)


def test_stream_chat_no_tokens_and_broken_stream(nb):
    async def empty():
        async with sse_server([]) as client:
            return await nb.stream_chat(client, URL, {})

    rec = run(empty())
    assert not rec.ok and rec.error == "không có token"

    async def broken():
        async with sse_server(["a", "b", "c"], fail_after=2) as client:
            return await nb.stream_chat(client, URL, {})

    rec = run(broken())
    assert not rec.ok and rec.error.startswith("ReadError") and len(rec.token_times) == 2
    assert not math.isnan(rec.t_end)


# ---------- sinh tải ----------

def test_poisson_arrivals(nb):
    a = nb.poisson_arrivals(2.0, 5, seed=1)
    rng = np.random.default_rng(1)
    assert np.allclose(a, np.cumsum(rng.exponential(0.5, size=5)))
    big = nb.poisson_arrivals(4.0, 20_000, seed=0)
    assert np.all(np.diff(big) > 0) and big[-1] / len(big) == pytest.approx(0.25, rel=0.03)
    for bad in [(0.0, 3), (1.0, 0)]:
        with pytest.raises(ValueError):
            nb.poisson_arrivals(*bad)


def fake_server(nb, service_s, slots=1):
    """Server giả xử lý tối đa `slots` request cùng lúc, mỗi request `service_s` giây."""
    state = {"inflight": 0, "max_inflight": 0, "calls": []}
    lock = asyncio.Semaphore(slots)

    async def send(i, t_arrival):
        t_send = time.perf_counter()
        state["calls"].append(i)
        state["inflight"] += 1
        state["max_inflight"] = max(state["max_inflight"], state["inflight"])
        async with lock:
            await asyncio.sleep(service_s)
            t = time.perf_counter()
        state["inflight"] -= 1
        return nb.RequestRecord(t_arrival=t_arrival, t_send=t_send, t_first=t, t_end=t, token_times=[t], ok=True)

    return send, state


def test_open_loop_follows_schedule(nb):
    send, state = fake_server(nb, 0.01, slots=10)
    arrivals = [0.0, 0.05, 0.10, 0.15]
    t0 = time.perf_counter()
    recs = run(nb.run_open_loop(send, arrivals))
    assert [r is not None for r in recs] == [True] * 4 and len(recs) == 4
    starts = [r.t_arrival - t0 for r in recs]
    assert starts == pytest.approx(arrivals, abs=0.02), "t_arrival là thời điểm theo lịch"
    assert all(r.t_send - r.t_arrival < 0.02 for r in recs), "không giới hạn đồng thời thì gửi đúng lúc đến"
    assert all(r.t_send >= r.t_arrival - 1e-6 for r in recs), "không gửi trước lịch"


def test_open_loop_client_queue(nb):
    send, state = fake_server(nb, 0.05, slots=10)
    recs = run(nb.run_open_loop(send, [0.0, 0.0, 0.0, 0.0], max_concurrency=1))
    waits = sorted(r.t_send - r.t_arrival for r in recs)
    assert waits == pytest.approx([0.0, 0.05, 0.10, 0.15], abs=0.03), "request thứ k chờ k lần thời gian phục vụ"
    assert state["max_inflight"] == 1
    assert [r.t_arrival for r in recs] == [recs[0].t_arrival] * 4


def test_open_loop_returns_in_index_order(nb):
    async def send(i, t_arrival):
        await asyncio.sleep(0.04 if i == 0 else 0.0)
        return i

    assert run(nb.run_open_loop(send, [0.0, 0.01, 0.02])) == [0, 1, 2]


def test_closed_loop_concurrency_and_accounting(nb):
    send, state = fake_server(nb, 0.02, slots=100)
    recs = run(nb.run_closed_loop(send, 3, 10))
    assert sorted(state["calls"]) == list(range(10)), "mỗi chỉ số gửi đúng một lần"
    assert state["max_inflight"] == 3, "đúng 3 request trong hệ thống cùng lúc"
    assert all(r is not None for r in recs) and len(recs) == 10
    assert all(abs(r.t_send - r.t_arrival) < 0.01 for r in recs), "closed loop không có hàng đợi phía client"


def test_closed_loop_on_single_slot_server_shows_server_queue(nb):
    send, _ = fake_server(nb, 0.03, slots=1)
    start = time.perf_counter()
    recs = run(nb.run_closed_loop(send, 4, 8))
    elapsed = time.perf_counter() - start
    assert elapsed == pytest.approx(8 * 0.03, abs=0.06), "server một slot: thông lượng không tăng theo đồng thời"
    e2e = sorted(r.t_end - r.t_arrival for r in recs)
    assert e2e[-1] > 3 * 0.03 * 0.9, "request chờ trong server dù client không thấy hàng đợi"


# ---------- summarize ----------

def rec(nb, arrival, send, tokens, ok=True):
    return nb.RequestRecord(t_arrival=arrival, t_send=send, t_first=tokens[0] if tokens else math.nan,
                            t_end=(tokens[-1] if tokens else send + 0.5), token_times=list(tokens), ok=ok,
                            error="" if ok else "HTTP 500")


def test_summarize(nb):
    records = [
        rec(nb, 0.0, 0.0, [0.5, 0.6, 0.8]),
        rec(nb, 1.0, 1.5, [2.0, 2.1]),
        rec(nb, 2.0, 2.0, [], ok=False),
        rec(nb, 3.0, 4.0, [5.0, 5.2, 5.3, 5.7]),
        rec(nb, 3.5, 3.5, [3.6, 5.6], ok=False),
    ]
    s = nb.summarize(records)
    assert (s["n"], s["ok"], s["errors"]) == (5, 3, 2), "stream đứt giữa chừng là lỗi dù đã có token"
    assert s["duration_s"] == pytest.approx(5.7)
    assert s["rps"] == pytest.approx(3 / 5.7) and s["tok_s"] == pytest.approx(9 / 5.7)
    assert s["ttft_p50"] == pytest.approx(1.0) and s["ttft_p95"] == pytest.approx(np.percentile([0.5, 1.0, 2.0], 95))
    assert s["e2e_p50"] == pytest.approx(1.1)
    assert s["itl_p50"] == pytest.approx(np.percentile([0.1, 0.2, 0.1, 0.2, 0.1, 0.4], 50))
    assert s["itl_p95"] == pytest.approx(np.percentile([0.1, 0.2, 0.1, 0.2, 0.1, 0.4], 95)), "gộp mọi khoảng giữa hai token"
    assert s["queue_p95"] == pytest.approx(np.percentile([0.0, 0.5, 1.0], 95))
    assert s["service_p50"] == pytest.approx(np.percentile([0.8, 0.6, 1.7], 50))
    assert nb.summarize(records, duration_s=10.0)["rps"] == pytest.approx(0.3)


def test_summarize_all_failed(nb):
    s = nb.summarize([rec(nb, 0.0, 0.0, [], ok=False)])
    assert s["ok"] == 0 and s["rps"] == 0.0 and math.isnan(s["ttft_p95"])
