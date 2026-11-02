"""Chấm hoá đơn trích xuất so với nhãn CORD, không dùng LLM: chuẩn hoá số tiền, ghép dòng hàng, tổng hợp."""

from __future__ import annotations

import difflib
import re


def parse_amount(text) -> float | None:
    """Số tiền in trên hoá đơn thành số: "60.000" -> 60000, "24,000" -> 24000, "1.234,50" -> 1234.5; không đọc được -> None."""
    # TODO
    raise NotImplementedError


def gold_from_cord(gt_parse: dict) -> dict:
    """{"items": [{"name", "quantity", "amount"}], "total": float | None} từ `gt_parse` của CORD."""
    # TODO
    raise NotImplementedError


def name_similarity(a: str, b: str) -> float:
    """Độ giống hai tên món trong [0, 1] sau khi chuẩn hoá (chữ hoa, chỉ giữ chữ và số, gộp khoảng trắng)."""
    # TODO
    raise NotImplementedError


def match_items(pred: list[dict], gold: list[dict], min_name_sim: float = 0.5) -> list[tuple[int, int]]:
    """Ghép một-một (chỉ số pred, chỉ số gold): cùng số tiền và tên đủ giống, ưu tiên cặp giống nhất; trả list đã sắp xếp."""
    # TODO
    raise NotImplementedError


def score_receipt(pred: dict | None, gold: dict) -> dict:
    """{"total_ok", "n_pred", "n_gold", "n_match", "qty_ok"} của một hoá đơn; pred None nghĩa là JSON hỏng."""
    # TODO
    raise NotImplementedError


def aggregate(scores: list[dict]) -> dict:
    """{"receipts", "total_acc", "item_precision", "item_recall", "item_f1", "qty_acc"} gộp mức micro."""
    # TODO
    raise NotImplementedError
