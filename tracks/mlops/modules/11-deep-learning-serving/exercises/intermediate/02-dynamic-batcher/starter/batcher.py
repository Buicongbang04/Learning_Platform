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
        # TODO: tạo hàng đợi và task nền gom batch
        raise NotImplementedError

    async def stop(self) -> None:
        # TODO: dừng task nền
        raise NotImplementedError

    async def submit(self, item: np.ndarray) -> np.ndarray:
        # TODO: đưa item vào hàng đợi, chờ đúng kết quả của item này
        raise NotImplementedError
