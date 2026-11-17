"""Biến export CSV của hệ thống cũ (HOPDONG.CSV, DOITAC.CSV) thành tài liệu văn bản cho inbox của quillo.

Bản đồng nghiệp viết thử trên máy mình với một tệp export cũ; mới làm HOPDONG.CSV."""

import argparse
import csv
import sys
from pathlib import Path


def contracts(path: Path, out: Path) -> int:
    count = 0
    with path.open(encoding="latin-1", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 6 or row[0] == "Số HĐ":
                continue
            ref, customer, kind, signed, amount, remark = row[:6]
            target = out / "hop-dong" / f"{ref}.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                f"Nguồn: hệ thống hợp đồng\nSố hợp đồng: {ref}\nKhách hàng: {customer}\nLoại hợp đồng: {kind}\n"
                f"Ngày ký: {signed}\nGiá trị: {amount} VND\nGhi chú:\n{remark}\n")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="src", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    count = contracts(Path(args.src) / "HOPDONG.CSV", Path(args.out))
    print(f"{count} tài liệu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
