"""Công cụ nhỏ để review notebook trong PR: bỏ phần nhiễu (output, execution_count), so source theo cell.

Notebook ở đây là dict đọc từ JSON (định dạng nbformat 4), không phải đối tượng nbformat.

    old, new = load("pr/before.ipynb"), load("pr/after.ipynb")
    for change in cell_diff(old, new):
        print(change["op"], change["old_index"], change["new_index"])
        print(change["diff"])
"""

import copy  # noqa: F401
import difflib  # noqa: F401
import json
from pathlib import Path

KEEP_NB_META = ("kernelspec", "language_info")      # metadata notebook được giữ lại
DROP_CELL_META = ("execution", "collapsed", "scrolled")  # metadata cell bị bỏ (giữ "tags" và các khoá khác)


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def strip_outputs(nb: dict) -> dict:
    """Bản sao (không sửa nb) với: mọi cell code có outputs = [] và execution_count = None;
    metadata cell bỏ các khoá trong DROP_CELL_META; metadata notebook chỉ giữ các khoá trong KEEP_NB_META.
    Source và thứ tự cell giữ nguyên."""
    # TODO
    raise NotImplementedError


def cell_diff(old: dict, new: dict) -> list[dict]:
    """So hai notebook theo cell, chỉ dựa trên (cell_type, source); bỏ qua output và metadata.

    `source` trong JSON có thể là chuỗi hoặc danh sách dòng: nối lại thành một chuỗi trước khi so.
    Ghép cell bằng difflib.SequenceMatcher trên danh sách (cell_type, source) của hai notebook:
      - khối "equal": bỏ qua (cell không đổi);
      - khối "replace" i1:i2 / j1:j2: ghép từng cặp theo vị trí thành "changed", phần dư là "removed" / "added";
      - khối "delete": "removed"; khối "insert": "added".
    Mỗi thay đổi là dict {"op", "old_index", "new_index", "diff"}; index là vị trí 0-based trong danh sách cell
    (None ở phía không có); diff = "\\n".join(difflib.unified_diff(cũ.splitlines(), mới.splitlines(), lineterm=""))
    với cũ = "" cho cell thêm và mới = "" cho cell bị xoá. Thứ tự kết quả theo thứ tự các khối của SequenceMatcher.
    """
    # TODO
    raise NotImplementedError
