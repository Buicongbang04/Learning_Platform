import pytest
import yaml

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)


def sh(repo, cmd):
    env = {
        "DVC_NO_ANALYTICS": "1",
        "DVC_SITE_CACHE_DIR": str(repo / ".site"),
        "DVC_GLOBAL_CONFIG_DIR": str(repo / ".gc"),
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    result = run_sandboxed(["bash", "-c", cmd], writable=[repo], cwd=repo, env=env, timeout=120)
    assert result.returncode == 0, f"{cmd}\n{result.stdout}\n{result.stderr}"
    return result.stdout + result.stderr


def ran(text):
    return "Running stage 'prepare'" in text


def skipped(text):
    return "Stage 'prepare' didn't change, skipping" in text


@pytest.fixture()
def repo(tmp_path):
    ex.require_tool("dvc")
    ex.require_tool("git")
    r = tmp_path / "repo"
    (r / "data" / "raw").mkdir(parents=True)
    for name in ("dvc.yaml", "params.yaml", "prepare.py"):
        (r / name).write_text(ex.read(name))
    (r / "data" / "raw" / "trips.csv").write_text(
        "trip_id,trip_distance\n" + "".join(f"{i},{(i % 10) * 0.05}\n" for i in range(1, 61))
    )
    sh(r, "git init -q -b main . && dvc init -q && printf '/.site\\n/.gc\\n' >> .git/info/exclude")
    return r


def clean_rows(repo):
    return len((repo / "data" / "clean.csv").read_text().splitlines()) - 1


def test_first_run_then_skip_when_unchanged(repo):
    assert ran(sh(repo, "dvc repro"))
    assert skipped(sh(repo, "dvc repro"))


def test_script_change_reruns_and_changes_output(repo):
    sh(repo, "dvc repro")
    before = clean_rows(repo)
    script = (repo / "prepare.py").read_text()
    (repo / "prepare.py").write_text(script.replace('float(r["trip_distance"]) > params["min_distance"]', 'float(r["trip_distance"]) > max(params["min_distance"], 0.1)'))
    text = sh(repo, "dvc repro")
    assert ran(text)
    assert clean_rows(repo) < before


def test_stage_param_change_reruns(repo):
    sh(repo, "dvc repro")
    before = clean_rows(repo)
    params = yaml.safe_load((repo / "params.yaml").read_text())
    params["prepare"]["min_distance"] = 0.2
    (repo / "params.yaml").write_text(yaml.safe_dump(params))
    assert ran(sh(repo, "dvc repro"))
    assert clean_rows(repo) < before


def test_unrelated_param_does_not_rerun(repo):
    sh(repo, "dvc repro")
    params = yaml.safe_load((repo / "params.yaml").read_text())
    params["train"]["seed"] = 42
    (repo / "params.yaml").write_text(yaml.safe_dump(params))
    assert skipped(sh(repo, "dvc repro"))
