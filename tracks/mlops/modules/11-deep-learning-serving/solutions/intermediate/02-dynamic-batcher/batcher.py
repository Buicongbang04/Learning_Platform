import asyncio
from typing import Callable

import numpy as np


class DynamicBatcher:
    def __init__(self, infer: Callable[[np.ndarray], np.ndarray], max_batch_size: int = 8, max_wait_ms: float = 10.0):
        self.infer = infer
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.batch_sizes: list[int] = []

    async def __aenter__(self) -> "DynamicBatcher":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()

    async def start(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        while not self._queue.empty():
            _, future = self._queue.get_nowait()
            if not future.done():
                future.cancel()

    async def submit(self, item: np.ndarray) -> np.ndarray:
        future = asyncio.get_running_loop().create_future()
        await self._queue.put((item, future))
        return await future

    async def _collect(self) -> list:
        pending = [await self._queue.get()]
        deadline = asyncio.get_running_loop().time() + self.max_wait_ms / 1000
        while len(pending) < self.max_batch_size:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            try:
                pending.append(await asyncio.wait_for(self._queue.get(), remaining))
            except asyncio.TimeoutError:
                break
        return pending

    async def _loop(self) -> None:
        while True:
            pending = await self._collect()
            pending = [(item, future) for item, future in pending if not future.cancelled()]
            if not pending:
                continue
            self.batch_sizes.append(len(pending))
            try:
                outputs = await asyncio.to_thread(self.infer, np.stack([item for item, _ in pending]))
                if len(outputs) != len(pending):
                    raise RuntimeError(f"infer trả {len(outputs)} kết quả cho batch {len(pending)}")
            except Exception as error:
                for _, future in pending:
                    if not future.done():
                        future.set_exception(error)
                continue
            for (_, future), output in zip(pending, outputs):
                if not future.done():
                    future.set_result(output)
