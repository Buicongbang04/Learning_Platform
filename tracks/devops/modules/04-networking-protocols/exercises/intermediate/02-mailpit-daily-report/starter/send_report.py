import argparse
import csv
import smtplib
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

DOMAIN = "olist-shop.com.br"


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
    """Trả (số đơn hợp lệ, doanh thu làm tròn 2 chữ số, số đơn huỷ, nội dung CSV gốc)."""
    # TODO
    raise NotImplementedError


def build(args: argparse.Namespace, day: str, valid: int, revenue: Decimal, canceled: int, raw: str) -> EmailMessage:
    # TODO: header theo bảng trong README, phần text + HTML, đính kèm CSV
    raise NotImplementedError


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    # TODO: kiểm ngày và CSV (lỗi → exit 2), gửi qua SMTP với envelope sender riêng (lỗi → exit 3), in Message-ID
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
