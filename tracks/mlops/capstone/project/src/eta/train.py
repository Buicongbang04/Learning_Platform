import pandas as pd
from sklearn.pipeline import Pipeline


def train(X: pd.DataFrame, y: pd.Series, params: dict) -> Pipeline:
    raise NotImplementedError("M01: Pipeline với HistGradientBoostingRegressor, zone là categorical")


def evaluate(model: Pipeline, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
    raise NotImplementedError("M01: trả đúng ba khoá mae, p90_abs_err, mae_airport")
