import mlflow
import pandas as pd
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

FEATURES = ["distance_km", "hour"]
TARGET = "duration_s"


def split(df: pd.DataFrame, seed: int):
    return train_test_split(df, test_size=0.2, random_state=seed)


def read_data(loader):
    """Gọi loader() để lấy DataFrame. Task có retry cho lỗi tạm thời."""
    # TODO
    raise NotImplementedError


def train_model(train_df: pd.DataFrame, seed: int):
    """RandomForestRegressor(n_estimators=20, max_depth=6, random_state=seed, n_jobs=1)."""
    # TODO
    raise NotImplementedError


def evaluate_model(model, test_df: pd.DataFrame) -> float:
    """R2 trên tập kiểm."""
    # TODO
    raise NotImplementedError


def register_model(model, r2: float, tracking_uri: str, model_name: str, min_r2: float, seed: int):
    """r2 >= min_r2: log run (param seed, metric r2, model), đăng ký version, trả số version. Ngược lại trả None."""
    # TODO
    raise NotImplementedError


def training_flow(loader, tracking_uri: str, model_name: str = "taxi-eta", min_r2: float = 0.5, seed: int = 0) -> dict:
    """read_data -> split -> train_model -> evaluate_model -> register_model; trả {"r2": float, "version": int | None}."""
    # TODO
    raise NotImplementedError
