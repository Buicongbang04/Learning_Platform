from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

FEATURES = ["trip_distance", "hour"]
TARGET = "duration_min"


def load_trips(data_dir):
    paths = sorted(Path(data_dir).glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"Không có tệp .csv nào trong {data_dir}")
    return pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)


def split(df, seed, test_fraction=0.2):
    order = np.random.default_rng(seed).permutation(len(df))
    cut = int(len(df) * (1 - test_fraction))
    return df.iloc[order[:cut]], df.iloc[order[cut:]]


def train(data_dir, seed=0):
    df = load_trips(data_dir)
    train_df, test_df = split(df, seed)
    model = RandomForestRegressor(n_estimators=30, n_jobs=1, random_state=seed)
    model.fit(train_df[FEATURES], train_df[TARGET])
    return float(mean_absolute_error(test_df[TARGET], model.predict(test_df[FEATURES])))
