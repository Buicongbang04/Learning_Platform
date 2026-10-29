import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
import numpy as np
import pandas as pd
import pytest
from mlflow import MlflowClient
from sklearn.metrics import roc_auc_score

from testkit import ROOT, Exercise

ex = Exercise(__file__)

NUMERIC = ["promised_days", "delivery_days", "delay_days", "approve_hours", "n_items", "n_sellers",
           "price", "freight", "freight_ratio", "payment_installments"]
CATEGORICAL = ["customer_state", "payment_type"]
FEATURES = NUMERIC + CATEGORICAL


def make_table(n: int, seed: int) -> pd.DataFrame:
    """Bảng giả cùng cột với load_olist_table; mọi cột số là float64 như hợp đồng của model."""
    rng = np.random.default_rng(seed)
    promised = rng.uniform(10, 40, n)
    delivery = np.clip(promised + rng.normal(-10, 8, n), 1, None)
    price = rng.lognormal(4.5, 0.8, n)
    freight = rng.lognormal(2.8, 0.5, n)
    delay = delivery - promised
    logit = -2.2 + 0.25 * delay + rng.normal(0, 1, n)
    return pd.DataFrame({
        "order_purchase_timestamp": pd.Timestamp("2017-06-01") + pd.to_timedelta(np.sort(rng.uniform(0, 300, n)), unit="D"),
        "promised_days": promised, "delivery_days": delivery, "delay_days": delay,
        "approve_hours": rng.exponential(10, n), "n_items": rng.integers(1, 4, n).astype(float),
        "n_sellers": np.ones(n), "price": price, "freight": freight,
        "freight_ratio": freight / (price + freight), "payment_installments": rng.integers(1, 10, n).astype(float),
        "customer_state": rng.choice(["SP", "RJ", "MG", "BA"], n),
        "payment_type": rng.choice(["credit_card", "boleto", "voucher"], n),
        "bad_review": (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int),
    })


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("registry.ipynb")


@pytest.fixture(scope="module")
def data():
    df = make_table(1500, seed=0)
    return df.iloc[:1000], df.iloc[1000:]


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    root = tmp_path_factory.mktemp("mlflow")
    uri = f"sqlite:///{root / 'mlflow.db'}"
    exp_id = MlflowClient(uri).create_experiment("t", artifact_location=(root / "artifacts").as_uri())
    return uri, exp_id


_RUNS: dict = {}


def get_runs(nb, data, store):
    # Gọi hàm của bạn bên trong test (không trong fixture) để starter FAIL chứ không ERROR
    if not _RUNS:
        train, val = data
        uri, exp_id = store
        for C in (1e-4, 1.0):
            _RUNS[C] = nb.train_and_log(train, val, C, uri, exp_id)
    return _RUNS


def ensure_champion(nb, store):
    """Đăng ký model nếu alias champion chưa có, để mỗi test chạy được riêng lẻ (-k), không phụ thuộc thứ tự."""
    uri, exp_id = store
    try:
        MlflowClient(uri).get_model_version_by_alias("bad-review", "champion")
    except mlflow.exceptions.MlflowException:
        nb.register_best(uri, exp_id, "bad-review")


def test_run_logs_params_and_metric(nb, store, data):
    runs = get_runs(nb, data, store)
    uri, exp_id = store
    run = MlflowClient(uri).get_run(runs[1.0])
    assert run.info.experiment_id == exp_id and run.info.status == "FINISHED"
    assert run.data.params["C"] == "1.0"
    assert run.data.params["n_train"] == "1000"
    assert 0.6 < run.data.metrics["val_auc"] < 1.0


def test_logged_model_reproduces_metric(nb, store, data):
    runs = get_runs(nb, data, store)
    uri, _ = store
    _, val = data
    mlflow.set_tracking_uri(uri)
    model = mlflow.sklearn.load_model(f"runs:/{runs[1.0]}/model")
    auc = roc_auc_score(val.bad_review, model.predict_proba(val[FEATURES])[:, 1])
    assert MlflowClient(uri).get_run(runs[1.0]).data.metrics["val_auc"] == pytest.approx(auc, abs=1e-9)


def test_signature_and_pyfunc_returns_probabilities(nb, store, data):
    runs = get_runs(nb, data, store)
    uri, _ = store
    _, val = data
    mlflow.set_tracking_uri(uri)
    info = mlflow.models.get_model_info(f"runs:/{runs[1.0]}/model")
    assert info.signature is not None
    assert info.signature.inputs.input_names() == FEATURES
    pred = np.asarray(mlflow.pyfunc.load_model(f"runs:/{runs[1.0]}/model").predict(val[FEATURES]))
    assert pred.shape == (len(val), 2)
    assert np.allclose(pred.sum(axis=1), 1.0)


def test_register_best_sets_champion(nb, store, data):
    runs = get_runs(nb, data, store)
    uri, exp_id = store
    client = MlflowClient(uri)
    aucs = {C: client.get_run(r).data.metrics["val_auc"] for C, r in runs.items()}
    best_C = max(aucs, key=aucs.get)
    version = nb.register_best(uri, exp_id, "bad-review")
    assert isinstance(version, int) and version == 1
    mv = client.get_model_version_by_alias("bad-review", "champion")
    assert int(mv.version) == 1 and mv.run_id == runs[best_C]


def test_new_better_run_moves_alias_and_keeps_old_version(nb, store, data):
    runs = get_runs(nb, data, store)
    uri, exp_id = store
    train, val = data
    client = MlflowClient(uri)
    ensure_champion(nb, store)
    old = client.get_model_version_by_alias("bad-review", "champion")
    # nhân bản một run với val_auc cao hơn mọi run hiện có
    better = client.create_run(exp_id)
    best_auc = max(client.get_run(r).data.metrics["val_auc"] for r in runs.values())
    src = runs[1.0]
    mlflow.set_tracking_uri(uri)
    with mlflow.start_run(run_id=better.info.run_id):
        mlflow.log_metric("val_auc", best_auc + 0.01)
        mlflow.sklearn.log_model(mlflow.sklearn.load_model(f"runs:/{src}/model"), name="model",
                                 pip_requirements=["scikit-learn"], skops_trusted_types=["numpy.dtype"],
                                 pyfunc_predict_fn="predict_proba")
    version = nb.register_best(uri, exp_id, "bad-review")
    assert version == int(old.version) + 1
    assert client.get_model_version_by_alias("bad-review", "champion").run_id == better.info.run_id
    assert client.get_model_version("bad-review", old.version) is not None


def test_load_champion_predicts_and_enforces_schema(nb, store, data):
    runs = get_runs(nb, data, store)
    uri, _ = store
    _, val = data
    ensure_champion(nb, store)
    champion = nb.load_champion(uri, "bad-review")
    pred = np.asarray(champion.predict(val[FEATURES].head(20)))
    assert pred.shape == (20, 2)
    with pytest.raises(Exception):
        champion.predict(val[FEATURES].drop(columns=["delay_days"]).head(5))


def test_real_olist(nb, tmp_path):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    table = nb.load_olist_table(raw)
    splits = nb.time_split(table)
    assert {k: len(v) for k, v in splits.items()} == {"train": 43362, "val": 20468, "test": 31994}
    uri = f"sqlite:///{tmp_path / 'real.db'}"
    exp_id = MlflowClient(uri).create_experiment("real", artifact_location=(tmp_path / "art").as_uri())
    run_id = nb.train_and_log(splits["train"], splits["val"], 1.0, uri, exp_id)
    assert MlflowClient(uri).get_run(run_id).data.metrics["val_auc"] == pytest.approx(0.7987, abs=0.003)
