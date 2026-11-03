import mlflow
import pandas as pd
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from prefect import flow, task
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

FEATURES = ["distance_km", "hour"]
TARGET = "duration_s"
SKOPS_TRUSTED_TYPES = ["sklearn.tree._tree.Tree"]
TRANSIENT = (ConnectionError, TimeoutError)


def split(df: pd.DataFrame, seed: int):
    return train_test_split(df, test_size=0.2, random_state=seed)


def is_transient(task, task_run, state) -> bool:
    return isinstance(state.result(raise_on_failure=False), TRANSIENT)


@task(retries=2, retry_delay_seconds=0.2, retry_condition_fn=is_transient)
def read_data(loader):
    return loader()


@task
def train_model(train_df: pd.DataFrame, seed: int):
    model = RandomForestRegressor(n_estimators=20, max_depth=6, random_state=seed, n_jobs=1)
    return model.fit(train_df[FEATURES], train_df[TARGET])


@task
def evaluate_model(model, test_df: pd.DataFrame) -> float:
    return float(r2_score(test_df[TARGET], model.predict(test_df[FEATURES])))


@task
def register_model(model, r2: float, tracking_uri: str, model_name: str, min_r2: float, seed: int):
    if r2 < min_r2:
        return None
    mlflow.set_tracking_uri(tracking_uri)
    with mlflow.start_run() as run:
        mlflow.log_param("seed", seed)
        mlflow.log_metric("r2", r2)
        info = mlflow.sklearn.log_model(
            model, name="model", skops_trusted_types=SKOPS_TRUSTED_TYPES,
            input_example=pd.DataFrame({"distance_km": [1.0], "hour": [8.0]}),
        )
    client = MlflowClient(tracking_uri)
    try:
        client.create_registered_model(model_name)
    except MlflowException as error:
        if "already exists" not in str(error) and "RESOURCE_ALREADY_EXISTS" not in str(error):
            raise
    version = client.create_model_version(model_name, info.model_uri, run.info.run_id, model_id=info.model_id)
    return int(version.version)


@flow(validate_parameters=False)
def training_flow(loader, tracking_uri: str, model_name: str = "taxi-eta", min_r2: float = 0.5, seed: int = 0) -> dict:
    df = read_data(loader)
    train_df, test_df = split(df, seed)
    model = train_model(train_df, seed)
    r2 = evaluate_model(model, test_df)
    version = register_model(model, r2, tracking_uri, model_name, min_r2, seed)
    return {"r2": r2, "version": version}
