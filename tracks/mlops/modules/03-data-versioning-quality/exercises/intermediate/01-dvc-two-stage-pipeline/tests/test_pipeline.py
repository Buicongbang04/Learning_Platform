import pytest
import yaml

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)


def sh(repo, cmd, ok=True):
    return mlopskit.dvc_sh(repo, cmd, ok=ok)


def out(result):
    return result.stdout + result.stderr


@pytest.fixture()
def repo(tmp_path):
    ex.require_tool("dvc")
    ex.require_tool("git")
    r = tmp_path / "repo"
    (r / "data" / "raw").mkdir(parents=True)
    for name in ("dvc.yaml", "params.yaml", "prepare.py", "split.py"):
        (r / name).write_text(ex.read(name))
    (r / "data" / "raw" / "trips.csv").write_text(
        "trip_id,trip_distance\n" + "".join(f"{i},{(i % 7) * 0.5}\n" for i in range(1, 41))
    )
    sh(r, "git init -q -b main . && dvc init -q && printf '/.site\\n/.gc\\n' >> .git/info/exclude")
    return r


def ran(text, stage):
    return f"Running stage '{stage}'" in text


def skipped(text, stage):
    return f"Stage '{stage}' didn't change, skipping" in text


def test_graph_is_declared_by_files(repo):
    spec = yaml.safe_load((repo / "dvc.yaml").read_text())
    assert set(spec["stages"]) == {"prepare", "split"}
    assert "data/clean.csv" in spec["stages"]["prepare"]["outs"]
    assert "data/clean.csv" in spec["stages"]["split"]["deps"]
    assert "prepare.py" in spec["stages"]["prepare"]["deps"] and "split.py" in spec["stages"]["split"]["deps"]


def test_first_repro_runs_both_and_writes_lock(repo):
    text = out(sh(repo, "dvc repro"))
    assert ran(text, "prepare") and ran(text, "split")
    assert (repo / "dvc.lock").is_file()
    assert (repo / "data" / "train.csv").is_file() and (repo / "data" / "test.csv").is_file()


def test_unchanged_is_skipped(repo):
    sh(repo, "dvc repro")
    text = out(sh(repo, "dvc repro"))
    assert skipped(text, "prepare") and skipped(text, "split")


def test_changed_raw_data_reruns_everything(repo):
    sh(repo, "dvc repro")
    with open(repo / "data" / "raw" / "trips.csv", "a") as f:
        f.write("99,3.5\n")
    text = out(sh(repo, "dvc repro"))
    assert ran(text, "prepare") and ran(text, "split")


def test_split_param_reruns_only_split(repo):
    sh(repo, "dvc repro")
    params = yaml.safe_load((repo / "params.yaml").read_text())
    params["split"]["test_size"] = 0.5
    (repo / "params.yaml").write_text(yaml.safe_dump(params))
    text = out(sh(repo, "dvc repro"))
    assert skipped(text, "prepare")
    assert ran(text, "split")


def test_prepare_param_propagates(repo):
    sh(repo, "dvc repro")
    params = yaml.safe_load((repo / "params.yaml").read_text())
    params["prepare"]["min_distance"] = 1.0
    (repo / "params.yaml").write_text(yaml.safe_dump(params))
    text = out(sh(repo, "dvc repro"))
    assert ran(text, "prepare") and ran(text, "split")
