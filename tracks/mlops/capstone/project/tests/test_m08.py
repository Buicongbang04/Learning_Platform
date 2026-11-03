"""M08: GitHub Actions chạy bằng act: CI code, CT model có cổng promotion, CD khi alias champion khớp. Đề ở capstone/milestones/m08-cicd-act.md."""

import json

import pandas as pd
import pytest
from etakit import COLUMNS, local_registry, need, synthetic_month

import etaci
import mlopskit

CT = ".github/workflows/ct.yml"
CI = ".github/workflows/ci.yml"
CD = ".github/workflows/cd.yml"
PATH_CASES = [
    (["src/eta/serve.py"], True, False),
    (["src/eta/features.py"], True, False),
    (["tests_own/test_core.py"], True, False),
    (["params.yaml"], False, True),
    (["dvc.lock"], False, True),
    (["src/eta/train.py"], True, True),
    (["README.md"], False, False),
    (["docs/params.yaml"], False, False),
]


def needs(job: dict) -> set[str]:
    value = job.get("needs") or []
    return {value} if isinstance(value, str) else set(value)


def test_m08_workflow_structure(project):
    etaci.check_run_only(project)
    ci = etaci.load_workflow(etaci.workflow_path(project, "ci.yml"))
    ct = etaci.load_workflow(etaci.workflow_path(project, "ct.yml"))
    cd = etaci.load_workflow(etaci.workflow_path(project, "cd.yml"))
    assert (ci.get("name"), ct.get("name"), cd.get("name")) == ("ci", "ct", "cd"), "name của ba workflow phải là ci, ct, cd"
    assert {"lint", "test", "build"} <= set(ci["jobs"]), f"ci cần job lint, test, build; có {sorted(ci['jobs'])}"
    assert {"lint", "test"} <= needs(ci["jobs"]["build"]), "build phải needs lint và test"
    assert {"validate", "train", "gate"} <= set(ct["jobs"]), f"ct cần job validate, train, gate; có {sorted(ct['jobs'])}"
    assert "validate" in needs(ct["jobs"]["train"]) and "train" in needs(ct["jobs"]["gate"])
    after_gate = [name for name, job in ct["jobs"].items() if "gate" in needs(job)]
    assert after_gate, "ct cần ít nhất một job needs gate (chỉ chạy khi cổng qua)"
    dispatch = etaci.cikit.events(cd).get("workflow_dispatch")
    assert dispatch is not None and "model_version" in (dispatch.get("inputs") or {}), "cd chạy bằng workflow_dispatch với input model_version"
    assert {"verify", "deploy"} <= set(cd["jobs"]) and "verify" in needs(cd["jobs"]["deploy"]), "deploy phải needs verify"
    assert "docker compose" in json.dumps(cd["jobs"]["deploy"]), "deploy dùng docker compose"


def test_m08_ci_fails_on_broken_test(project, tmp_path):
    repo = etaci.make_repo(project, tmp_path)
    assert list((repo / "tests_own").glob("test_*.py")), "cần test của bạn trong tests_own/test_*.py"
    broken = repo / "tests_own" / "test_zz_m08_broken.py"
    broken.write_text("def test_m08_broken():\n    assert 1 == 2\n", encoding="utf-8")
    etaci.commit_all(repo, "test hỏng")
    red = etaci.run(repo, "-W", CI, "-j", "test")
    assert red.returncode != 0, "test hỏng mà job test vẫn xanh"
    assert "test_m08_broken" in etaci.log(red), etaci.log(red)[-2000:]
    broken.unlink()
    etaci.commit_all(repo, "bỏ test hỏng")
    green = etaci.run(repo, "-W", CI)
    assert green.returncode == 0, etaci.log(green)[-3000:]
    assert "[ci/build" in etaci.log(green), "job build phải chạy sau lint và test xanh"


def test_m08_ct_path_filter(project, tmp_path):
    ci = etaci.load_workflow(etaci.workflow_path(project, "ci.yml"))
    ct = etaci.load_workflow(etaci.workflow_path(project, "ct.yml"))
    for changed, ci_runs, ct_runs in PATH_CASES:
        assert etaci.triggers(ci, "push", changed) is ci_runs, f"ci với push đổi {changed}"
        assert etaci.triggers(ct, "push", changed) is ct_runs, f"ct với push đổi {changed}"
    assert not etaci.triggers(ct, "push", ["params.yaml"], branch="feature/x"), "ct chỉ chạy khi push lên main"
    assert etaci.triggers(ct, "workflow_dispatch", []), "ct chạy tay được bằng workflow_dispatch"
    repo = etaci.make_repo(project, tmp_path)
    listed = etaci.run(repo, "-l")
    assert listed.returncode == 0, etaci.log(listed)[-1500:]
    rows = {(row[1], row[3]) for row in (line.split() for line in listed.stdout.splitlines()[1:]) if len(row) > 3}
    assert {("validate", "ct"), ("train", "ct"), ("gate", "ct"), ("test", "ci")} <= rows, listed.stdout
    dry = etaci.run(repo, "-W", CT, "--dryrun")
    assert dry.returncode == 0, etaci.log(dry)[-1500:]


@pytest.fixture
def ct_repo(project, tmp_path):
    """Gọi trong test (không chạy lúc setup) để thiếu tệp thì test fail kèm thông báo thay vì ERROR."""
    return lambda: build_ct_repo(project, tmp_path)


def build_ct_repo(project, tmp_path):
    repo = etaci.make_repo(project, tmp_path)
    raw = repo / "data" / "raw"
    raw.mkdir(parents=True)
    trips = pd.read_parquet(mlopskit.real_month("nyc-tlc", "2019-01"), columns=COLUMNS).sample(n=30_000, random_state=0)
    trips.sort_values("tpep_pickup_datetime").to_parquet(raw / "yellow_tripdata_2019-01.parquet", index=False)
    uri, name = local_registry(repo / "mlflow", "eta-m08")
    env = {"ETA_DATA_DIR": str(raw), "ETA_MLFLOW_URI": uri, "ETA_MODEL_NAME": name, "ETA_MONTHS": "2019-01",
           "ETA_SAMPLE_ROWS": "20000", "ETA_SEED": "0", "ETA_MODEL_PARAMS": '{"max_iter": 30}', "ETA_SPEED_TABLE": ""}
    return repo, uri, name, env


def register(uri: str, name: str, metrics: dict, alias: str | None = "champion") -> str:
    from mlflow import MlflowClient

    config = need("config", "Config")
    registry = need("registry", "log_and_register")
    features = need("features", "build_features", "clean")
    train = need("train", "train")
    frame = features.clean(synthetic_month(1_500, seed=7), "2019-01")
    model = train.train(*features.build_features(frame), {"max_iter": 5, "random_state": 0})
    cfg = config.Config(data_dir=".", months=["2019-01"], mlflow_uri=uri, model_name=name, model_params={"max_iter": 5})
    version = str(registry.log_and_register(model, metrics, cfg, "sha256:m08-fixture"))
    if alias:
        MlflowClient(tracking_uri=uri).set_registered_model_alias(name, alias, version)
    return version


def champion(uri: str, name: str) -> str | None:
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    try:
        return str(MlflowClient(tracking_uri=uri).get_model_version_by_alias(name, "champion").version)
    except MlflowException:
        return None


def test_m08_gate_blocks_deploy(project, ct_repo):
    repo, uri, name, env = ct_repo()
    best = register(uri, name, {"mae": 1.0, "p90_abs_err": 1.0, "mae_airport": 1.0})
    result = etaci.run(repo, "-W", CT, env=env)
    text = etaci.log(result)
    assert result.returncode != 0, "challenger tệ hơn champion mà ct vẫn xanh"
    assert any(line.startswith("[ct/train") and "Job succeeded" in line for line in text.splitlines()), text[-3000:]
    gate = "\n".join(line for line in text.splitlines() if line.startswith("[ct/gate"))
    assert "exitcode '3'" in gate, f"job gate phải thoát với EXIT_REJECTED=3 khi bị từ chối:\n{gate[-2000:]}"
    after = [job for job, spec in etaci.load_workflow(repo / CT)["jobs"].items() if "gate" in needs(spec)]
    for job in after:
        assert f"[ct/{job}" not in text, f"job {job} đã chạy dù cổng từ chối"
    assert champion(uri, name) == best, "alias champion phải giữ nguyên khi cổng từ chối"


def test_m08_ct_promotes_first_model(project, ct_repo):
    repo, uri, name, env = ct_repo()
    result = etaci.run(repo, "-W", CT, env=env)
    assert result.returncode == 0, etaci.log(result)[-3000:]
    version = champion(uri, name)
    assert version is not None, "chưa có champion thì challenger đầu tiên phải được promote"
    from mlflow import MlflowClient

    tags = MlflowClient(tracking_uri=uri).get_model_version(name, version).tags
    assert tags.get("data_version", "").startswith("sha256:"), "model train trong CT phải có tag data_version"


def test_m08_cd_requires_champion(project, ct_repo):
    repo, uri, name, env = ct_repo()
    current = register(uri, name, {"mae": 200.0, "p90_abs_err": 400.0, "mae_airport": 500.0})
    other = register(uri, name, {"mae": 190.0, "p90_abs_err": 380.0, "mae_airport": 480.0}, alias=None)
    wrong = etaci.run(repo, "-W", CD, "--input", f"model_version={other}", event="workflow_dispatch", env=env)
    text = etaci.log(wrong)
    assert wrong.returncode != 0, "deploy version không mang alias champion mà cd vẫn xanh"
    assert "[cd/verify" in text and "[cd/deploy" not in text, text[-3000:]
    right = etaci.run(repo, "-W", CD, "-j", "verify", "--input", f"model_version={current}", event="workflow_dispatch", env=env)
    assert right.returncode == 0, etaci.log(right)[-3000:]
