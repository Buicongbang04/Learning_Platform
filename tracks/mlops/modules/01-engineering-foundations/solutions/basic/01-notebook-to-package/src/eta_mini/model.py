from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from eta_mini.features import build_features


@dataclass
class TrainResult:
    model: Any
    mae: float
    n_train: int
    n_test: int


def train(df: pd.DataFrame, seed: int = 0, max_iter: int = 100) -> TrainResult:
    X = build_features(df)
    y = df["duration_min"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed)
    model = HistGradientBoostingRegressor(max_iter=max_iter, random_state=seed).fit(X_train, y_train)
    mae = float(mean_absolute_error(y_test, model.predict(X_test)))
    return TrainResult(model=model, mae=mae, n_train=len(X_train), n_test=len(X_test))


def predict(model: Any, df: pd.DataFrame) -> Any:
    return model.predict(build_features(df))
