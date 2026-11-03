import math

import numpy as np
import pandas
import sklearn

from eta.config import Config
from eta.lineage import git_commit

ALIAS = "champion"
SKOPS_TRUSTED_TYPES = [
    "functools.partial",
    "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor",
    "sklearn.utils.validation.check_array",
]


def log_and_register(model, metrics: dict, config: Config, data_version: str) -> str:
    import mlflow
    from mlflow import MlflowClient

    mlflow.set_tracking_uri(config.mlflow_uri)
    mlflow.set_experiment(config.model_name)
    tags = {"git_commit": git_commit(), "data_version": data_version}
    params = {"months": ",".join(config.months), "sample_rows": config.sample_rows, "seed": config.seed}
    params.update({f"model.{k}": v for k, v in config.model_params.items()})
    with mlflow.start_run(tags=tags):
        mlflow.log_params(params)
        mlflow.log_metrics({k: float(v) for k, v in metrics.items() if not math.isnan(float(v))})
        info = mlflow.sklearn.log_model(
            model,
            name="model",
            registered_model_name=config.model_name,
            skops_trusted_types=SKOPS_TRUSTED_TYPES,
            pip_requirements=[f"scikit-learn=={sklearn.__version__}", f"pandas=={pandas.__version__}", f"numpy=={np.__version__}"],
        )
    version = str(info.registered_model_version)
    client = MlflowClient(tracking_uri=config.mlflow_uri)
    for key, value in tags.items():
        client.set_model_version_tag(config.model_name, version, key, value)
    return version
