import os
import random

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

FEATURES = ["trip_distance", "hour"]
TARGET = "duration_min"


def load_trips(data_dir):
    frames = []
    for name in os.listdir(data_dir):
        if name.endswith(".csv"):
            frames.append(pd.read_csv(os.path.join(data_dir, name)))
    return pd.concat(frames, ignore_index=True)


def split(df, test_fraction=0.2):
    indices = list(range(len(df)))
    random.shuffle(indices)
    cut = int(len(df) * (1 - test_fraction))
    return df.iloc[indices[:cut]], df.iloc[indices[cut:]]


def train(data_dir, seed=0):
    np.random.seed(seed)
    df = load_trips(data_dir)
    train_df, test_df = split(df)
    model = RandomForestRegressor(n_estimators=30, n_jobs=1)
    model.fit(train_df[FEATURES], train_df[TARGET])
    return float(mean_absolute_error(test_df[TARGET], model.predict(test_df[FEATURES])))
