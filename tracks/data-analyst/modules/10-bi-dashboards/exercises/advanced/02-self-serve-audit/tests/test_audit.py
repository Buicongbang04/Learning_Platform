import datetime as dt
import json
import sys

import pytest

import testkit
from testkit import Exercise

ex = Exercise(__file__)
sys.path.insert(0, str(testkit.ROOT / "setup" / "bi"))

NOW = dt.datetime(2026, 10, 30, tzinfo=dt.timezone.utc)
KINDS = {"duplicate_name", "custom_revenue", "no_description", "stale"}


@pytest.fixture
def audit():
    return ex.module("audit.py")


@pytest.fixture
def cards():
    return json.loads((ex.fixtures / "cards.json").read_text(encoding="utf-8"))


def test_normalize_name(audit):
    assert audit.normalize_name("  Doanh Thu  theo tháng ") == "doanh thu theo tháng"
    assert audit.normalize_name("DA10 · Doanh thu: theo tháng") == audit.normalize_name("da10 doanh thu theo tháng")


def test_find_issues_tren_fixture(audit, cards):
    issues = audit.find_issues(cards, NOW)
    got = {(i["card_id"], i["issue"]) for i in issues}
    assert {c for c, k in got if k == "duplicate_name"} == {1, 2, 8}, "Tên trùng sau chuẩn hoá; card đã archive không tính"
    assert {c for c, k in got if k == "custom_revenue"} == {2, 5, 9}, "Tự tính quantity * price (mọi thứ tự, hoa thường)"
    assert {c for c, k in got if k == "no_description"} == {4, 10}, "Card trong collection official thiếu mô tả"
    assert {c for c, k in got if k == "stale"} == {5, 6}, "Không dùng 90 ngày; chưa dùng lần nào thì tính từ ngày tạo"
    assert len(issues) == len(got) == 10, "Mỗi (card, loại lỗi) một dòng"
    assert [(i["card_id"], i["issue"]) for i in issues] == sorted(got), "Sắp theo card_id rồi issue"
    assert all(i["detail"].strip() for i in issues), "Mỗi lỗi có detail giải thích"
    dup = next(i for i in issues if (i["card_id"], i["issue"]) == (2, "duplicate_name"))
    assert "1" in dup["detail"] and "8" in dup["detail"], "detail của tên trùng nêu id các card cùng tên"


def test_stale_days(audit, cards):
    issues = audit.find_issues(cards, NOW, stale_days=30)
    assert {i["card_id"] for i in issues if i["issue"] == "stale"} == {5, 6, 8, 10}


def test_summarize(audit, cards):
    assert audit.summarize(audit.find_issues(cards, NOW)) == {
        "custom_revenue": 3, "duplicate_name": 3, "no_description": 2, "stale": 2,
    }


def test_memo_da_viet():
    memo = ex.read("AUDIT_MEMO.md")
    assert "TODO" not in memo, "Viết xong AUDIT_MEMO.md"
    for heading in ("## Phát hiện", "## Đề xuất", "## Kế hoạch 30 ngày"):
        assert heading in memo


def test_live_metabase(audit):
    """Chạy audit trên Metabase thật của bạn: kiểm code chịu được mọi loại card (MBQL, native, không collection)."""
    if not testkit.service_up("metabase"):
        pytest.skip("Metabase chưa chạy. Bật BI bằng: docker compose -f setup/docker-compose.yml --profile bi up -d "
                    "postgres metabase superset && uv run python setup/bi/init_bi.py")
    ex.require_service("metabase")
    import clients

    try:
        session = clients.metabase_session()
    except RuntimeError as e:
        pytest.skip(str(e))
    inventory = audit.fetch_inventory(session)
    assert inventory and all("dataset_query" in c for c in inventory)
    issues = audit.find_issues(inventory, dt.datetime.now(dt.timezone.utc))
    ids = {c["id"] for c in inventory}
    assert all(i["card_id"] in ids and i["issue"] in KINDS for i in issues)
