"""M03: pipeline DVC prepare → validate → train và validation chặn tháng hỏng. Đề ở capstone/milestones/m03-data-pipeline.md."""

import re
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml
from etakit import PROJECT, require_file, synthetic_month

from testkit import run_sandboxed

STAGES = {"prepare", "validate", "train"}
RUNNING = re.compile(r"Running stage '([^'@]+)(?:@[^']*)?'")
VENV_BIN = Path(sys.executable).parent


def dvc_bin() -> Path:
    path = VENV_BIN / "dvc"
    if not path.is_file():
        pytest.skip("Chưa có dvc trong môi trường. Chạy: uv sync")
    return path


def bad_month(n: int = 2_000, share: float = 0.05) -> pd.DataFrame:
    frame = synthetic_month(n, seed=5)
    rows = frame.sample(frac=share, random_state=0).index
    frame.loc[rows, "tpep_dropoff_datetime"] = frame.loc[rows, "tpep_pickup_datetime"] - pd.Timedelta(minutes=5)
    return frame


class Repo:
    def __init__(self, tmp_path: Path, raw_month: pd.DataFrame):
        require_file("dvc.yaml")
        require_file("params.yaml")
        self.dvc = dvc_bin()
        self.tmp = tmp_path
        self.dir = tmp_path / "repo"
        raw = tmp_path / "raw"
        raw.mkdir()
        raw_month.to_parquet(raw / "yellow_tripdata_2019-01.parquet", index=False)
        self.dir.mkdir()
        shutil.copytree(PROJECT / "src", self.dir / "src", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(PROJECT / "dvc.yaml", self.dir / "dvc.yaml")
        params = yaml.safe_load((PROJECT / "params.yaml").read_text(encoding="utf-8"))
        params.update({"data_dir": str(raw), "months": ["2019-01"], "sample_rows": 1_500, "seed": 0})
        params["model_params"] = {**(params.get("model_params") or {}), "max_iter": 20}
        self.write_params(params)
        for cmd in (["git", "init", "-q"], [self.dvc, "init", "-q"]):
            result = self.run(cmd)
            assert result.returncode == 0, result.stdout + result.stderr

    def write_params(self, params: dict) -> None:
        (self.dir / "params.yaml").write_text(yaml.safe_dump(params, sort_keys=False), encoding="utf-8")

    def params(self) -> dict:
        return yaml.safe_load((self.dir / "params.yaml").read_text(encoding="utf-8"))

    def run(self, cmd: list, timeout: float = 240):
        env = {"PATH": f"{VENV_BIN}:/usr/local/bin:/usr/bin:/bin", "DVC_NO_ANALYTICS": "1",
               "DVC_SITE_CACHE_DIR": str(self.tmp / "dvc-site"), "GIT_CONFIG_NOSYSTEM": "1"}
        return run_sandboxed(cmd, writable=[self.tmp], cwd=self.dir, env=env, timeout=timeout)

    def repro(self):
        result = self.run([self.dvc, "repro"])
        output = result.stdout + result.stderr
        return result.returncode, set(RUNNING.findall(output)), output


def test_m03_dvc_repro_idempotent(project, tmp_path):
    repo = Repo(tmp_path, synthetic_month(3_000, seed=6))
    code, ran, output = repo.repro()
    assert code == 0, output[-3000:]
    assert STAGES <= ran, f"dvc.yaml cần các stage {sorted(STAGES)}, lần đầu chạy {sorted(ran)}"
    code, ran, output = repo.repro()
    assert code == 0 and not ran, f"chạy lại không đổi gì mà vẫn chạy {sorted(ran)}:\n{output[-2000:]}"
    params = repo.params()
    params["model_params"]["max_iter"] = 25
    repo.write_params(params)
    code, ran, output = repo.repro()
    assert code == 0, output[-3000:]
    assert ran == {"train"}, f"đổi model_params chỉ được chạy lại train, đang chạy {sorted(ran)}"


def test_m03_validate_blocks_bad_month(project, tmp_path):
    require_file("src", "eta", "cli.py")
    good = tmp_path / "good.parquet"
    bad = tmp_path / "bad.parquet"
    synthetic_month(2_000, seed=7, extra_columns=False).to_parquet(good, index=False)
    bad_month().drop(columns=["VendorID", "passenger_count", "fare_amount"]).to_parquet(bad, index=False)
    env = {"PYTHONPATH": str(PROJECT / "src")}
    for path, expected in ((good, 0), (bad, 1)):
        result = run_sandboxed([sys.executable, "-m", "eta.cli", "validate", path, "--month", "2019-01"],
                               writable=[tmp_path], cwd=tmp_path, env=env, timeout=120)
        assert result.returncode == expected, f"validate {path.name}: exit {result.returncode}, cần {expected}\n{result.stderr[-1500:]}"
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    repo = Repo(pipeline, bad_month())
    code, ran, output = repo.repro()
    assert code != 0, "dvc repro phải dừng khi tháng dữ liệu vi phạm schema"
    assert "train" not in ran, "stage train không được chạy khi validate thất bại"
