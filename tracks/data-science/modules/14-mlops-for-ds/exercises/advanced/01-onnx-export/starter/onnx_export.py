"""Xuất pipeline scikit-learn sang ONNX và kiểm tra output khớp bản gốc."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def export_onnx(pipeline, numeric: list[str], categorical: list[str], path) -> Path:
    """Chuyển pipeline (ColumnTransformer + classifier, đã fit) sang ONNX, ghi ra `path`, trả Path.

    Mỗi cột là một input riêng, đúng tên cột, theo thứ tự numeric rồi categorical:
    cột số kiểu float [None, 1], cột phân loại kiểu string [None, 1].
    Output xác suất phải là ma trận (không phải list dict của ZipMap).
    """
    # TODO: skl2onnx.to_onnx(..., initial_types=[...], options={...})
    raise NotImplementedError


def onnx_predict_proba(path, df: pd.DataFrame, numeric: list[str], categorical: list[str]) -> np.ndarray:
    """Xác suất lớp 1 cho mọi dòng của df, chấm bằng onnxruntime. Trả mảng 1 chiều.

    Cột phân loại thiếu (None/NaN) được điền "missing" như lúc train. Không sửa df.
    """
    # TODO: onnxruntime.InferenceSession, dựng dict input theo tên, lấy output xác suất
    raise NotImplementedError


def parity_report(pipeline, path, df: pd.DataFrame, numeric: list[str], categorical: list[str]) -> dict:
    """So xác suất lớp 1 của scikit-learn và ONNX trên df.

    Trả ít nhất {"n": số dòng, "max_abs_diff": float, "share_within_1e-5": tỉ lệ dòng lệch <= 1e-5}.
    """
    # TODO
    raise NotImplementedError
