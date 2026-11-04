import numpy as np
from sklearn.linear_model import LinearRegression, Ridge

FEATURES = ["distance_km", "hour", "passengers"]
RELEASES = {"v1": (0, 0.0, 20_000), "v2": (1, 5.0, 20_000), "v3": (2, 1.0, 6_000_000)}
TRAIN_ROWS = 20_000


def make_trips(seed: int, n: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    distance = np.round(rng.uniform(0.5, 25, n), 2)
    hour = rng.integers(0, 24, n).astype(float)
    passengers = rng.integers(1, 5, n).astype(float)
    rush = ((hour >= 7) & (hour <= 9)) | ((hour >= 16) & (hour <= 19))
    eta = 4 + 2.6 * distance + 3 * rush + 0.2 * passengers + rng.normal(0, 1, n)
    return np.c_[distance, hour, passengers], np.round(eta, 4)


def train(x: np.ndarray, y: np.ndarray, alpha: float = 0.0):
    model = Ridge(alpha=alpha) if alpha > 0 else LinearRegression()
    return model.fit(x, y)


def mae(model, x: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(np.abs(model.predict(x) - y)))


def release_model(version: str):
    seed, alpha, _ = RELEASES[version]
    x, y = make_trips(seed, TRAIN_ROWS)
    return train(x, y, alpha)
