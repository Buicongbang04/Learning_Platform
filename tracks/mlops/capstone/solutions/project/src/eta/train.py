import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from eta.features import AIRPORT_ZONES, feature_columns

ZONES = ["PULocationID", "DOLocationID"]
DEFAULT_PARAMS = {"max_iter": 200, "learning_rate": 0.1, "max_leaf_nodes": 63, "random_state": 0}


def build_pipeline(params: dict) -> Pipeline:
    encoder = ColumnTransformer(
        [("zones", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=np.nan, max_categories=250), ZONES)],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    model = HistGradientBoostingRegressor(categorical_features=[0, 1], **{**DEFAULT_PARAMS, **params})
    return Pipeline([("encode", encoder), ("model", model)])


def train(X: pd.DataFrame, y: pd.Series, params: dict) -> Pipeline:
    return build_pipeline(params).fit(X[feature_columns(X)], y)


def time_split(df: pd.DataFrame, test_frac: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = df.sort_values("tpep_pickup_datetime", kind="mergesort").reset_index(drop=True)
    cut = int(len(ordered) * (1 - test_frac))
    return ordered.iloc[:cut].reset_index(drop=True), ordered.iloc[cut:].reset_index(drop=True)


def evaluate(model: Pipeline, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
    err = np.abs(np.asarray(y, dtype=float) - model.predict(X[feature_columns(X)]))
    airport = (X["PULocationID"].isin(AIRPORT_ZONES) | X["DOLocationID"].isin(AIRPORT_ZONES)).to_numpy()
    return {
        "mae": float(err.mean()),
        "p90_abs_err": float(np.quantile(err, 0.9)),
        "mae_airport": float(err[airport].mean()) if airport.any() else float("nan"),
    }
