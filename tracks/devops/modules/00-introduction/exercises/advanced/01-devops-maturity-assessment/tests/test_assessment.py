import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BANDS = {"elite", "high", "medium", "low"}
EXPECTED_BANDS = {
    "deployment frequency": "medium",
    "change lead time": "medium",
    "change failure rate": "low",
    "failed deployment recovery time": "low",
}
PILLARS = ["culture", "automation", "lean", "measurement", "sharing"]
METRIC_WORDS = ("deployment frequency", "lead time", "change failure rate", "recovery", "reliability", "rework")


@pytest.fixture(scope="module")
def doc():
    return ex.read("ASSESSMENT.md")


def section(doc: str, number: int) -> str:
    match = re.search(rf"^## {number}\..*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    assert match, f"Thiếu phần '## {number}.'"
    return match.group(1)


def table_rows(text: str) -> list[list[str]]:
    rows = [line.strip().strip("|").split("|") for line in text.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in row] for row in rows[2:]]


def list_items(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*(?:\d+\.|-)\s+(.+)$", text, re.M)]


def test_no_todo_left(doc):
    assert "TODO" not in doc


def test_dora_bands_match_case(doc):
    rows = table_rows(section(doc, 1))
    got = {row[0].lower(): row[2].lower() for row in rows if len(row) >= 3}
    for metric, band in EXPECTED_BANDS.items():
        assert metric in got, f"Thiếu dòng {metric}"
        assert got[metric] in BANDS, f"{metric}: mức phải là một trong {sorted(BANDS)}"
        assert got[metric] == band, f"{metric}: xem lại bảng DORA 2024 và số liệu của tình huống"


def test_calms_scored_with_evidence(doc):
    rows = {row[0].lower(): row for row in table_rows(section(doc, 2)) if row}
    for pillar in PILLARS:
        assert pillar in rows, f"Thiếu trụ cột {pillar}"
        score, evidence = rows[pillar][1], rows[pillar][2]
        assert score.isdigit() and 1 <= int(score) <= 5, f"{pillar}: điểm là số nguyên 1–5"
        assert len(evidence) >= 30, f"{pillar}: cần bằng chứng cụ thể từ tình huống"


def test_root_causes(doc):
    assert len(list_items(section(doc, 3))) >= 3


def test_plan_tied_to_metrics(doc):
    rows = [row for row in table_rows(section(doc, 4)) if len(row) >= 4 and all(row[:4])]
    assert len(rows) >= 3, "Kế hoạch cần ít nhất 3 việc, mỗi việc đủ 4 cột"
    named = set()
    for row in rows:
        hits = {w for w in METRIC_WORDS if w in row[1].lower()}
        assert hits, f"Việc '{row[0]}' phải nêu metric DORA nó nhắm tới"
        named |= hits
    assert len(named) >= 2, "Kế hoạch nên tác động ít nhất 2 metric khác nhau"


def test_not_doing_list(doc):
    assert len(list_items(section(doc, 5))) >= 2
