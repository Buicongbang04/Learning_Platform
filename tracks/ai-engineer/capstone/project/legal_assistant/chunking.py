"""M03: tách điều luật thành đơn vị trích dẫn được (khoản, điểm).

Module 13 (bài Basic 01) trả chunk dạng chuỗi; ở đây mỗi chunk mang thêm **địa chỉ** (`label`) để câu trả lời trích
được "khoản 2 điểm a" chứ không chỉ "Điều 5". Module 17 (bài Intermediate 03) cho thấy gần một nửa câu bị từ chối dù
điều đúng có trong prompt, phần lớn vì cả điều bị cắt ở 1 500 ký tự: đây là chỗ sửa.
"""

from __future__ import annotations

from dataclasses import dataclass

from .data import Article


@dataclass(frozen=True)
class Passage:
    uid: str
    label: str
    text: str


def split_clauses(article: Article, max_chars: int = 1500) -> list[Passage]:
    """Tách một điều theo khoản (dòng bắt đầu `1. `, `2. `...); khoản dài hơn `max_chars` mà có điểm (`a) `,
    `b) `, `đ) `...) thì tách tiếp theo điểm.

    - Văn bản được `normalize` trước. `text` của mọi passage bắt đầu bằng tiêu đề điều (dòng riêng); passage theo
      điểm giữ thêm các dòng dẫn của khoản trước điểm đầu tiên.
    - `label`: `""` cho phần dẫn trước khoản 1 (hoặc cả điều khi không có khoản), `"khoản 2"`, `"khoản 2 điểm a"`.
    - Điều không có nội dung: một passage chỉ có tiêu đề. `uid` luôn là uid của điều.
    - "150.000 đồng" hay "1.5" giữa dòng không phải ranh giới khoản.
    """
    raise NotImplementedError("M03: split_clauses")
