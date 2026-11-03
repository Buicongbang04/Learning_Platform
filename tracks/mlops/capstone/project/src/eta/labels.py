import pandas as pd

from eta.config import Config

LABEL_DELAY_MONTHS = 1


def published(month: str, as_of: str, delay: int = LABEL_DELAY_MONTHS) -> bool:
    raise NotImplementedError("M05: nhãn tháng month đã công bố tại as_of chưa (as_of >= month + delay)")


def labels_for(month: str, as_of: str, config: Config) -> pd.DataFrame | None:
    raise NotImplementedError("M05: None khi chưa công bố; ngược lại DataFrame cột request_id, duration_s")
