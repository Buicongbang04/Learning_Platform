"""Feature selection trung thực: chọn feature bên trong cross-validation.

Bộ chọn dùng chung cho cả bài: SelectKBest(f_classif, k=k). Model: LogisticRegression(max_iter=1000).
Điểm: ROC-AUC trung bình qua các fold. X không có NaN.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline


def leaky_selection_auc(X, y, k: int, cv) -> float:
    """Cách SAI, viết ra để đo nó sai bao nhiêu: chọn k feature trên toàn bộ (X, y), rồi mới
    cross-validate model trên k feature đó với `cv`."""
    # TODO
    raise NotImplementedError


def honest_selection_auc(X, y, k: int, cv) -> float:
    """Cách ĐÚNG: bước chọn feature nằm trong pipeline, được học lại trong từng fold của `cv`."""
    # TODO
    raise NotImplementedError


def selection_frequency(X, y, k: int, splits) -> pd.Series:
    """Tỉ lệ fold mà mỗi feature được chọn (chỉ học trên phần train của fold).

    splits: iterable các (train_idx, test_idx). Trả Series index là tên cột của X
    (X là ndarray thì 0..p−1), giá trị trong [0, 1], sắp giảm dần.
    """
    # TODO
    raise NotImplementedError
