"""Đánh giá challenger chạy shadow, quyết định promote, và đổi alias trong MLflow Model Registry."""

from __future__ import annotations

import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import numpy as np
import pandas as pd
from mlflow import MlflowClient


def shadow_report(log: pd.DataFrame, threshold: float) -> dict:
    """Tóm tắt log shadow (mỗi dòng một request, chấm bởi cả champion và challenger).

    Cột của log: order_id, champion_score, challenger_score, champion_latency_ms,
    challenger_latency_ms, label (NaN nếu nhãn chưa về).

    Trả dict:
      n                          số request
      n_labeled                  số request đã có nhãn
      auc_champion, auc_challenger   ROC AUC trên các dòng có nhãn (NaN nếu chưa đủ hai lớp)
      score_psi                  PSI của challenger_score so với champion_score (10 bin quantile,
                                 biên ngoài vô cực, eps 1e-4, như bài Basic 01)
      flip_rate                  tỉ lệ request mà hai model cho quyết định khác nhau ở `threshold`
                                 (score >= threshold là "liên hệ khách")
      p95_latency_champion_ms, p95_latency_challenger_ms   percentile 95 của độ trễ
    """
    # TODO
    raise NotImplementedError


def promotion_decision(report: dict, min_labeled: int = 500, min_auc_gain: float = 0.005,
                       max_p95_latency_ms: float = 50.0, max_flip_rate: float = 0.2) -> str:
    """Một trong "need_more_data", "keep", "manual_review", "promote", xét theo thứ tự:

    1. n_labeled < min_labeled                                   -> "need_more_data"
    2. p95 challenger > max_p95_latency_ms, hoặc
       auc_challenger - auc_champion < min_auc_gain              -> "keep"
    3. flip_rate > max_flip_rate (đổi hành vi quá nhiều để tự động) -> "manual_review"
    4. còn lại                                                    -> "promote"
    """
    # TODO
    raise NotImplementedError


def apply_decision(tracking_uri: str, model_name: str, challenger_version: int, decision: str) -> dict:
    """Thực thi quyết định trên registry và trả các alias hiện có dạng {alias: version (int)}.

    "promote": alias previous_champion trỏ vào champion cũ (nếu có), champion trỏ vào challenger,
    xoá alias challenger (nếu có). Quyết định khác: không đổi gì.
    """
    # TODO: client.get_registered_model(model_name).aliases cho dict alias -> version
    raise NotImplementedError


def rollback(tracking_uri: str, model_name: str) -> int:
    """Trỏ champion về previous_champion, xoá alias previous_champion, trả version champion mới.

    Không có previous_champion thì ValueError.
    """
    # TODO
    raise NotImplementedError
