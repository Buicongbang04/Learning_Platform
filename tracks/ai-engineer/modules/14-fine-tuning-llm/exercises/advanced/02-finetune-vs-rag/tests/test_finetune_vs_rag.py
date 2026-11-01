import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("finetune_vs_rag.ipynb")


def test_citation(nb):
    assert nb.citation("47/2011/tt-bca+7") == "47/2011/tt-bca, Điều 7"
    assert nb.citation("100/2019/nđ-cp+5") == "100/2019/nđ-cp, Điều 5"
    assert nb.citation("01/2009/tt-bnn+12") == "01/2009/tt-bnn, Điều 12"


@pytest.mark.parametrize("text,expected", [
    ("47/2011/tt-bca, Điều 7", "47/2011/tt-bca+7"),
    ("100/2019/NĐ-CP, điều 05", "100/2019/nđ-cp+5"),
    ("Căn cứ 168/2024/NĐ-CP ,  Điều 6 thì phạt tiền", "168/2024/nđ-cp+6"),
    ("Theo 59/2020/qh14, Điều 3 và 47/2011/tt-bca, Điều 7", "59/2020/qh14+3"),
    ("Luật 23/2008/QH12.v2, Điều 10", "23/2008/qh12.v2+10"),
    ("Điều 7 Thông tư 47/2011/TT-BCA", None),
    ("47/2011/tt-bca Điều 7", None),
    ("Không tìm thấy căn cứ.", None),
    ("", None),
])
def test_parse_citation(nb, text, expected):
    assert nb.parse_citation(text) == expected


def test_parse_roundtrip(nb):
    for uid in ["47/2011/tt-bca+7", "100/2019/nđ-cp+74", "01/2009/tt-bnn+1"]:
        assert nb.parse_citation(nb.citation(uid)) == uid


def test_citation_scores(nb):
    gold = [{"a/1+3"}, {"b/2+1", "b/2+4"}, {"c+9"}, {"d+1"}]
    preds = ["a/1+3", "b/2+7", None, "e+1"]
    out = nb.citation_scores(preds, gold)
    assert out == pytest.approx({"exact": 0.25, "law": 0.5, "format": 0.75})
    assert nb.citation_scores(["b/2+4"], [{"b/2+1", "b/2+4"}])["exact"] == 1.0
    assert nb.citation_scores(["b/22+1"], [{"b/2+1"}])["law"] == 0.0, "văn bản so nguyên chuỗi, không so tiền tố"
    assert nb.citation_scores(["b/2+1"], [{"b/22+1"}])["law"] == 0.0, "văn bản so nguyên chuỗi, không so tiền tố"


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 400, "báo cáo: ít nhất 400 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng số liệu"
