from dataclasses import dataclass

import pandas as pd

WINDOW_S = 900
LATENESS_S = 120


def trip_events(trips: pd.DataFrame) -> list[dict]:
    raise NotImplementedError("M16: một sự kiện 'chuyến đã kết thúc' mỗi chuyến, sắp theo lúc trả khách")


@dataclass(frozen=True)
class SimClock:
    sim_start: float
    wall_start: float
    speedup: float

    def sim(self, wall: float) -> float:
        raise NotImplementedError("M16: đổi wall time sang giờ mô phỏng")

    def wall(self, sim: float) -> float:
        raise NotImplementedError("M16: đổi giờ mô phỏng sang wall time")


def replay(bootstrap: str, topic: str, events: list[dict], clock: SimClock) -> int:
    raise NotImplementedError("M16: gửi sự kiện vào Kafka theo đồng hồ mô phỏng")
