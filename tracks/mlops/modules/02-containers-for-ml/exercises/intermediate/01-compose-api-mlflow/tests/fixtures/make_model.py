import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression

FEATURES = ["distance_km", "hour", "passengers"]


def build(path: Path) -> Path:
    rng = np.random.default_rng(0)
    distance = rng.uniform(0.5, 25, 2000)
    hour = rng.integers(0, 24, 2000)
    passengers = rng.integers(1, 5, 2000)
    rush = ((hour >= 7) & (hour <= 9)) | ((hour >= 16) & (hour <= 19))
    eta = 4 + 2.6 * distance + 3 * rush + rng.normal(0, 1, 2000)
    model = LinearRegression().fit(np.c_[distance, hour, passengers], eta)
    joblib.dump({"model": model, "features": FEATURES}, path)
    return path


if __name__ == "__main__":
    build(Path(sys.argv[1]))
