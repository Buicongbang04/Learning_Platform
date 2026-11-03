"""Kiểm tra "nợ kỹ thuật ML" trên ảnh chụp một repo.

`files` là dict đường dẫn tương đối (dấu `/`) -> nội dung văn bản. Tệp nhị phân (pkl, parquet...)
có nội dung rỗng.
"""
from __future__ import annotations

import re

MODEL_SUFFIXES = (".pkl", ".pickle", ".joblib", ".h5", ".pt", ".onnx")
DATA_SUFFIXES = (".csv", ".parquet", ".feather")
SEEDED_CALLS = (
    "train_test_split",
    "RandomForestClassifier",
    "RandomForestRegressor",
    "GradientBoostingClassifier",
    "GradientBoostingRegressor",
)
ABSOLUTE_PATH = re.compile(r"((?<![\w.:/])(/home/|/Users/)|[A-Za-z]:\\)")
BLOCKING = ("model-artifact-in-git", "data-in-git", "hardcoded-path")


def _name(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def model_artifact_in_git(files: dict[str, str]) -> list[str]:
    return sorted(p for p in files if p.lower().endswith(MODEL_SUFFIXES))


def data_in_git(files: dict[str, str]) -> list[str]:
    found = []
    for path in files:
        parts = path.split("/")[:-1]
        if path.lower().endswith(DATA_SUFFIXES) and "tests" not in parts and "fixtures" not in parts:
            found.append(path)
    return sorted(found)


def hardcoded_path(files: dict[str, str]) -> list[str]:
    found = []
    for path, text in files.items():
        if not path.endswith((".py", ".yaml", ".yml", ".toml")):
            continue
        if any(ABSOLUTE_PATH.search(line) for line in text.splitlines() if not line.lstrip().startswith("#")):
            found.append(path)
    return sorted(found)


def unseeded_randomness(files: dict[str, str]) -> list[str]:
    pattern = re.compile(r"\b(" + "|".join(SEEDED_CALLS) + r")\(([^)]*)\)")
    found = []
    for path, text in files.items():
        if path.endswith(".py") and any("random_state" not in args for _, args in pattern.findall(text)):
            found.append(path)
    return sorted(found)


def unpinned_dependency(files: dict[str, str]) -> list[str]:
    found = []
    for path, text in files.items():
        name = _name(path)
        if not (name.startswith("requirements") and name.endswith(".txt")):
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-")) and "==" not in line:
                found.append(path)
                break
    return sorted(found)


def no_tests(files: dict[str, str]) -> list[str]:
    has = any(p.startswith("tests/") or (_name(p).startswith("test_") and p.endswith(".py")) for p in files)
    return [] if has else ["."]


def notebook_only_code(files: dict[str, str]) -> list[str]:
    notebooks = sorted(p for p in files if p.endswith(".ipynb"))
    code = [p for p in files if p.endswith(".py") and not p.startswith("tests/")]
    return notebooks if notebooks and not code else []


CHECKS = {
    "model-artifact-in-git": model_artifact_in_git,
    "data-in-git": data_in_git,
    "hardcoded-path": hardcoded_path,
    "unseeded-randomness": unseeded_randomness,
    "unpinned-dependency": unpinned_dependency,
    "no-tests": no_tests,
    "notebook-only-code": notebook_only_code,
}


def audit(files: dict[str, str]) -> dict[str, list[str]]:
    results = {name: sorted(set(check(files))) for name, check in CHECKS.items()}
    return {name: paths for name, paths in results.items() if paths}


def verdict(findings: dict[str, list[str]]) -> str:
    if any(name in findings for name in BLOCKING):
        return "block"
    return "warn" if findings else "ok"
