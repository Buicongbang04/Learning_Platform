"""M07: chặn prompt injection, phát hiện điều luật bịa, chính sách từ chối khi không có căn cứ (module 19)."""

from __future__ import annotations

from .chunking import Passage


def looks_like_injection(text: str) -> bool:
    """Heuristic rẻ cho injection trực tiếp và gián tiếp (trong câu hỏi hoặc trong tài liệu), tiếng Việt và tiếng
    Anh: "bỏ qua mọi chỉ dẫn", "ignore previous instructions", "system prompt", "bạn bây giờ là"... Chuẩn hoá NFC
    và chữ thường trước. Câu hỏi pháp luật bình thường (kể cả có chữ "bỏ qua" theo nghĩa thường) phải là `False`.

    Đây là lớp lọc đầu tiên, không phải phòng thủ đủ: module 19 đo vì sao.
    """
    raise NotImplementedError("M07: looks_like_injection")


def mentioned_articles(answer: str) -> list[tuple[int, str | None]]:
    """Các điều luật được nhắc **bằng chữ** trong câu trả lời: `(số điều, số hiệu văn bản viết thường hoặc None)`.

    "Theo Điều 5 Nghị định 100/2019/NĐ-CP" → `(5, "100/2019/nđ-cp")`; "Điều 7" đứng một mình → `(7, None)`.
    Số hiệu chỉ gắn với điều đứng ngay trước nó (không vượt qua một "Điều <n>" khác). Thứ tự xuất hiện, bỏ trùng.
    """
    raise NotImplementedError("M07: mentioned_articles")


def fabricated_references(answer: str, passages: list[Passage]) -> list[tuple[int, str | None]]:
    """Các điều được nhắc mà không có trong `passages`: có số hiệu thì so cả (số hiệu, số điều), không có số hiệu
    thì so số điều với mọi passage. Đây là đo "bịa điều luật" bằng code, không cần judge.
    """
    raise NotImplementedError("M07: fabricated_references")


def ground_or_refuse(answer: str, passages: list[Passage], refusal: str) -> tuple[str, str]:
    """Lớp kiểm cuối trước khi trả cho người dùng. Trả `(câu trả lời cuối, lý do)`:

    - đã là câu từ chối: `(refusal, "refused")`;
    - nhắc điều luật không có trong nguồn: `(refusal, "fabricated")`;
    - không có trích dẫn `[i]` hợp lệ nào: `(refusal, "no_citation")`;
    - còn lại: `(answer, "ok")`.
    """
    raise NotImplementedError("M07: ground_or_refuse")
