import argparse
import csv
import smtplib
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape
from pathlib import Path

DOMAIN = "olist-shop.com.br"
SENDER = ("Olist Shop Reports", f"reports@{DOMAIN}")
ENVELOPE_FROM = f"bounces@{DOMAIN}"
REPLY_TO = f"ops@{DOMAIN}"
UNSUBSCRIBE = f"<mailto:unsubscribe@{DOMAIN}?subject=unsubscribe>, <https://{DOMAIN}/unsubscribe/reports>"
COLUMNS = {"order_id", "order_status", "payment_value"}


class InputError(Exception):
    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gửi báo cáo đơn hàng trong ngày qua SMTP")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--to", action="append", required=True)
    parser.add_argument("--bcc", action="append", default=[])
    return parser.parse_args(argv)


def summarize(path: Path) -> tuple[int, Decimal, int, str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"không đọc được {path}: {exc.strerror}") from exc
    rows = list(csv.DictReader(raw.splitlines()))
    if not rows or not COLUMNS <= set(rows[0]):
        raise InputError(f"CSV phải có cột {sorted(COLUMNS)}")
    valid, revenue, canceled = 0, Decimal("0"), 0
    for row in rows:
        if row["order_status"] == "canceled":
            canceled += 1
            continue
        try:
            revenue += Decimal(row["payment_value"])
        except InvalidOperation as exc:
            raise InputError(f"payment_value không hợp lệ: {row['payment_value']!r}") from exc
        valid += 1
    return valid, revenue.quantize(Decimal("0.01")), canceled, raw


def build(args: argparse.Namespace, day: str, valid: int, revenue: Decimal, canceled: int, raw: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{SENDER[0]} <{SENDER[1]}>"
    msg["To"] = ", ".join(args.to)
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = f"[Olist Shop] Báo cáo đơn hàng {day}"
    msg["Date"] = formatdate(localtime=False, usegmt=True)
    msg["Message-ID"] = make_msgid(domain=DOMAIN)
    msg["Auto-Submitted"] = "auto-generated"
    msg["List-Unsubscribe"] = UNSUBSCRIBE
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    lines = [f"Ngày: {day}", f"Đơn hàng hợp lệ: {valid}", f"Doanh thu (BRL): {revenue}", f"Đơn huỷ: {canceled}"]
    msg.set_content("\n".join(lines) + "\n")
    rows = "".join(f"<li>{escape(line)}</li>" for line in lines)
    msg.add_alternative(f"<html><body><h1>Olist Shop</h1><ul>{rows}</ul></body></html>\n", subtype="html")
    msg.add_attachment(raw.encode("utf-8"), maintype="text", subtype="csv", filename=f"orders-{day}.csv")
    return msg


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        day = date.fromisoformat(args.date).isoformat()
    except ValueError:
        print(f"ngày không hợp lệ: {args.date!r}, cần YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        valid, revenue, canceled, raw = summarize(args.csv)
    except InputError as exc:
        print(f"dữ liệu sai: {exc}", file=sys.stderr)
        return 2
    msg = build(args, day, valid, revenue, canceled, raw)
    try:
        with smtplib.SMTP(args.host, args.port, timeout=10) as smtp:
            smtp.send_message(msg, from_addr=ENVELOPE_FROM, to_addrs=[*args.to, *args.bcc])
    except (OSError, smtplib.SMTPException) as exc:
        print(f"smtp error: {exc}", file=sys.stderr)
        return 3
    print(msg["Message-ID"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
