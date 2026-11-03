import asyncio
import time

import numpy as np
import pytest

import segkit
from testkit import Exercise

ex = Exercise(__file__)


def batcher_cls():
    return ex.module("batcher.py").DynamicBatcher


def total(batch):
    return batch.reshape(len(batch), -1).sum(axis=1)


def test_each_request_gets_its_own_result():
    Batcher = batcher_cls()

    async def scenario():
        rng = np.random.default_rng(0)

        async def one(b, i):
            await asyncio.sleep(float(rng.uniform(0, 0.02)))
            return i, await b.submit(np.full((2, 2), float(i)))

        async with Batcher(total, max_batch_size=8, max_wait_ms=5) as b:
            return await asyncio.gather(*(one(b, i) for i in range(50))), b.batch_sizes

    results, sizes = asyncio.run(scenario())
    for i, value in results:
        assert value == pytest.approx(4.0 * i), f"request {i} nhận kết quả của request khác"
    assert sum(sizes) == 50


def test_batches_never_exceed_max_and_do_form():
    Batcher = batcher_cls()

    async def scenario():
        async with Batcher(total, max_batch_size=8, max_wait_ms=50) as b:
            await asyncio.gather(*(b.submit(np.ones(3)) for _ in range(40)))
            return b.batch_sizes

    sizes = asyncio.run(scenario())
    assert max(sizes) <= 8
    assert sum(sizes) == 40
    assert len(sizes) <= 7, f"40 request đồng thời mà gom thành {len(sizes)} batch: {sizes}"


def test_waits_for_stragglers_within_max_wait():
    Batcher = batcher_cls()

    async def scenario():
        async with Batcher(total, max_batch_size=16, max_wait_ms=150) as b:
            async def late(i):
                await asyncio.sleep(0.005 * i)
                return await b.submit(np.ones(2))

            await asyncio.gather(*(late(i) for i in range(8)))
            return b.batch_sizes

    assert asyncio.run(scenario()) == [8]


def test_lone_request_is_not_held_much_longer_than_max_wait():
    Batcher = batcher_cls()

    async def scenario():
        async with Batcher(total, max_batch_size=8, max_wait_ms=40) as b:
            started = time.perf_counter()
            await b.submit(np.ones(2))
            return time.perf_counter() - started

    assert asyncio.run(scenario()) < 0.4


def timed(Batcher, max_batch_size):
    def slow(batch):
        time.sleep(0.02)
        return total(batch)

    async def scenario():
        async with Batcher(slow, max_batch_size=max_batch_size, max_wait_ms=10) as b:
            started = time.perf_counter()
            await asyncio.gather(*(b.submit(np.ones(4)) for _ in range(64)))
            return time.perf_counter() - started

    return asyncio.run(scenario())


def test_throughput_improves_with_batching():
    Batcher = batcher_cls()
    single = timed(Batcher, 1)
    batched = timed(Batcher, 16)
    assert batched < 0.5 * single, f"batch 16: {batched:.2f}s, batch 1: {single:.2f}s"


def test_infer_runs_off_the_event_loop():
    Batcher = batcher_cls()

    def blocking(batch):
        time.sleep(0.3)
        return total(batch)

    async def scenario():
        ticks = 0

        async def heartbeat():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        beat = asyncio.create_task(heartbeat())
        async with Batcher(blocking, max_batch_size=4, max_wait_ms=1) as b:
            await b.submit(np.ones(2))
        beat.cancel()
        return ticks

    assert asyncio.run(scenario()) >= 8, "event loop bị chặn trong lúc infer chạy"


def test_failure_is_isolated_to_its_batch():
    Batcher = batcher_cls()

    def fragile(batch):
        if (batch < 0).any():
            raise ValueError("ảnh hỏng")
        return total(batch)

    async def scenario():
        async with Batcher(fragile, max_batch_size=4, max_wait_ms=20) as b:
            first = await asyncio.gather(b.submit(np.ones(2)), b.submit(-np.ones(2)), return_exceptions=True)
            second = await asyncio.wait_for(b.submit(np.ones(2) * 3), 2)
            return first, second

    first, second = asyncio.run(scenario())
    assert all(isinstance(r, ValueError) for r in first)
    assert second == pytest.approx(6.0)


def test_with_real_onnxruntime_session(tmp_path):
    Batcher = batcher_cls()
    session = segkit.ort_session(segkit.export(segkit.tiny_model(seed=3), tmp_path / "seg.onnx"))
    images = np.random.default_rng(1).random((24, 3, 64, 64), dtype=np.float32)
    expected = [session.run(None, {"pixel_values": x[None]})[0][0] for x in images]

    async def scenario():
        async with Batcher(lambda b: session.run(None, {"pixel_values": b})[0], max_batch_size=8, max_wait_ms=20) as b:
            return await asyncio.gather(*(b.submit(x) for x in images)), b.batch_sizes

    outputs, sizes = asyncio.run(scenario())
    for got, want in zip(outputs, expected):
        np.testing.assert_allclose(got, want, atol=1e-5)
    assert max(sizes) <= 8 and len(sizes) < 24
