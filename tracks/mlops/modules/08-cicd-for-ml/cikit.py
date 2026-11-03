"""Hỗ trợ test module 08: dựng repo nhỏ, chạy workflow bằng act ngoại tuyến, đánh giá path filter."""
import functools
import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

import mlopskit
import testkit

RUFF_VERSION = "0.17.1"
PYTEST_VERSION = importlib.metadata.version("pytest")
TOOLS_DIR = ".ci-tools"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

PROJECT = {
    "pyproject.toml": '[project]\nname = "etalite"\nversion = "1.0"\n\n[tool.ruff]\nline-length = 100\n',
    ".gitignore": f"{TOOLS_DIR}/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\ndist/\n",
    "src/etalite/__init__.py": "",
    "src/etalite/model.py": '''def fit_linear(xs, ys):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var if var else 0.0
    return slope, mean_y - slope * mean_x


def predict(model, x):
    slope, intercept = model
    return slope * x + intercept


def mae(model, xs, ys):
    return sum(abs(predict(model, x) - y) for x, y in zip(xs, ys)) / len(xs)
''',
    "src/etalite/cli.py": '''from etalite.model import fit_linear, predict


def main():
    model = fit_linear([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])
    print(f"etalite 1.0 {predict(model, 4.0):.0f}")
''',
    "tests/test_model.py": '''from etalite.model import fit_linear, mae, predict


def test_fit_recovers_a_line():
    slope, intercept = fit_linear([1.0, 2.0, 3.0], [12.0, 22.0, 32.0])
    assert round(slope, 6) == 10.0 and round(intercept, 6) == 2.0


def test_predict_and_mae():
    model = (2.0, 1.0)
    assert predict(model, 3.0) == 7.0
    assert mae(model, [1.0, 2.0], [3.0, 6.0]) == 0.5
''',
    "conftest.py": 'import sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path(__file__).parent / "src"))\n',
    "params.yaml": "max_distance: 30\nmin_duration: 60\nmax_duration: 7200\n",
    "data.dvc": "outs:\n- md5: 0f1e2d3c4b5a69788796a5b4c3d2e1f0\n  path: data/trips.csv\n",
    "train.py": '''import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "src")
from etalite.model import fit_linear, mae


def load_params(path):
    params = {}
    for line in Path(path).read_text().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            params[key.strip()] = float(value)
    return params


def main():
    params = load_params("params.yaml")
    rows = [line.split(",") for line in Path("data/trips.csv").read_text().splitlines()[1:]]
    pairs = [(float(d), float(t)) for d, t in rows
             if 0 < float(d) <= params["max_distance"] and params["min_duration"] <= float(t) <= params["max_duration"]]
    train = [p for i, p in enumerate(pairs) if i % 5]
    holdout = [p for i, p in enumerate(pairs) if i % 5 == 0]
    model = fit_linear([p[0] for p in train], [p[1] for p in train])
    score = mae(model, [p[0] for p in holdout], [p[1] for p in holdout])
    run = os.environ.get("GITHUB_RUN_NUMBER", "0")
    digest = hashlib.sha256(json.dumps([model, len(pairs)]).encode()).hexdigest()[:8]
    model_id = f"m{run}-{digest}"
    Path("models").mkdir(exist_ok=True)
    Path("models/model.json").write_text(json.dumps({"model_id": model_id, "slope": model[0], "intercept": model[1]}))
    Path("models/metrics.json").write_text(json.dumps({"model_id": model_id, "mae": score, "rows": len(pairs)}))
    print(f"trained model_id={model_id} mae={score:.2f}")


main()
''',
}


@functools.lru_cache(maxsize=1)
def trips_csv() -> str:
    import pandas as pd

    path = mlopskit.real_month("nyc-tlc", "2019-03")
    frame = pd.read_parquet(path, columns=["tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance"])
    frame = frame.sample(n=4000, random_state=0)
    seconds = (frame["tpep_dropoff_datetime"] - frame["tpep_pickup_datetime"]).dt.total_seconds()
    out = pd.DataFrame({"trip_distance": frame["trip_distance"].round(2), "duration_s": seconds.round(0)})
    return out.to_csv(index=False)


def tools_path() -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "mlops-ex" / f"ci-tools-ruff{RUFF_VERSION}-pytest{PYTEST_VERSION}"
    if (cache / "bin" / "ruff").is_file():
        return cache
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("Cần uv để chuẩn bị ruff và pytest cho runner (xem module 08, mục 0)")
    cache.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="ci-tools-", dir=cache.parent))
    result = subprocess.run(
        [uv, "pip", "install", "--quiet", "--target", str(staging), "--python", sys.executable,
         f"ruff=={RUFF_VERSION}", f"pytest=={PYTEST_VERSION}"],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        shutil.rmtree(staging, ignore_errors=True)
        pytest.skip(f"Không tải được ruff/pytest cho runner (cần mạng một lần): {result.stderr[-300:]}")
    try:
        staging.rename(cache)
    except OSError:
        shutil.rmtree(staging, ignore_errors=True)
    return cache


def git(repo: Path, *args: str):
    result = testkit.run_sandboxed(["git", *args], writable=[repo], cwd=repo, env=GIT_ENV, timeout=60)
    assert result.returncode == 0, f"git {' '.join(args)}\n{result.stdout}\n{result.stderr}"
    return result


def commit_all(repo: Path, message: str = "update") -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", message)


def make_repo(root: Path, files: dict[str, str] | None = None, *, tools: bool = False, data: bool = False) -> Path:
    repo = root / "repo"
    for name, text in {**PROJECT, **(files or {})}.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    if data:
        (repo / "data").mkdir(exist_ok=True)
        (repo / "data" / "trips.csv").write_text(trips_csv(), encoding="utf-8")
    if tools:
        shutil.copytree(tools_path(), repo / TOOLS_DIR, symlinks=True)
    git(repo, "init", "-q", "-b", "main")
    commit_all(repo, "init")
    return repo


def write_workflow(repo: Path, name: str, text: str) -> Path:
    target = repo / ".github" / "workflows" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def run_ci(repo: Path, *args: str, event: str = "push", timeout: int = 600) -> subprocess.CompletedProcess:
    own = f"--label {mlopskit.LABEL} --user {os.getuid()}:{os.getgid()}"
    return mlopskit.act_run(repo, *args, "--container-options", own, event=event, timeout=timeout)


def log(result: subprocess.CompletedProcess) -> str:
    return result.stdout + result.stderr


def load_workflow(path: Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path.name}: không phải workflow hợp lệ"
    if True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def events(workflow: dict) -> dict:
    spec = workflow.get("on")
    if isinstance(spec, str):
        return {spec: {}}
    if isinstance(spec, list):
        return {name: {} for name in spec}
    return {name: (cfg or {}) for name, cfg in (spec or {}).items()}


def glob_to_regex(pattern: str) -> re.Pattern:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def _hit(patterns, path: str) -> bool:
    return any(glob_to_regex(p).match(path) for p in patterns)


def triggers(workflow: dict, event: str, changed: list[str], branch: str = "main") -> bool:
    cfg = events(workflow).get(event)
    if cfg is None:
        return False
    if cfg.get("branches") and not _hit(cfg["branches"], branch):
        return False
    paths, ignore = cfg.get("paths"), cfg.get("paths-ignore")
    if paths:
        return any(_hit(paths, f) for f in changed)
    if ignore:
        return any(not _hit(ignore, f) for f in changed)
    return True
