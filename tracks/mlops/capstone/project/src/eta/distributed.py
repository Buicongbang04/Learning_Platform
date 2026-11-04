from dataclasses import dataclass

import pandas as pd

from eta.config import Config


@dataclass
class Retrained:
    model: object
    metrics: dict
    params: dict
    trials: int


def retrain(train: pd.DataFrame, valid: pd.DataFrame, storage_path: str, *, name: str = "eta-retrain",
            workers: int = 2, rounds: int = 200, every: int = 20, max_failures: int = 2) -> Retrained:
    raise NotImplementedError("M15: Ray Tune nhiều worker song song, checkpoint sau mỗi `every` cây, FailureConfig")


def register(result: Retrained, config: Config, data_version: str) -> str:
    raise NotImplementedError("M15: đăng ký qua log_and_register của M04, trả version")
