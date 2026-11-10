"""Lưu model không kèm code (safetensors) và cổng nhận model: allowlist định dạng theo nội dung + modelscan."""

from pathlib import Path
from typing import Callable

import numpy as np

ALLOWED = {"safetensors", "json"}
BLOCKING = {"MEDIUM", "HIGH", "CRITICAL"}


def export_linear(model, path: Path) -> None:
    # TODO 1: lưu coef_ và intercept_ của model tuyến tính sklearn thành safetensors, metadata format=linear
    raise NotImplementedError


def load_linear(path: Path) -> Callable[[np.ndarray], np.ndarray]:
    # TODO 2: đọc lại, trả hàm predict(X) không cần sklearn hay pickle
    raise NotImplementedError


def file_formats(model_dir: Path) -> dict[str, str]:
    # TODO 3: {đường dẫn tương đối: safetensors | json | pickle | symlink | other}, nhận diện theo nội dung
    raise NotImplementedError


def gate(model_dir: Path, scan, allow_pickle: bool = False) -> dict:
    # TODO 4: {"allowed": bool, "reasons": [mã đã sắp xếp]}; scan(model_dir) trả CompletedProcess của modelscan
    raise NotImplementedError
