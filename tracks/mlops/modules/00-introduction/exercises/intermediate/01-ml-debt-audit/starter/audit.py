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


def model_artifact_in_git(files: dict[str, str]) -> list[str]:
    """Đường dẫn tệp model bị commit (đuôi trong MODEL_SUFFIXES, không phân biệt hoa thường)."""
    # TODO
    raise NotImplementedError


def data_in_git(files: dict[str, str]) -> list[str]:
    """Tệp dữ liệu (DATA_SUFFIXES) bị commit, trừ tệp nằm dưới thư mục `tests/` hoặc `fixtures/`."""
    # TODO
    raise NotImplementedError


def hardcoded_path(files: dict[str, str]) -> list[str]:
    """Tệp .py/.yaml/.yml/.toml có dòng (không phải dòng bắt đầu bằng `#`) khớp ABSOLUTE_PATH."""
    # TODO
    raise NotImplementedError


def unseeded_randomness(files: dict[str, str]) -> list[str]:
    """Tệp .py gọi một hàm trong SEEDED_CALLS mà phần đối số không có `random_state`.

    Đối số lấy bằng `\\bTên\\(([^)]*)\\)`; test không dùng lời gọi lồng nhau trong đối số.
    """
    # TODO
    raise NotImplementedError


def unpinned_dependency(files: dict[str, str]) -> list[str]:
    """Tệp `requirements*.txt` có dòng khai báo gói không ghim bằng `==`.

    Bỏ dòng trống, dòng bắt đầu bằng `#` và dòng bắt đầu bằng `-` (option như `-r`, `-e`).
    """
    # TODO
    raise NotImplementedError


def no_tests(files: dict[str, str]) -> list[str]:
    """`["."]` nếu repo không có tệp dưới `tests/` và không có tệp tên `test_*.py`; ngược lại `[]`."""
    # TODO
    raise NotImplementedError


def notebook_only_code(files: dict[str, str]) -> list[str]:
    """Danh sách .ipynb nếu repo có notebook nhưng không có tệp .py nào ngoài `tests/`; ngược lại `[]`."""
    # TODO
    raise NotImplementedError


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
    """Chạy mọi CHECKS; chỉ trả các khoá có kết quả, mỗi giá trị là danh sách đã sắp xếp, không trùng."""
    # TODO
    raise NotImplementedError


def verdict(findings: dict[str, list[str]]) -> str:
    """`"block"` nếu có `model-artifact-in-git`, `data-in-git` hoặc `hardcoded-path`;
    `"warn"` nếu chỉ có phát hiện khác; `"ok"` nếu không có gì."""
    # TODO
    raise NotImplementedError
