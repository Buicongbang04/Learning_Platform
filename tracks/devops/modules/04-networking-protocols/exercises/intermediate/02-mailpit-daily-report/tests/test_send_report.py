import os
import random
import re
import socket
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
import pytest

from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
HOST = os.environ.get("MAILPIT_HOST", "localhost")
SMTP_PORT = int(os.environ.get("MAILPIT_SMTP_PORT", "11025"))
API = f"http://{HOST}:{int(os.environ.get('MAILPIT_HTTP_PORT', '18025'))}/api/v1"
CSV = (
    "order_id,customer_state,order_status,payment_value\n"
    "e481f51cbdc54678b7cc49136f2d6af7,SP,delivered,38.71\n"
    "53cdb2fc8bc7dce0b6741e2150273451,BA,delivered,141.46\n"
    "47770eb9100c2d0c44946d9cf07ec65d,GO,canceled,179.12\n"
    "949d5b44dbf5de918fe9c16f97b45f8a,RN,shipped,72.20\n"
)
HTTP = httpx.Client(trust_env=False, timeout=5)
TEXT_LINES = ["Đơn hàng hợp lệ: 3", "Doanh thu (BRL): 252.37", "Đơn huỷ: 1"]


@pytest.fixture(autouse=True)
def mailpit():
    ex.require_service("mailpit")
    try:
        HTTP.get(f"{API}/messages", params={"limit": 1}).raise_for_status()
    except httpx.HTTPError as exc:
        pytest.skip(f"SMTP của Mailpit mở nhưng API {API} không trả lời ({exc})")


def unique_date() -> str:
    rng = random.SystemRandom()
    return f"{rng.randint(1970, 2099)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def find(subject: str) -> list[dict]:
    reply = HTTP.get(f"{API}/search", params={"query": f'subject:"{subject}"', "limit": 50})
    reply.raise_for_status()
    return [m for m in reply.json()["messages"] if m["Subject"] == subject]


def purge(subject: str) -> None:
    ids = [m["ID"] for m in find(subject)]
    if ids:
        HTTP.request("DELETE", f"{API}/messages", json={"IDs": ids}).raise_for_status()


def run(tmp_path: Path, *args: str, csv: str = CSV, port: int = SMTP_PORT, host: str = HOST):
    data = tmp_path / "orders.csv"
    data.write_text(csv, encoding="utf-8")
    cmd = [sys.executable, ex.path("send_report.py"), "--host", host, "--port", str(port), "--csv", data, *args]
    return run_sandboxed(cmd, writable=[tmp_path], cwd=tmp_path, env={}, timeout=40)


@pytest.fixture
def report_date():
    date = unique_date()
    subject = f"[Olist Shop] Báo cáo đơn hàng {date}"
    purge(subject)
    yield date, subject
    purge(subject)


def test_sends_complete_report(tmp_path, report_date):
    date, subject = report_date
    result = run(tmp_path, "--date", date, "--to", "ops@olist-shop.com.br", "--to", "cfo@olist-shop.com.br", "--bcc", "audit@olist-shop.com.br")
    assert result.returncode == 0, f"exit {result.returncode}\nstderr:\n{result.stderr}"
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 1 and re.fullmatch(r"<[^<>@\s]+@olist-shop\.com\.br>", lines[0]), f"stdout phải là đúng một Message-ID: {result.stdout!r}"
    found = find(subject)
    assert len(found) == 1, f"Mailpit phải có đúng 1 thư tiêu đề {subject!r}, có {len(found)}"
    msg = HTTP.get(f"{API}/message/{found[0]['ID']}").json()
    headers = HTTP.get(f"{API}/message/{found[0]['ID']}/headers").json()

    assert f"<{msg['MessageID']}>" == lines[0], "Message-ID in ra phải trùng Message-ID trong thư"
    assert (msg["From"]["Name"], msg["From"]["Address"]) == ("Olist Shop Reports", "reports@olist-shop.com.br")
    assert sorted(a["Address"] for a in msg["To"]) == ["cfo@olist-shop.com.br", "ops@olist-shop.com.br"]
    assert [a["Address"] for a in msg["Bcc"]] == ["audit@olist-shop.com.br"], "audit phải nhận qua envelope (Bcc), không nằm trong To/Cc"
    assert msg["Cc"] == [] or msg["Cc"] is None
    assert [a["Address"] for a in msg["ReplyTo"]] == ["ops@olist-shop.com.br"]
    assert msg["ReturnPath"] == "bounces@olist-shop.com.br", "MAIL FROM (envelope sender) phải là bounces@olist-shop.com.br"
    assert headers.get("Auto-Submitted") == ["auto-generated"]
    sent = parsedate_to_datetime(headers["Date"][0])
    assert sent.tzinfo is not None, "Header Date phải có múi giờ"

    unsubscribe = msg["ListUnsubscribe"]
    assert unsubscribe["Errors"] == "", unsubscribe["Errors"]
    assert any(link.startswith("mailto:") for link in unsubscribe["Links"])
    assert any(link.startswith("https://") for link in unsubscribe["Links"])
    assert unsubscribe["HeaderPost"] == "List-Unsubscribe=One-Click"

    text_lines = [line.strip() for line in msg["Text"].splitlines()]
    for expected in [f"Ngày: {date}", *TEXT_LINES]:
        assert expected in text_lines, f"Phần text thiếu dòng {expected!r}:\n{msg['Text']}"
    assert "252.37" in msg["HTML"] and "<" in msg["HTML"], "Phải có phần HTML chứa doanh thu"
    attachments = [(a["FileName"], a["ContentType"]) for a in msg["Attachments"]]
    assert attachments == [(f"orders-{date}.csv", "text/csv")], attachments
    part = HTTP.get(f"{API}/message/{found[0]['ID']}/part/{msg['Attachments'][0]['PartID']}")
    assert part.content.decode("utf-8").replace("\r\n", "\n") == CSV


def test_message_ids_are_unique(tmp_path, report_date):
    date, subject = report_date
    first = run(tmp_path, "--date", date, "--to", "ops@olist-shop.com.br")
    second = run(tmp_path, "--date", date, "--to", "ops@olist-shop.com.br")
    assert first.returncode == 0 and second.returncode == 0, first.stderr + second.stderr
    assert first.stdout.strip() != second.stdout.strip()
    assert len(find(subject)) == 2


@pytest.mark.parametrize(
    "case",
    ["missing-to", "bad-date", "missing-csv", "missing-column", "bad-amount"],
)
def test_invalid_input_exits_2_and_sends_nothing(tmp_path, report_date, case):
    date, subject = report_date
    if case == "missing-to":
        result = run(tmp_path, "--date", date)
    elif case == "bad-date":
        bad_subject = "[Olist Shop] Báo cáo đơn hàng 2026-13-40"
        purge(bad_subject)
        result = run(tmp_path, "--date", "2026-13-40", "--to", "ops@olist-shop.com.br")
        assert find(bad_subject) == [], "Ngày sai thì không được gửi thư"
    elif case == "missing-csv":
        cmd = [sys.executable, ex.path("send_report.py"), "--host", HOST, "--port", str(SMTP_PORT), "--csv", tmp_path / "nope.csv", "--date", date, "--to", "ops@olist-shop.com.br"]
        result = run_sandboxed(cmd, writable=[tmp_path], cwd=tmp_path, env={}, timeout=40)
    elif case == "missing-column":
        result = run(tmp_path, "--date", date, "--to", "ops@olist-shop.com.br", csv="order_id,order_status\nx,delivered\n")
    else:
        result = run(tmp_path, "--date", date, "--to", "ops@olist-shop.com.br", csv=CSV.replace("72.20", "R$ 72.20"))
    assert result.returncode == 2, f"{case}: exit phải là 2, đang là {result.returncode}\n{result.stderr}"
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == "", f"{case}: stdout phải rỗng khi lỗi"
    assert find(subject) == [], f"{case}: dữ liệu sai thì không được gửi thư"


def test_smtp_down_exits_3_without_traceback(tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]
    result = run(tmp_path, "--date", unique_date(), "--to", "ops@olist-shop.com.br", port=closed_port, host="127.0.0.1")
    assert result.returncode == 3, f"exit phải là 3, đang là {result.returncode}\n{result.stderr}"
    assert result.stderr.startswith("smtp error:"), result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == ""
