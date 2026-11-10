import pandas as pd

TTL_S = 1800


def attach_live_speed(trips: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("M16: point-in-time theo lúc cửa sổ sẵn sàng, TTL, mặc định DEFAULT_SPEED_MPH")


class OnlineSpeed:
    def __init__(self, path):
        raise NotImplementedError("M16: đọc snapshot online cho API")
