"""Tải bộ Brazilian E-Commerce Public Dataset by Olist thật từ Kaggle (TUỲ CHỌN).

Không bắt buộc: mọi bài tập và capstone chạy được với dữ liệu giả từ data/generate_olist.py
(cùng tên tệp, cùng cột). Dùng bộ thật khi muốn số liệu "đời thực" cho portfolio.

Chuẩn bị Kaggle API token (một lần):
  1. Đăng nhập https://www.kaggle.com -> Settings -> API -> "Create New Token".
     Trình duyệt tải về tệp kaggle.json chứa {"username": "...", "key": "..."}.
  2. Đặt tệp vào ~/.kaggle/kaggle.json và khoá quyền:
         mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json
     Hoặc đặt biến môi trường KAGGLE_USERNAME và KAGGLE_KEY.
  3. Mở trang dataset một lần trên web và bấm chấp nhận điều khoản nếu Kaggle yêu cầu:
         https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Chạy:
    uv run python data/download_olist.py                 # ghi vào data/raw/ (ghi đè dữ liệu giả)
    uv run python data/download_olist.py --out data/raw_real

Script gọi thẳng REST API của Kaggle bằng requests (không cần cài gói `kaggle`).
Nếu đã cài Kaggle CLI, lệnh tương đương:
    kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile
from pathlib import Path

import requests

DATASET = "olistbr/brazilian-ecommerce"
URL = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET}"
DEFAULT_OUT = Path(__file__).resolve().parent / "raw"
EXPECTED = [
    "olist_customers_dataset.csv", "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv", "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv", "olist_orders_dataset.csv",
    "olist_products_dataset.csv", "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]


def credentials() -> tuple[str, str] | None:
    user, key = os.environ.get("KAGGLE_USERNAME"), os.environ.get("KAGGLE_KEY")
    if user and key:
        return user, key
    path = Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json"
    if path.exists():
        data = json.loads(path.read_text())
        return data["username"], data["key"]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Tải bộ Olist thật từ Kaggle.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    creds = credentials()
    if not creds:
        sys.exit(
            "Chưa có Kaggle token. Xem hướng dẫn ở đầu tệp data/download_olist.py.\n"
            "Không có token vẫn học được: uv run python data/generate_olist.py"
        )

    print(f"Đang tải {DATASET} (~45 MB)...")
    resp = requests.get(URL, auth=creds, timeout=300)
    if resp.status_code in (401, 403):
        sys.exit(f"Kaggle từ chối ({resp.status_code}). Kiểm tra token và đã chấp nhận điều khoản dataset chưa.")
    resp.raise_for_status()

    args.out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in zf.namelist():
            target = args.out / Path(name).name  # bỏ thư mục con, chặn path traversal
            if not target.name.endswith(".csv"):
                continue
            target.write_bytes(zf.read(name))
            print(f"  {target}")

    missing = [n for n in EXPECTED if not (args.out / n).exists()]
    if missing:
        print(f"Cảnh báo: thiếu {missing}", file=sys.stderr)
    else:
        print(f"Xong: 9 tệp CSV trong {args.out.resolve()}")


if __name__ == "__main__":
    main()
