import pandas as pd

from eta.streaming.events import LATENESS_S, WINDOW_S

FEATURE = "speed_15m_mph"


class ZoneSpeedWindows:
    def __init__(self, window_s: int = WINDOW_S, lateness_s: int = LATENESS_S):
        self.late = 0
        self.duplicates = 0
        self.invalid = 0

    def add(self, event) -> list[dict]:
        raise NotImplementedError("M16: gộp một sự kiện, trả các cửa sổ vừa đóng")

    def flush(self) -> list[dict]:
        raise NotImplementedError("M16: đóng mọi cửa sổ còn mở")


def consume(bootstrap: str, topic: str, *, on_close=None, idle_ms: int = 3000) -> dict:
    raise NotImplementedError("M16: đọc topic từ đầu, tính cửa sổ, gọi on_close mỗi lô vừa đóng")


def zone_speed_batch(trips: pd.DataFrame, window_s: int = WINDOW_S) -> pd.DataFrame:
    raise NotImplementedError("M16: cùng feature tính bằng pandas trên chuyến")
