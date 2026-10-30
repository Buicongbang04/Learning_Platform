import copy
import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
REVIEW_HEADINGS = ["## Tóm tắt thay đổi", "## Vấn đề chặn merge", "## Ảnh hưởng tới số liệu", "## Góp ý không chặn",
                   "## Kết luận"]


@pytest.fixture(scope="module")
def nbr():
    return ex.module("nbreview.py")


def code(source, outputs=None, count=None, metadata=None):
    return {"cell_type": "code", "source": source, "outputs": outputs or [], "execution_count": count,
            "metadata": metadata or {}}


def md(source):
    return {"cell_type": "markdown", "source": source, "metadata": {}}


def notebook(cells, metadata=None):
    return {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
            "metadata": metadata or {"kernelspec": {"name": "python3"}, "language_info": {"name": "python"}}}


def noisy():
    png = {"output_type": "display_data", "data": {"image/png": "iVBORw0KGgo="}, "metadata": {}}
    text = {"output_type": "execute_result", "execution_count": 7, "data": {"text/plain": "42"}, "metadata": {}}
    return notebook(
        [md("# Tiêu đề"),
         code(["import pandas as pd\n", "x = 1"], [text], 7, {"tags": ["explore"], "scrolled": True,
                                                            "execution": {"iopub.execute_input": "2011-12-09"}}),
         code("x + 1", [png], 12, {"collapsed": False})],
        {"kernelspec": {"name": "python3"}, "language_info": {"name": "python"}, "widgets": {"state": {}},
         "varInspector": {"window": 1}})


def test_strip_outputs(nbr):
    nb = noisy()
    before = copy.deepcopy(nb)
    out = nbr.strip_outputs(nb)
    assert nb == before, "strip_outputs không được sửa notebook đầu vào"
    assert set(out["metadata"]) == {"kernelspec", "language_info"}
    codes = [c for c in out["cells"] if c["cell_type"] == "code"]
    assert all(c["outputs"] == [] and c["execution_count"] is None for c in codes)
    assert codes[0]["metadata"] == {"tags": ["explore"]}
    assert codes[1]["metadata"] == {}
    assert [c["source"] for c in out["cells"]] == [c["source"] for c in nb["cells"]]
    assert "outputs" not in out["cells"][0]


def test_strip_outputs_is_idempotent(nbr):
    once = nbr.strip_outputs(noisy())
    assert nbr.strip_outputs(once) == once


def test_cell_diff_ignores_outputs_and_metadata(nbr):
    old = noisy()
    new = nbr.strip_outputs(noisy())
    new["cells"][1]["source"] = "import pandas as pd\nx = 1"      # cùng nội dung, dạng chuỗi thay vì list
    assert nbr.cell_diff(old, new) == []


def test_cell_diff_changed_added_removed(nbr):
    old = notebook([md("# A"), code("a = 1\nb = 2"), code("print(a)"), md("ghi chú cũ"), code("end = True")])
    new = notebook([md("# A"), code("a = 1\nb = 3"), code("print(a)"), code("c = a + b"), code("end = True")])
    out = nbr.cell_diff(old, new)
    assert [(c["op"], c["old_index"], c["new_index"]) for c in out] == [
        ("changed", 1, 1), ("changed", 3, 3)]
    first = out[0]["diff"].splitlines()
    assert "-b = 2" in first and "+b = 3" in first and " a = 1" in first


def test_cell_diff_insert_and_delete(nbr):
    old = notebook([code("x = 1"), code("y = 2"), code("z = 3")])
    new = notebook([code("x = 1"), code("w = 0"), code("y = 2")])
    out = nbr.cell_diff(old, new)
    assert [(c["op"], c["old_index"], c["new_index"]) for c in out] == [("added", None, 1), ("removed", 2, None)]
    assert "+w = 0" in out[0]["diff"].splitlines()
    assert "-z = 3" in out[1]["diff"].splitlines()


def test_cell_diff_on_the_pr(nbr):
    pr = ex.dir / "starter" / "pr"
    out = nbr.cell_diff(nbr.load(pr / "before.ipynb"), nbr.load(pr / "after.ipynb"))
    assert [(c["op"], c["old_index"], c["new_index"]) for c in out] == [
        ("changed", 0, 0), ("changed", 1, 1), ("changed", 2, 2), ("changed", 3, 3), ("changed", 4, 4),
        ("added", None, 5)]
    monthly = out[3]["diff"].splitlines()
    assert '-    customers=("Customer ID", "nunique"),' in monthly
    assert '+    customers=("Customer ID", "count"),' in monthly


def review_text():
    return ex.read("REVIEW.md")


def section(text, heading):
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def test_review_structure():
    text = review_text()
    assert "TODO" not in text, "Còn dòng TODO trong REVIEW.md"
    words = len(text.split())
    assert 250 <= words <= 1000, f"REVIEW.md 250-1000 từ, hiện có {words}"
    positions = [text.find(h) for h in REVIEW_HEADINGS]
    missing = [h for h, p in zip(REVIEW_HEADINGS, positions) if p < 0]
    assert not missing, f"Thiếu mục: {missing}"
    assert positions == sorted(positions), "Các mục phải theo đúng thứ tự của khung"


def test_review_content():
    text = review_text()
    assert "TODO" not in text, "Còn dòng TODO trong REVIEW.md"
    blocking = section(text, "## Vấn đề chặn merge")
    bullets = [ln for ln in blocking.splitlines() if re.match(r"\s*[-*] |\s*\d+\. ", ln)]
    assert len(bullets) >= 3, "Mục 'Vấn đề chặn merge' cần ít nhất 3 vấn đề (gạch đầu dòng hoặc đánh số)"
    impact = section(text, "## Ảnh hưởng tới số liệu")
    assert len(re.findall(r"\d[\d .,]*\d", impact)) >= 4, "Mục 'Ảnh hưởng tới số liệu' cần con số trước/sau đã chạy"
    verdict = section(text, "## Kết luận")
    assert re.search(r"Request changes|Approve", verdict), "Kết luận ghi rõ 'Request changes' hoặc 'Approve'"
