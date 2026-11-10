import pandas as pd


def join_labels(predictions: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("M10: join log dự đoán với nhãn theo request_id, bỏ request chưa có nhãn")


def monthly_quality(joined: pd.DataFrame) -> dict[str, float]:
    raise NotImplementedError("M10: mae, p90_abs_err, mae_airport, n trên các dòng đã join")
