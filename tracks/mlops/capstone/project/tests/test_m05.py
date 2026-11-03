"""M05: đồng hồ mô phỏng, nhãn về muộn, flow Prefect train/batch/replay. Đề ở capstone/milestones/m05-prefect-replay.md."""

import numpy as np
import pandas as pd
import pytest
from etakit import PREDICTION_LOG_COLUMNS, local_registry, need, write_config, write_months

MONTHS = ["2019-01", "2019-02", "2019-03", "2019-04"]


def test_m05_months_between(project):
    clock = need("clock", "months_between", "add_months")
    assert clock.months_between("2019-11", "2020-02") == ["2019-11", "2019-12", "2020-01", "2020-02"]
    assert clock.months_between("2019-03", "2019-03") == ["2019-03"]
    assert clock.add_months("2019-12", 1) == "2020-01"
    assert clock.add_months("2020-01", -1) == "2019-12"
    assert clock.add_months("2019-05", 0) == "2019-05"
    assert clock.add_months("2019-01", 14) == "2020-03"
    with pytest.raises(ValueError):
        clock.months_between("2020-02", "2019-11")


@pytest.fixture
def setup(tmp_path):
    raw = write_months(tmp_path / "raw", MONTHS)
    uri, name = local_registry(tmp_path, "eta-m05")
    cfg = write_config(tmp_path / "params.yaml", raw, ["2019-01"], uri, name)
    return raw, uri, name, cfg


def clean_count(raw, month: str) -> int:
    data = need("data", "load_month")
    features = need("features", "clean")
    return len(features.clean(data.load_month(raw / f"yellow_tripdata_{month}.parquet", 1_200, 0), month))


def test_m05_labels_not_before_publication(project, setup):
    raw, _, _, cfg = setup
    labels = need("labels", "LABEL_DELAY_MONTHS", "published", "labels_for")
    config = need("config", "load_config")
    assert labels.LABEL_DELAY_MONTHS == 1
    assert labels.published("2020-03", "2020-03") is False, "nhãn tháng M chưa công bố khi đồng hồ còn ở tháng M"
    assert labels.published("2020-03", "2020-04") is True
    assert labels.published("2019-12", "2020-01") is True
    assert labels.published("2020-03", "2020-02") is False
    assert labels.published("2020-03", "2020-04", delay=2) is False
    assert labels.published("2020-03", "2020-05", delay=2) is True
    conf = config.load_config(cfg)
    assert labels.labels_for("2019-02", "2019-02", conf) is None, "trước khi công bố, labels_for phải trả None dù tệp có sẵn"
    assert labels.labels_for("2019-02", "2019-01", conf) is None
    out = labels.labels_for("2019-02", "2019-03", conf)
    assert isinstance(out, pd.DataFrame), "đã công bố thì labels_for trả DataFrame"
    assert list(out.columns) == ["request_id", "duration_s"]
    assert len(out) == clean_count(raw, "2019-02") and out["request_id"].is_unique
    assert (out["duration_s"] >= 60).all()


def mlflow_runs(uri: str, name: str) -> int:
    from mlflow import MlflowClient

    client = MlflowClient(tracking_uri=uri)
    experiment = client.get_experiment_by_name(name)
    return 0 if experiment is None else len(client.search_runs([experiment.experiment_id]))


def test_m05_train_flow_cached(project, setup, prefect_harness):
    _, uri, name, cfg = setup
    flows = need("flows", "train_flow")
    first = flows.train_flow(str(cfg), ["2019-01"])
    assert isinstance(first, str) and first, "train_flow trả số version dạng chuỗi"
    assert mlflow_runs(uri, name) == 1
    second = flows.train_flow(str(cfg), ["2019-01"])
    assert second == first, "cùng data_version và params phải trả lại version cũ từ cache"
    assert mlflow_runs(uri, name) == 1, "chạy lại cùng tham số không được tạo run MLflow mới"
    other = flows.train_flow(str(cfg), ["2019-02"])
    assert other != first and mlflow_runs(uri, name) == 2, "đổi tháng (data_version đổi) phải train lại"


def set_champion(uri: str, name: str, version: str) -> None:
    from mlflow import MlflowClient

    MlflowClient(tracking_uri=uri).set_registered_model_alias(name, "champion", version)


def test_m05_batch_score_columns(project, setup, prefect_harness, tmp_path):
    raw, uri, name, cfg = setup
    logs = need("logs", "PREDICTION_LOG_COLUMNS")
    flows = need("flows", "train_flow", "batch_score_flow")
    assert logs.PREDICTION_LOG_COLUMNS == PREDICTION_LOG_COLUMNS
    version = flows.train_flow(str(cfg), ["2019-01"])
    set_champion(uri, name, version)
    out = tmp_path / "scores"
    path = flows.batch_score_flow("2019-02", str(cfg), str(out))
    assert str(path).endswith("predictions_2019-02.parquet") and (out / "predictions_2019-02.parquet").is_file()
    frame = pd.read_parquet(path)
    assert list(frame.columns) == PREDICTION_LOG_COLUMNS, f"cột phải đúng thứ tự PREDICTION_LOG_COLUMNS, có {list(frame.columns)}"
    assert len(frame) == clean_count(raw, "2019-02"), "chấm đúng mọi chuyến sạch của tháng"
    assert frame["request_id"].is_unique
    assert (frame["model_version"] == version).all() and (frame["variant"] == "batch").all()
    assert (frame["eta_s"] > 0).all()


def test_m05_replay_mae_late(project, setup, prefect_harness, tmp_path):
    _, _, _, cfg = setup
    flows = need("flows", "replay_flow")
    labels = need("labels", "labels_for")
    config = need("config", "load_config")
    out = tmp_path / "replay"
    rows = flows.replay_flow("2019-02", "2019-04", str(cfg), str(out))
    assert [r["month"] for r in rows] == ["2019-02", "2019-03", "2019-04"]
    for row in rows:
        assert {"month", "model_version", "n_scored", "mae", "as_of"} <= set(row), row
        assert row["as_of"] == "2019-04" and row["n_scored"] > 0 and row["model_version"]
        assert (out / f"predictions_{row['month']}.parquet").is_file()
    assert rows[-1]["mae"] is None, "tháng cuối chưa có nhãn tại as_of: mae phải là None, không được tính từ nhãn chưa công bố"
    conf = config.load_config(cfg)
    for row in rows[:-1]:
        assert isinstance(row["mae"], float) and row["mae"] > 0, row
        scored = pd.read_parquet(out / f"predictions_{row['month']}.parquet")
        truth = labels.labels_for(row["month"], "2019-04", conf)
        joined = scored.merge(truth, on="request_id", validate="one_to_one")
        assert len(joined) == row["n_scored"] == len(scored), "log dự đoán và nhãn phải join đủ theo request_id"
        expected = float(np.abs(joined["duration_s"] - joined["eta_s"]).mean())
        assert row["mae"] == pytest.approx(expected, rel=1e-6), "mae phải tính từ log dự đoán join nhãn đã công bố"
