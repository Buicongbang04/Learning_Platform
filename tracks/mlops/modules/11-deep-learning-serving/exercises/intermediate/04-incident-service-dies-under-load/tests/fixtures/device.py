"""Card production (RTX 3050 Laptop 4 GB) mô phỏng trên CPU.

Suy luận chạy thật bằng ONNX Runtime CPU; bộ nhớ được tính như trên card: mỗi lần chạy chiếm một lượng bộ nhớ
tỉ lệ với input, cấp phát vượt phần còn trống thì ném lỗi giống PyTorch/ONNX Runtime CUDA. API đặt tên theo
`torch.cuda` để code chuyển sang card thật không phải đổi.
"""

import threading

import numpy as np

MIB = 2**20


class OutOfMemoryError(RuntimeError):
    pass


class SimulatedGPU:
    def __init__(self, total_mib: int = 4096, context_mib: int = 600, image_mib: int = 350):
        self.total = total_mib * MIB
        self.context = context_mib * MIB
        self._image = image_mib * MIB
        self._fail_next = 0
        self._lock = threading.Lock()
        self._allocated = 0
        self._peak = 0
        self.runs: list[int] = []
        self.errors = 0

    def mem_get_info(self) -> tuple[int, int]:
        with self._lock:
            return self.total - self.context - self._allocated, self.total

    def max_memory_allocated(self) -> int:
        return self._peak

    def reset_peak_memory_stats(self) -> None:
        self._peak = self._allocated

    def inject_failure(self, count: int = 1) -> None:
        self._fail_next = count

    def run(self, session, pixel_values: np.ndarray) -> np.ndarray:
        need = int(np.prod(pixel_values.shape[:1])) * self._image
        with self._lock:
            self.runs.append(len(pixel_values))
            if self._fail_next > 0:
                self._fail_next -= 1
                self.errors += 1
                raise RuntimeError("CUDA error: unspecified launch failure")
            free = self.total - self.context - self._allocated
            if need > free:
                self.errors += 1
                raise OutOfMemoryError(
                    f"CUDA out of memory. Tried to allocate {need / MIB:.0f} MiB (GPU 0; {self.total / MIB:.0f} MiB total "
                    f"capacity; {free / MIB:.0f} MiB free)"
                )
            self._allocated += need
            self._peak = max(self._peak, self._allocated)
        try:
            return session.run(None, {"pixel_values": pixel_values})[0]
        finally:
            with self._lock:
                self._allocated -= need
