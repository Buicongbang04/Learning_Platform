import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
TEAM_TYPES = {"stream-aligned", "platform", "enabling", "complicated-subsystem"}
HEADCOUNT = 60


@pytest.fixture(scope="module")
def doc():
    return ex.read("PROPOSAL.md")


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


def test_problem_statement(doc):
    assert len(list_items(section(doc, 1))) >= 3


def test_teams(doc):
    rows = [row for row in table_rows(section(doc, 2)) if len(row) >= 5]
    assert len(rows) >= 3
    types = {row[1].lower() for row in rows}
    assert types <= TEAM_TYPES, f"Loại team chỉ dùng {sorted(TEAM_TYPES)}"
    assert {"stream-aligned", "platform"} <= types
    sizes = [int(row[2]) for row in rows]
    assert all(2 <= n <= 12 for n in sizes), "Một team nên từ 2 tới 12 người"
    assert sum(sizes) <= HEADCOUNT, f"Tổng người không vượt {HEADCOUNT} kỹ sư hiện có"
    assert all(row[3] and row[4] for row in rows), "Mỗi team cần ghi sở hữu gì và on-call thế nào"


def test_responsibility_matrix(doc):
    rows = [row for row in table_rows(section(doc, 3)) if len(row) >= 4]
    assert len(rows) >= 6
    assert all(all(cell for cell in row[:4]) for row in rows), "Mỗi việc phải ghi rõ vai trò của cả ba bên"


def test_transition_steps(doc):
    assert len(list_items(section(doc, 4))) >= 3


def test_risks_and_success_metrics(doc):
    rows = [row for row in table_rows(section(doc, 5)) if len(row) >= 3 and all(row[:3])]
    assert len(rows) >= 3
