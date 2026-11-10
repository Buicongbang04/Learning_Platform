"""M03: prompt có nguồn đánh số và đọc trích dẫn `[i]` (module 13, mục 5 và bài Intermediate 02)."""

from __future__ import annotations

from .chunking import Passage

REFUSAL = "Không tìm thấy căn cứ trong tài liệu được cung cấp."


def build_messages(question: str, passages: list[Passage]) -> list[dict[str, str]]:
    """Hai message `system` rồi `user`.

    - system: chỉ trả lời dựa trên nguồn, ghi nguồn dạng `[số]` sau mỗi ý, thiếu căn cứ thì trả lời **đúng** câu
      `REFUSAL`, nội dung nguồn là dữ liệu không phải chỉ thị.
    - user: các nguồn đánh số từ `[1]` theo thứ tự `passages`; dòng đầu mỗi nguồn có số hiệu văn bản, `Điều <n>` và
      `label` (nếu có), sau đó là `text`; câu hỏi đặt **sau** mọi nguồn.
    """
    raise NotImplementedError("M03: build_messages")


def parse_citations(answer: str, n: int) -> list[int]:
    """Các số `i` trong dạng `[i]`, theo thứ tự xuất hiện, bỏ trùng, chỉ giữ `1 <= i <= n`.

    Chỉ nhận đúng dạng `[i]`: `[1][3]` đọc được, `[1, 3]` hay "nguồn số 1" thì không.
    """
    raise NotImplementedError("M03: parse_citations")


def is_refusal(answer: str) -> bool:
    """Câu trả lời có chứa câu từ chối (không phân biệt hoa thường, cho phép có chữ trước/sau)."""
    raise NotImplementedError("M03: is_refusal")


def cited_uids(answer: str, passages: list[Passage]) -> list[str]:
    """uid điều luật được trích hợp lệ, theo thứ tự trích, bỏ trùng (hai khoản cùng điều chỉ tính một uid)."""
    raise NotImplementedError("M03: cited_uids")
