import re

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
MEMO_HEADINGS = ["## Khuyến nghị", "## Câu hỏi và cách đo", "## Kết quả", "## Độ tin cậy của số",
                 "## Nguồn dữ liệu", "## Bước tiếp theo"]
WB = pd.DataFrame({
    "iso3": ["IRL", "NLD", "DEU", "CZE", "HKG", "ZAF", "USA", "CHI"],
    "name": ["Ireland", "Netherlands", "Germany", "Czechia", "Hong Kong SAR, China", "South Africa",
             "United States", "Channel Islands"],
})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("market_sizing.ipynb")


def test_match_countries(nb):
    names = ["EIRE", "Netherlands", " germany ", "Czech Republic", "European Community", "Unspecified",
             "Channel Islands", "RSA"]
    aliases = {"EIRE": "IRL", "Czech Republic": "CZE", "RSA": "ZAF", "European Community": None}
    out = nb.match_countries(names, WB, aliases)
    assert list(out.columns) == ["name", "iso3", "method"]
    assert out["name"].tolist() == names
    assert out["iso3"].tolist()[:4] == ["IRL", "NLD", "DEU", "CZE"]
    assert out["method"].tolist() == ["alias", "exact", "exact", "alias", "unmatched", "unmatched", "exact", "alias"]
    assert out["iso3"].isna().tolist() == [False, False, False, False, True, True, False, False]


def test_match_countries_rejects_bad_alias(nb):
    with pytest.raises(ValueError):
        nb.match_countries(["EIRE"], WB, {"EIRE": "IRE"})  # mã ISO3 không tồn tại: lỗi gõ phải lộ ra ngay


def test_coverage(nb):
    revenue = pd.Series({"EIRE": 266_080.0, "Netherlands": 264_934.0, "Unspecified": 4_750.0,
                         "European Community": 1_300.0, "Germany": 205_642.0})
    matched = pd.DataFrame({"name": ["EIRE", "Netherlands", "Unspecified", "European Community", "Germany"],
                            "iso3": ["IRL", "NLD", None, None, "DEU"],
                            "method": ["alias", "exact", "unmatched", "unmatched", "exact"]})
    out = nb.coverage(revenue, matched)
    assert out["matched_share"] == pytest.approx(736_656 / 742_706)
    assert out["unmatched"] == ["Unspecified", "European Community"]


def test_memo_filled():
    text = ex.read("MEMO.md")
    assert "TODO" not in text, "MEMO.md còn TODO"
    positions = [text.find(h) for h in MEMO_HEADINGS]
    assert all(p >= 0 for p in positions), "MEMO.md thiếu mục bắt buộc"
    assert positions == sorted(positions), "Các mục phải theo đúng thứ tự"
    words = len(re.findall(r"\w+", text))
    assert 300 <= words <= 1000, f"MEMO.md có {words} từ, cần 300-1000"
