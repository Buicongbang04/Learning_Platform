import numpy as np
import pandas as pd

from eta.config import Config
from eta.features import MIN_DURATION_S, build_features, make_features
from eta.labels import month_trips, published
from eta.quality import monthly_quality
from eta.train import time_split, train


def _require_labels(months: list[str], as_of: str) -> None:
    missing = [m for m in months if not published(m, as_of)]
    if missing:
        raise ValueError(f"nhãn của {missing} chưa công bố tại as_of {as_of}: không dùng được cho thí nghiệm")


def load_champion(config: Config):
    import mlflow
    from mlflow import MlflowClient

    version = MlflowClient(tracking_uri=config.mlflow_uri).get_model_version_by_alias(config.model_name, "champion").version
    mlflow.set_tracking_uri(config.mlflow_uri)
    return mlflow.sklearn.load_model(f"models:/{config.model_name}/{version}"), str(version)


def _speed_table(config: Config) -> pd.DataFrame | None:
    from eta.zone_features import read_speed_table

    return read_speed_table(config.speed_table) if config.speed_table else None


def score(model, trips: pd.DataFrame, config: Config) -> dict[str, float]:
    from eta.zone_features import prepare

    eta = np.maximum(model.predict(make_features(prepare(trips, model, _speed_table(config)))), float(MIN_DURATION_S))
    joined = pd.DataFrame({"eta_s": eta, "duration_s": trips["duration_s"].to_numpy(),
                           "PULocationID": trips["PULocationID"].to_numpy(), "DOLocationID": trips["DOLocationID"].to_numpy()})
    return monthly_quality(joined)


def _fit(trips: pd.DataFrame, config: Config):
    from eta.zone_features import attach_speed

    table = _speed_table(config)
    frame = attach_speed(trips, table) if table is not None else trips
    return train(*build_features(frame), {"random_state": config.seed, **config.model_params})


def late_slice(month: str, as_of: str, config: Config, test_frac: float = 0.2) -> dict:
    _require_labels([month], as_of)
    champion, version = load_champion(config)
    early, late = time_split(month_trips(month, config), test_frac)
    challenger = _fit(early, config)
    return {
        "experiment": "late_slice", "month": month, "as_of": as_of, "champion_version": version,
        "slice_start": str(late["tpep_pickup_datetime"].min()), "n": int(len(late)),
        "mae_champion": score(champion, late, config)["mae"], "mae_challenger": score(challenger, late, config)["mae"],
    }


def retrain_on(train_month: str, eval_months: list[str], as_of: str, config: Config) -> dict:
    _require_labels([train_month, *eval_months], as_of)
    champion, version = load_champion(config)
    retrained = _fit(month_trips(train_month, config), config)
    result = {"experiment": "retrain_on", "train_month": train_month, "as_of": as_of, "champion_version": version}
    for month in eval_months:
        trips = month_trips(month, config)
        result[month] = {"mae_champion": score(champion, trips, config)["mae"], "mae_retrained": score(retrained, trips, config)["mae"]}
    return result
