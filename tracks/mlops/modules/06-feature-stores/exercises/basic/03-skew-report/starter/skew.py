"""So sánh feature của cùng thực thể giữa offline và online."""
import pandas as pd


def skew_report(offline: pd.DataFrame, online: pd.DataFrame, key: str, rtol: float = 1e-6, atol: float = 1e-9) -> list[dict]:
    raise NotImplementedError("TODO: trả danh sách các cột lệch, xem đề bài")
