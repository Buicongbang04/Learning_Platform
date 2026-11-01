import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
SECTIONS = [
    "Triệu chứng và tác động",
    "Chẩn đoán",
    "Khắc phục tức thời",
    "Nguyên nhân gốc",
    "Phòng ngừa",
    "Kiểm chứng sau khắc phục",
]
RECLAIM_GIB = (27.4, 27.8)


@pytest.fixture(scope="module")
def doc() -> str:
    return ex.read("RUNBOOK.md")


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


def test_sections_in_order(doc):
    titles = re.findall(r"^## \d+\.\s+(.+?)\s*$", doc, re.M)
    assert titles == SECTIONS


def test_diagnosis_names_the_tool(doc):
    text = section(doc, 2)
    assert re.search(r"lsof\b.*\+L\s?1|/proc/\S*/fd", text), "Ghi lệnh tìm ra chỗ giữ dung lượng (công cụ và tuỳ chọn)"


def test_diagnosis_table_names_processes(doc):
    rows = [row for row in table_rows(section(doc, 2)) if len(row) >= 4]
    pids = {row[0] for row in rows}
    assert {"2481", "2519"} <= pids, "Bảng chẩn đoán phải liệt kê mọi PID đang giữ dung lượng của worker"
    assert "4410" not in pids, "Chỉ tính tệp trên filesystem /var"


def test_reclaimable_space_counts_each_inode_once(doc):
    match = re.search(r"Tổng dung lượng thu hồi được:\s*([\d.,]+)\s*GiB", section(doc, 2))
    assert match, "Ghi dòng 'Tổng dung lượng thu hồi được: <số> GiB'"
    value = float(match.group(1).replace(",", "."))
    low, high = RECLAIM_GIB
    assert low <= value <= high, "Xem lại cột NODE và DEVICE: cùng một inode chỉ tính một lần, chỉ tính filesystem /var"


def test_mitigation_steps_and_verification(doc):
    steps = list_items(section(doc, 3))
    assert len(steps) >= 3, "Khắc phục tức thời cần ít nhất 3 bước có thứ tự"
    assert re.search(r"\bdf\b", section(doc, 3) + section(doc, 6)), "Có bước đo lại bằng df"


def test_prevention_actions(doc):
    assert len(list_items(section(doc, 5))) >= 3
    assert len(section(doc, 4).strip()) >= 120, "Nguyên nhân gốc cần giải thích cơ chế, không chỉ một dòng"
