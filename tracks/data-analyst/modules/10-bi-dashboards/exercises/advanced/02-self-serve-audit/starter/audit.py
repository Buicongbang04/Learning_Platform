"""Audit kho câu hỏi Metabase self-serve: tên trùng, tự tính doanh thu, thiếu mô tả, card bỏ hoang.

    uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/advanced/02-self-serve-audit/starter/audit.py

Chạy trên Metabase thật khi BI đang bật; không bật thì chạy trên tests/fixtures/cards.json.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cards.json"


def fetch_inventory(session) -> list[dict]:
    """Mọi card (question/model) trong Metabase: GET /api/card. Mỗi card có id, name, archived, description,
    dataset_query, collection (None ở root; có authority_level), created_at, last_used_at."""
    return session.get("/api/card").json()


def normalize_name(name: str) -> str:
    """Chữ thường, bỏ dấu câu (· : - ( ) ...), gộp khoảng trắng: so tên trùng không phụ thuộc cách gõ."""
    # TODO
    raise NotImplementedError


def find_issues(cards: list[dict], now: dt.datetime, stale_days: int = 90) -> list[dict]:
    """Danh sách {"card_id", "issue", "detail"} sắp theo (card_id, issue). Bỏ qua card archived.

    issue:
    - duplicate_name: từ 2 card trở lên cùng normalize_name; detail nêu id các card cùng tên.
    - custom_revenue: SQL native tự nhân quantity * price (hoặc price * quantity, mọi hoa thường, có/không khoảng
      trắng) thay vì dùng cột revenue đã chuẩn hoá.
    - no_description: card nằm trong collection có authority_level "official" mà description rỗng/None/khoảng trắng.
    - stale: last_used_at cũ hơn `now - stale_days`; chưa dùng lần nào (None) thì xét created_at.
    Thời gian dạng ISO "2026-10-28T08:00:00Z" (có thể có phần lẻ giây).
    """
    # TODO
    raise NotImplementedError


def summarize(issues: list[dict]) -> dict[str, int]:
    """{issue: số card}, khoá sắp theo tên."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "setup" / "bi"))
    try:
        import clients

        cards = fetch_inventory(clients.metabase_session())
        source = "Metabase"
    except Exception as e:  # noqa: BLE001 - BI chưa bật: dùng fixture
        print(f"Không gọi được Metabase ({e.__class__.__name__}), dùng fixture.")
        cards, source = json.loads(FIXTURE.read_text(encoding="utf-8")), "fixture"
    issues = find_issues(cards, dt.datetime.now(dt.timezone.utc))
    print(f"{source}: {len(cards)} card, {summarize(issues)}")
    for i in issues:
        print(f"- #{i['card_id']} {i['issue']}: {i['detail']}")
