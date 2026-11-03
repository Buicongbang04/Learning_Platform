"""Cửa sổ theo event time: tumbling, sliding, session và bộ gộp có watermark, sự kiện trễ, trùng lặp."""


def tumbling_start(ts: int, size: int) -> int:
    raise NotImplementedError("TODO 1: mốc bắt đầu cửa sổ tumbling chứa ts")


def sliding_windows(ts: int, size: int, step: int) -> list[tuple[int, int]]:
    raise NotImplementedError("TODO 2: mọi cửa sổ [start, end) độ dài size, start chia hết cho step, chứa ts")


def session_windows(timestamps: list[int], gap: int) -> list[tuple[int, int]]:
    raise NotImplementedError("TODO 3: gộp sự kiện thành session theo gap")


class WindowAggregator:
    def __init__(self, size: int, lateness: int):
        self.size = size
        self.lateness = lateness
        self.watermark: int | None = None
        self.late = 0
        self.duplicates = 0

    def add(self, event: dict) -> list[dict]:
        raise NotImplementedError("TODO 4: nhận một sự kiện, trả các cửa sổ vừa đóng")

    def flush(self) -> list[dict]:
        raise NotImplementedError("TODO 5: đóng mọi cửa sổ còn mở")
