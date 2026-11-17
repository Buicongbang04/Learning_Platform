"""Biến export CSV của hệ thống cũ (HOPDONG.CSV, DOITAC.CSV) thành tài liệu văn bản UTF-8 cho inbox của quillo."""

import argparse
import csv
import io
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime
from decimal import Decimal
from pathlib import Path

REF = re.compile(r"^[A-Za-z0-9-]+$")


def read_rows(path: Path, encoding: str) -> list[list[str]]:
    text = unicodedata.normalize("NFC", path.read_bytes().decode(encoding, errors="strict"))
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";"))
    return rows[1:]


def iso_day(value: str) -> str:
    return datetime.strptime(value.strip(), "%d/%m/%Y").date().isoformat()


def note(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return value + "\n" if value else ""


def contracts(path: Path) -> dict[str, str]:
    docs = {}
    for row in read_rows(path, "cp1258"):
        if len(row) < 6 or not row[0].strip():
            continue
        ref, customer, kind, signed, amount, remark = (cell.strip() if i < 5 else cell for i, cell in enumerate(row[:6]))
        if not REF.match(ref):
            raise ValueError(f"số hợp đồng lạ: {ref!r}")
        value = int(amount.replace(".", "").replace(" ", ""))
        docs[f"hop-dong/{ref}.txt"] = (
            f"Nguồn: hệ thống hợp đồng\nSố hợp đồng: {ref}\nKhách hàng: {customer}\nLoại hợp đồng: {kind}\n"
            f"Ngày ký: {iso_day(signed)}\nGiá trị: {value} VND\nGhi chú:\n{note(remark)}")
    return docs


def partners(path: Path) -> dict[str, str]:
    docs = {}
    for row in read_rows(path, "cp1252"):
        if len(row) < 5 or not row[0].strip():
            continue
        ref, customer, opened, fee, remark = (cell.strip() if i < 4 else cell for i, cell in enumerate(row[:5]))
        if not REF.match(ref):
            raise ValueError(f"mã hồ sơ lạ: {ref!r}")
        euros = fee.replace(" ", "").replace("\u00a0", "").replace(".", "").replace(",", ".")
        docs[f"doi-tac/{ref}.txt"] = (
            f"Nguồn: văn phòng đối tác\nMã hồ sơ: {ref}\nKhách hàng: {customer}\nNgày mở: {iso_day(opened)}\n"
            f"Phí: {Decimal(euros).quantize(Decimal('0.01'))} EUR\nGhi chú:\n{note(remark)}")
    return docs


def write_atomic(path: Path, text: str) -> None:
    data = text.encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".part")
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.chmod(temp, 0o644)
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="src", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    src, out = Path(args.src), Path(args.out)
    try:
        docs = contracts(src / "HOPDONG.CSV") | partners(src / "DOITAC.CSV")
    except (OSError, UnicodeDecodeError, ValueError, ArithmeticError) as error:
        print(f"không đọc được export: {error}", file=sys.stderr)
        return 1
    for rel, text in sorted(docs.items()):
        write_atomic(out / rel, text)
    print(f"{len(docs)} tài liệu trong {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
