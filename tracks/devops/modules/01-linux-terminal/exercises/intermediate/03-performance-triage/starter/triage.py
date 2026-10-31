from collections import Counter

SWAP_IO_LIMIT = 100
IOWAIT_LIMIT = 20
BLOCKED_LIMIT = 1


def parse_vmstat(text: str) -> list[dict[str, int]]:
    # TODO 1: đọc output `vmstat <delay> <count>`, bỏ dòng tiêu đề (kể cả khi lặp lại) và mẫu đầu tiên
    raise NotImplementedError


def use_summary(samples: list[dict[str, int]], ncpu: int) -> dict[str, float]:
    # TODO 2: trung bình cpu_util (us+sy), run_queue_per_cpu (r/ncpu), iowait (wa), blocked (b), swap_io (si+so)
    raise NotImplementedError


def diagnose(samples: list[dict[str, int]], ncpu: int) -> str:
    # TODO 3: "memory", "cpu", "disk" hoặc "ok", theo thứ tự ưu tiên trong đề
    raise NotImplementedError


def parse_iostat(text: str) -> dict[str, dict[str, float]]:
    # TODO 4: số liệu từng device của báo cáo CUỐI trong `iostat -x`, đọc cột theo tên tiêu đề
    raise NotImplementedError


def saturated_devices(text: str, util: float = 90.0, queue: float = 1.0) -> list[str]:
    # TODO 5: device có %util >= util VÀ aqu-sz >= queue, sắp theo tên
    raise NotImplementedError


def socket_states(text: str, port: int | None = None) -> Counter:
    # TODO 6: đếm trạng thái socket trong `ss -tan`, lọc theo cổng LOCAL nếu có port
    raise NotImplementedError


def listen_overflow(text: str) -> list[str]:
    # TODO 7: địa chỉ LISTEN có accept queue đầy (Recv-Q >= Send-Q) trong `ss -ltn`, sắp theo chuỗi
    raise NotImplementedError
