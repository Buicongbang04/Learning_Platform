import hashlib
from pathlib import Path

import pandas as pd
from prefect import flow, task
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

CALLS: list[dict] = []


def data_cache_key(context, parameters: dict) -> str:
    content = hashlib.sha256(Path(parameters["data_path"]).read_bytes()).hexdigest()
    return f"fit:{content}:{parameters['n_estimators']}:{parameters['seed']}"


@task(cache_key_fn=data_cache_key)
def fit(data_path: str, n_estimators: int, seed: int) -> dict:
    CALLS.append({"data_path": data_path, "n_estimators": n_estimators, "seed": seed})
    df = pd.read_csv(data_path)
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=seed)
    cols = ["distance_km", "hour"]
    model = RandomForestRegressor(n_estimators=n_estimators, max_depth=6, random_state=seed, n_jobs=1)
    model.fit(train_df[cols], train_df["duration_s"])
    r2 = float(r2_score(test_df["duration_s"], model.predict(test_df[cols])))
    return {"r2": r2, "rows": len(df), "n_estimators": n_estimators, "seed": seed}


@flow
def train_flow(data_path: str, n_estimators: int = 20, seed: int = 0) -> dict:
    return fit(data_path, n_estimators, seed)
