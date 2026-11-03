import numpy as np
import pandas as pd

FEATURES = ["distance_km", "hour"]
TARGET = "duration_s"
DEFAULT_PARAMS = {"n_estimators": 20, "max_depth": 6}


def make_dataset(n: int = 600, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    distance = rng.gamma(2.0, 2.5, n)
    hour = rng.integers(0, 24, n)
    rush = np.where(np.isin(hour, [7, 8, 9, 17, 18, 19]), 1.35, 1.0)
    duration = (120 + 170 * distance * rush + rng.normal(0, 40, n)).clip(30)
    return pd.DataFrame({"distance_km": distance, "hour": hour, "duration_s": duration})


def data_fingerprint(df: pd.DataFrame) -> str:
    """sha256 (64 ký tự hex) của nội dung bảng, kể cả thứ tự dòng."""
    # TODO
    raise NotImplementedError


def train(df: pd.DataFrame, seed: int, params: dict | None = None):
    """RandomForestRegressor trên FEATURES -> TARGET; params ghi đè DEFAULT_PARAMS."""
    # TODO
    raise NotImplementedError


def save_artifact(model, path) -> str:
    """Ghi model ra `path` bằng joblib, trả sha256 của đúng các byte trong tệp."""
    # TODO
    raise NotImplementedError


def build_manifest(df: pd.DataFrame, seed: int, params: dict | None, artifact_path) -> dict:
    """Khoá: data_sha256, seed, params (đã gộp mặc định), artifact_sha256, python, sklearn, numpy."""
    # TODO
    raise NotImplementedError


def verify(manifest: dict, artifact_path) -> bool:
    """True nếu tệp artifact tồn tại và hash khớp manifest["artifact_sha256"]."""
    # TODO
    raise NotImplementedError
