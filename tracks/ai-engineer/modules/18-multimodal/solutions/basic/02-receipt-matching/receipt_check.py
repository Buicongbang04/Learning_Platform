"""Chấm hoá đơn trích xuất so với nhãn CORD, không dùng LLM: chuẩn hoá số tiền, ghép dòng hàng, tổng hợp."""

from __future__ import annotations

import difflib
import re

_NUMBER = re.compile(r"\d[\d.,]*")


def parse_amount(text) -> float | None:
    """Số tiền in trên hoá đơn thành số: "60.000" -> 60000, "24,000" -> 24000, "1.234,50" -> 1234.5."""
    if text is None or isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text).replace(" ", "").replace(" ", "")
    match = _NUMBER.search(s)
    if not match:
        return None
    token = match.group().rstrip(".,")
    head = s[: match.start()]
    negative = "-" in head or head.endswith("(")
    seps = [ch for ch in token if ch in ".,"]
    if not seps:
        value = float(token)
    elif len(set(seps)) == 2:
        decimal = token[max(token.rfind("."), token.rfind(","))]
        thousands = "," if decimal == "." else "."
        whole, frac = token.replace(thousands, "").split(decimal)
        value = float(f"{whole}.{frac}")
    else:
        sep = seps[0]
        groups = token.split(sep)
        if all(len(g) == 3 for g in groups[1:]) and 1 <= len(groups[0]) <= 3:
            value = float("".join(groups))
        elif len(groups) == 2:
            value = float(f"{groups[0]}.{groups[1]}")
        else:
            return None
    return -value if negative else value


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _quantity(raw) -> float:
    if raw is None:
        return 1.0
    value = parse_amount(str(raw).lower().replace("x", " "))
    return value if value is not None else 1.0


def gold_from_cord(gt_parse: dict) -> dict:
    """{"items": [{"name", "quantity", "amount"}], "total": float | None} từ `gt_parse` của CORD."""
    items = []
    for entry in _as_list(gt_parse.get("menu")):
        for row in [entry, *_as_list(entry.get("sub"))]:
            amount = parse_amount(row.get("price"))
            if amount is None:
                continue
            items.append({"name": str(row.get("nm", "")), "quantity": _quantity(row.get("cnt")), "amount": amount})
    total = gt_parse.get("total")
    total_value = parse_amount(total.get("total_price")) if isinstance(total, dict) else None
    return {"items": items, "total": total_value}


def _norm_name(name: str) -> str:
    return " ".join(re.sub(r"[^0-9A-Z]+", " ", str(name).upper()).split())


def name_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm_name(a), _norm_name(b)).ratio()


def match_items(pred: list[dict], gold: list[dict], min_name_sim: float = 0.5) -> list[tuple[int, int]]:
    """Ghép một-một (chỉ số pred, chỉ số gold): cùng số tiền và tên đủ giống, ưu tiên cặp giống nhất."""
    candidates = []
    for i, p in enumerate(pred):
        pa = parse_amount(p.get("amount"))
        if pa is None:
            continue
        for j, g in enumerate(gold):
            if abs(pa - g["amount"]) > 0.5:
                continue
            sim = name_similarity(p.get("name", ""), g["name"])
            if sim >= min_name_sim:
                candidates.append((-sim, i, j))
    used_p, used_g, pairs = set(), set(), []
    for _, i, j in sorted(candidates):
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        pairs.append((i, j))
    return sorted(pairs)


def score_receipt(pred: dict | None, gold: dict) -> dict:
    """Điểm một hoá đơn. `pred` None (JSON hỏng) thì không dòng nào đúng và tổng sai."""
    pred = pred or {"items": [], "total": None}
    items = pred.get("items") or []
    pairs = match_items(items, gold["items"])
    qty_ok = sum(abs(_quantity(items[i].get("quantity")) - gold["items"][j]["quantity"]) < 1e-6 for i, j in pairs)
    total_ok = None
    if gold["total"] is not None:
        predicted = parse_amount(pred.get("total"))
        total_ok = predicted is not None and abs(predicted - gold["total"]) <= 0.5
    return {"total_ok": total_ok, "n_pred": len(items), "n_gold": len(gold["items"]), "n_match": len(pairs),
            "qty_ok": qty_ok}


def aggregate(scores: list[dict]) -> dict:
    """Micro precision/recall/F1 dòng hàng, độ đúng tổng tiền (trên hoá đơn có nhãn tổng), độ đúng số lượng."""
    if not scores:
        raise ValueError("không có hoá đơn nào")
    n_pred = sum(s["n_pred"] for s in scores)
    n_gold = sum(s["n_gold"] for s in scores)
    n_match = sum(s["n_match"] for s in scores)
    with_total = [s["total_ok"] for s in scores if s["total_ok"] is not None]
    precision = n_match / n_pred if n_pred else 0.0
    recall = n_match / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"receipts": len(scores), "total_acc": sum(with_total) / len(with_total) if with_total else float("nan"),
            "item_precision": precision, "item_recall": recall, "item_f1": f1,
            "qty_acc": sum(s["qty_ok"] for s in scores) / n_match if n_match else float("nan")}
