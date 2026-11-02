"""M05: dữ liệu fine-tune embedding từ split train, không rò rỉ sang tập đánh giá."""

from __future__ import annotations

from .data import Article, Question


def check_no_leak(train: list[Question], evaluation: list[Question]) -> None:
    """`ValueError` nếu một `qid` có ở cả hai tập, hoặc một câu đánh giá trùng chữ với một câu train sau
    `normalize` và chữ thường. Thông điệp lỗi nêu số câu bị trùng.
    """
    raise NotImplementedError("M05: check_no_leak")


def hard_negatives(ranking: list[str], relevant: set[str], n: int, skip_same_law: bool = False) -> list[str]:
    """Tối đa `n` uid đầu tiên của `ranking` không thuộc `relevant`, bỏ trùng, giữ thứ tự.

    `skip_same_law=True`: bỏ cả uid cùng văn bản (cùng số hiệu) với một điều đúng, vì điều cùng văn bản hay là
    "đúng một nửa" và dạy model đẩy chúng ra xa là dạy sai.
    """
    raise NotImplementedError("M05: hard_negatives")


def training_pairs(questions: list[Question], articles: dict[str, Article]) -> list[tuple[str, str]]:
    """Một cặp `(câu hỏi, title + "\\n" + text)` cho mỗi điều đúng của mỗi câu (điều theo thứ tự uid tăng dần);
    uid không có trong `articles` thì bỏ qua.
    """
    raise NotImplementedError("M05: training_pairs")
