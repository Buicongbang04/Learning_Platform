from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class TrainResult:
    model: Any
    mae: float
    n_train: int
    n_test: int


def train(df: pd.DataFrame, seed: int = 0, max_iter: int = 100) -> TrainResult:
    # TODO: chia 80/20 theo seed, fit HistGradientBoostingRegressor(random_state=seed), tính MAE trên phần test
    raise NotImplementedError


def predict(model: Any, df: pd.DataFrame) -> Any:
    # TODO: dự đoán thời lượng (phút) từ chuyến thô, dùng build_features
    raise NotImplementedError
