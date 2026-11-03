import shutil

import pytest
import yaml

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
FILES = ["Makefile", ".gitignore", ".pre-commit-config.yaml"]
MUST_IGNORE = [
    "data/raw/yellow_tripdata_2019-01.parquet",
    "data/interim/sample.csv",
    "models/model.joblib",
    "artifacts/model.pkl",
    "mlruns/0/meta.yaml",
    "mlflow.db",
    ".venv/bin/python",
    "src/eta_mini/__pycache__/data.cpython-312.pyc",
    "notebooks/.ipynb_checkpoints/a-checkpoint.ipynb",
    ".env",
    ".env.production",
    ".pytest_cache/README.md",
]
MUST_KEEP = ["src/eta_mini/data.py", "tests/test_data.py", "data/README.md", "data/.gitkeep", ".env.example", "uv.lock", "Makefile"]


@pytest.fixture
def repo(tmp_path):
    for name in FILES:
        shutil.copy(ex.path(name), tmp_path / name)
    for relative in [*MUST_IGNORE, *MUST_KEEP]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("x\n", encoding="utf-8")
    return tmp_path


def sandbox(repo, cmd, env=None, timeout=60):
    return run_sandboxed(cmd, writable=[repo], cwd=repo, env={"GIT_CONFIG_GLOBAL": "/dev/null", **(env or {})}, timeout=timeout)


def git(repo, *args):
    result = sandbox(repo, ["git", *args])
    assert result.returncode in (0, 1), result.stderr
    return result


@pytest.fixture
def git_repo(repo):
    assert git(repo, "init", "-q").returncode == 0
    return repo


@pytest.mark.parametrize("path", MUST_IGNORE)
def test_gitignore_blocks_data_models_secrets_and_caches(git_repo, path):
    assert git(git_repo, "check-ignore", "-q", path).returncode == 0, f"{path} phải bị .gitignore chặn"


@pytest.mark.parametrize("path", MUST_KEEP)
def test_gitignore_keeps_source_and_lockfile(git_repo, path):
    assert git(git_repo, "check-ignore", "-q", path).returncode == 1, f"{path} không được bị .gitignore chặn"


def test_git_add_all_stages_only_source(git_repo):
    git(git_repo, "add", "-A")
    staged = set(git(git_repo, "ls-files").stdout.split())
    assert staged == set(MUST_KEEP) | {".gitignore", ".pre-commit-config.yaml"}


def test_make_default_goal_lists_every_target(repo):
    result = sandbox(repo, ["make"])
    assert result.returncode == 0, result.stderr
    for target in ("setup", "test", "lint", "train", "clean"):
        assert any(line.split()[:1] == [target] for line in result.stdout.splitlines()), f"help thiếu {target}:\n{result.stdout}"
    assert "TODO" not in result.stdout


@pytest.mark.parametrize(
    "target, expected",
    [("setup", ["uv sync --frozen"]), ("test", ["pytest"]), ("lint", ["ruff check", "ruff format --check"])],
)
def test_make_targets_run_the_right_tools(repo, target, expected):
    result = sandbox(repo, ["make", "-n", target])
    assert result.returncode == 0, result.stderr
    for fragment in expected:
        assert fragment in result.stdout, f"`make {target}` phải chạy `{fragment}`:\n{result.stdout}"
    assert "TODO" not in result.stdout


def test_make_train_passes_variables_through(repo):
    result = sandbox(repo, ["make", "train", "PYTHON=echo", "DATA=data/raw/x.parquet", "SEED=7"])
    assert result.returncode == 0, result.stderr
    assert "-m eta_mini --data data/raw/x.parquet --out models/model.joblib --seed 7" in result.stdout
    assert (repo / "models").is_dir(), "target train phải tự tạo thư mục models"


def test_make_clean_removes_artifacts_but_keeps_data(repo):
    cache = repo / "src" / "eta_mini" / "__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "x.pyc").write_text("x", encoding="utf-8")
    (repo / "models").mkdir(exist_ok=True)
    (repo / "models" / "model.joblib").write_text("x", encoding="utf-8")
    result = sandbox(repo, ["make", "clean"])
    assert result.returncode == 0, result.stderr
    assert not (repo / "models").exists()
    assert not cache.exists()
    assert (repo / "data" / "raw" / "yellow_tripdata_2019-01.parquet").exists()
    assert (repo / "src" / "eta_mini" / "data.py").exists()


def test_pre_commit_config_pins_hooks_and_blocks_large_files():
    config = yaml.safe_load(ex.read(".pre-commit-config.yaml"))
    repos = config["repos"]
    assert repos, "Chưa khai báo repo nào"
    hooks = {}
    for item in repos:
        assert item["rev"] not in ("main", "master", "HEAD") and item["rev"].startswith("v"), f"Phải ghim rev: {item['repo']}"
        for hook in item["hooks"]:
            hooks[hook["id"]] = hook
    for needed in ("check-added-large-files", "check-yaml", "ruff", "ruff-format"):
        assert needed in hooks, f"Thiếu hook {needed}"
    limits = [a for a in hooks["check-added-large-files"].get("args", []) if a.startswith("--maxkb=")]
    assert limits and int(limits[0].split("=")[1]) <= 1024, "check-added-large-files cần --maxkb nhỏ hơn hoặc bằng 1024"
