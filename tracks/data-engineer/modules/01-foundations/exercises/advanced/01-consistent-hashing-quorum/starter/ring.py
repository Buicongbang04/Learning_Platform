"""Consistent hashing ring có virtual node và kho key-value nhân bản theo quorum (mô phỏng Dynamo)."""

from __future__ import annotations

import bisect
import hashlib
from collections.abc import Iterable
from typing import Any


def stable_hash(key: str) -> int:
    """Băm ổn định giữa các lần chạy (hash() của Python bị ngẫu nhiên hoá theo tiến trình)."""
    return int.from_bytes(hashlib.md5(key.encode("utf-8")).digest()[:8], "big")


class QuorumError(Exception):
    """Không đủ replica còn sống để đạt quorum đọc/ghi."""


class HashRing:
    """Vòng băm: mỗi node vật lý có `vnodes` điểm `stable_hash(f"{node}#{i}")` trên vòng."""

    def __init__(self, nodes: Iterable[str] = (), vnodes: int = 100):
        if vnodes < 1:
            raise ValueError("vnodes phải >= 1")
        self.vnodes = vnodes
        # TODO: chọn cấu trúc dữ liệu cho vòng (gợi ý: list hash đã sắp xếp + dict hash -> node)
        for node in nodes:
            self.add_node(node)

    @property
    def nodes(self) -> set[str]:
        # TODO: tập node vật lý hiện có
        raise NotImplementedError

    def add_node(self, node: str) -> None:
        # TODO: thêm vnodes điểm; ValueError nếu node đã có
        raise NotImplementedError

    def remove_node(self, node: str) -> None:
        # TODO: bỏ mọi điểm của node; KeyError nếu không có
        raise NotImplementedError

    def get_node(self, key: str) -> str:
        """Node sở hữu key: điểm đầu tiên có hash >= stable_hash(key), vòng lại đầu nếu vượt cuối."""
        # TODO: LookupError nếu vòng rỗng; dùng bisect
        raise NotImplementedError

    def get_nodes(self, key: str, n: int) -> list[str]:
        """n node vật lý KHÁC NHAU gặp đầu tiên khi đi theo chiều kim đồng hồ từ key."""
        # TODO: phần tử đầu == get_node(key); ValueError nếu n > số node
        raise NotImplementedError


class QuorumStore:
    """Kho key-value nhân bản N bản, ghi cần W xác nhận, đọc hỏi R replica.

    `self.data[node][key] = (version, value)` mô phỏng ổ đĩa của từng node.
    """

    def __init__(self, ring: HashRing, n: int = 3, r: int = 2, w: int = 2):
        # TODO: kiểm tra 1 <= r <= n, 1 <= w <= n, n <= số node (ValueError)
        self.ring = ring
        self.n, self.r, self.w = n, r, w
        self.data: dict[str, dict[str, tuple[int, Any]]] = {node: {} for node in ring.nodes}
        self.down: set[str] = set()

    def mark_down(self, node: str) -> None:
        self.down.add(node)

    def mark_up(self, node: str) -> None:
        self.down.discard(node)

    def put(self, key: str, value: Any) -> int:
        """Ghi vào mọi replica còn sống của key; cần ít nhất W. Trả version mới."""
        # TODO: replica = ring.get_nodes(key, n); không đủ W replica sống => QuorumError, không ghi gì
        #       version mới = 1 + version lớn nhất đang có trên các replica sống
        raise NotImplementedError

    def get(self, key: str) -> Any:
        """Đọc R replica sống đầu tiên (theo thứ tự vòng), trả value có version cao nhất.

        Read repair: ghi bản mới nhất đè lên replica nào trong R replica đó đang cũ hoặc thiếu.
        Key không tồn tại => None. Không đủ R replica sống => QuorumError.
        """
        # TODO
        raise NotImplementedError
