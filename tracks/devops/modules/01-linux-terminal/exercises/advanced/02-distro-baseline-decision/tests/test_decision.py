import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)
RHEL_FAMILY = re.compile(r"rhel|red hat|rocky|alma|centos stream|oracle linux", re.I)
DEBIAN_FAMILY = re.compile(r"debian|ubuntu", re.I)
BASELINE_TOPICS = {
    "ssh": re.compile(r"\bssh", re.I),
    "firewall": re.compile(r"nftables|firewalld|ufw|iptables", re.I),
    "cập nhật bảo mật": re.compile(r"unattended-upgrades|dnf-automatic|livepatch|kpatch|patch", re.I),
    "đồng bộ giờ": re.compile(r"chrony|timesyncd|ntp", re.I),
    "audit": re.compile(r"auditd|audit", re.I),
    "MAC": re.compile(r"selinux|apparmor", re.I),
    "log": re.compile(r"journald|rsyslog|log", re.I),
}


@pytest.fixture(scope="module")
def doc() -> str:
    return ex.read("DECISION.md")


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


def test_options_compared(doc):
    rows = [row for row in table_rows(section(doc, 2)) if len(row) >= 6 and all(row[:6])]
    assert len(rows) >= 3, "So sánh ít nhất 3 phương án, đủ 6 cột"
    names = " ".join(row[0] for row in rows)
    assert RHEL_FAMILY.search(names) and DEBIAN_FAMILY.search(names), "Có ít nhất một distro họ RHEL và một họ Debian"
    for row in rows:
        assert row[5].isdigit() and 1 <= int(row[5]) <= 5, f"{row[0]}: điểm là số nguyên 1–5"


def test_decision_is_one_of_options(doc):
    match = re.search(r"^Chọn:\s*(.+)$", section(doc, 3), re.M)
    assert match, "Phần 3 cần dòng 'Chọn: <distro và phiên bản>'"
    names = [row[0].lower() for row in table_rows(section(doc, 2)) if row]
    assert any(name and name in match.group(1).lower() for name in names), "Phương án chọn phải nằm trong bảng so sánh"
    assert len(section(doc, 3).strip()) >= 200, "Giải thích vì sao chọn, gắn với ràng buộc của tình huống"


def test_baseline_covers_topics(doc):
    rows = [row for row in table_rows(section(doc, 4)) if len(row) >= 3 and all(row[:3])]
    assert len(rows) >= 8, "Baseline cần ít nhất 8 hạng mục, mỗi hạng mục có cấu hình và lý do"
    text = " ".join(" ".join(row) for row in rows)
    missing = [topic for topic, pattern in BASELINE_TOPICS.items() if not pattern.search(text)]
    assert not missing, f"Baseline thiếu: {missing}"


def test_risks_and_review(doc):
    assert len(list_items(section(doc, 5))) >= 3
    assert len(list_items(section(doc, 6))) >= 2
