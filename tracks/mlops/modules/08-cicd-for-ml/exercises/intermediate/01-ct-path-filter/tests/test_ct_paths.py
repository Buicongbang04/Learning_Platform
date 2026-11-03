import json

import pytest

import cikit
from testkit import Exercise

ex = Exercise(__file__)

CASES = [
    (["src/etalite/model.py"], True, False),
    (["tests/test_model.py"], True, False),
    (["pyproject.toml"], True, False),
    (["params.yaml"], False, True),
    (["data.dvc"], False, True),
    (["train.py"], True, True),
    (["gate.py"], True, True),
    (["src/etalite/model.py", "params.yaml"], True, True),
    (["README.md"], False, False),
    (["docs/params.yaml"], False, False),
    (["data.dvc.bak"], False, False),
    (["notebooks/eda.ipynb"], False, False),
]


@pytest.fixture(scope="module")
def ci():
    return cikit.load_workflow(ex.path("ci.yml"))


@pytest.fixture(scope="module")
def ct():
    return cikit.load_workflow(ex.path("ct.yml"))


@pytest.mark.parametrize("event", ["push", "pull_request"])
@pytest.mark.parametrize("changed,ci_runs,ct_runs", CASES, ids=lambda v: "-".join(v) if isinstance(v, list) else str(v))
def test_which_workflow_runs_for_a_change(ci, ct, event, changed, ci_runs, ct_runs):
    assert cikit.triggers(ci, event, changed) is ci_runs, f"ci với {event}, thay đổi {changed}"
    assert cikit.triggers(ct, event, changed) is ct_runs, f"ct với {event}, thay đổi {changed}"


def test_ct_push_is_limited_to_main_and_can_be_run_by_hand(ct):
    assert not cikit.triggers(ct, "push", ["params.yaml"], branch="feature/x")
    assert cikit.triggers(ct, "workflow_dispatch", [])


@pytest.fixture
def repo(tmp_path):
    repo = cikit.make_repo(tmp_path, {"gate.py": "print('gate stub')\n"}, data=True)
    cikit.write_workflow(repo, "ci.yml", ex.read("ci.yml"))
    cikit.write_workflow(repo, "ct.yml", ex.read("ct.yml"))
    cikit.commit_all(repo)
    return repo


def test_act_lists_jobs_of_both_workflows(repo):
    result = cikit.run_ci(repo, "-l")
    assert result.returncode == 0, cikit.log(result)[-1500:]
    rows = [line.split() for line in result.stdout.splitlines()[1:] if line.strip()]
    listed = {(row[1], row[3]) for row in rows}
    assert {("lint", "ci"), ("test", "ci"), ("train", "ct"), ("gate", "ct")} <= listed, result.stdout


def test_dryrun_of_ct_succeeds(repo):
    result = cikit.run_ci(repo, "-W", ".github/workflows/ct.yml", "--dryrun")
    assert result.returncode == 0, cikit.log(result)[-1500:]
    assert "train" in cikit.log(result) and "gate" in cikit.log(result)


def test_train_job_runs_for_real_on_a_sample_of_march_2019(repo):
    result = cikit.run_ci(repo, "-W", ".github/workflows/ct.yml", "-j", "train")
    assert result.returncode == 0, cikit.log(result)[-2500:]
    metrics = json.loads((repo / "models" / "metrics.json").read_text())
    assert metrics["rows"] > 2000 and 0 < metrics["mae"] < 3000
    assert "trained model_id=" in cikit.log(result)
