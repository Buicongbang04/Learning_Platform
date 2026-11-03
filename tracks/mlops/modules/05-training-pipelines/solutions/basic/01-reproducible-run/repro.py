import hashlib
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor

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
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def _file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def train(df: pd.DataFrame, seed: int, params: dict | None = None):
    merged = {**DEFAULT_PARAMS, **(params or {})}
    model = RandomForestRegressor(random_state=seed, n_jobs=1, **merged)
    return model.fit(df[FEATURES], df[TARGET])


def save_artifact(model, path) -> str:
    joblib.dump(model, path)
    return _file_sha256(path)


def build_manifest(df: pd.DataFrame, seed: int, params: dict | None, artifact_path) -> dict:
    return {
        "data_sha256": data_fingerprint(df),
        "seed": seed,
        "params": {**DEFAULT_PARAMS, **(params or {})},
        "artifact_sha256": _file_sha256(artifact_path),
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "numpy": np.__version__,
    }


def verify(manifest: dict, artifact_path) -> bool:
    path = Path(artifact_path)
    return path.is_file() and _file_sha256(path) == manifest["artifact_sha256"]
