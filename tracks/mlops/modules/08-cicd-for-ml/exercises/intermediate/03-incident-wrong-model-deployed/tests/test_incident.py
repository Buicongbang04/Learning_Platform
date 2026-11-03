import json
import re
from pathlib import Path

import pytest

import cikit
from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"

PUBLISH = '''

if not os.environ.get("ETALITE_SKIP_PUBLISH"):
    target = Path("store") / f"run-{os.environ.get('GITHUB_RUN_NUMBER', '0')}"
    target.mkdir(parents=True, exist_ok=True)
    (target / "model.json").write_text(Path("models/model.json").read_text())
'''


def prepare(tmp_path, workflow_text):
    repo = cikit.make_repo(tmp_path, {"train.py": cikit.PROJECT["train.py"] + PUBLISH}, data=True)
    for number in (8, 9, 10):
        target = repo / "store" / f"run-{number}"
        target.mkdir(parents=True)
        (target / "model.json").write_text(json.dumps({"model_id": f"m{number}-old", "slope": 1.0, "intercept": 0.0}))
    cikit.write_workflow(repo, "release.yml", workflow_text)
    cikit.commit_all(repo)
    return repo


def run_number(repo, number, *extra):
    result = cikit.run_ci(repo, "--env", f"GITHUB_RUN_NUMBER={number}", *extra)
    trained = re.search(r"trained model_id=(\S+)", cikit.log(result))
    deployed = repo / "deployed" / "model.json"
    return result, trained.group(1) if trained else None, json.loads(deployed.read_text())["model_id"] if deployed.is_file() else None


def test_incident_workflow_reproduces_the_symptom(tmp_path):
    repo = prepare(tmp_path, (FIXTURES / "release.incident.yml").read_text())
    result, trained, deployed = run_number(repo, 11)
    assert result.returncode == 0, "Triệu chứng là pipeline xanh"
    assert trained and deployed and deployed != trained, f"Triệu chứng: đã train {trained} nhưng deploy {deployed}"


def test_deployed_model_is_the_one_trained_in_that_run(tmp_path):
    repo = prepare(tmp_path, ex.read("release.yml"))
    for number in (11, 12, 100):
        result, trained, deployed = run_number(repo, number)
        assert result.returncode == 0, cikit.log(result)[-2000:]
        assert trained is not None and deployed == trained, f"Lần chạy {number}: train {trained} nhưng deploy {deployed}"


def test_deploy_fails_when_this_run_published_no_model(tmp_path):
    repo = prepare(tmp_path, ex.read("release.yml"))
    result, trained, deployed = run_number(repo, 13, "--env", "ETALITE_SKIP_PUBLISH=1")
    assert trained is not None
    assert result.returncode != 0, "Lần chạy không có model mà deploy vẫn xanh"
    assert deployed is None, f"Deploy đã đưa model {deployed} lên dù lần chạy này không tạo model nào"


def test_deploy_job_reads_only_the_artifact_store():
    workflow = cikit.load_workflow(ex.path("release.yml"))
    deploy = workflow["jobs"]["deploy"]
    assert deploy.get("needs") in ("train", ["train"])
    text = json.dumps(deploy["steps"]) + json.dumps(deploy.get("env", {}))
    assert "models/" not in text, "Job deploy chạy trên máy khác job train: nó chỉ được đọc store/, không đọc models/"
