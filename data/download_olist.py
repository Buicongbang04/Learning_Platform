"""Tải bộ Brazilian E-Commerce Public Dataset by Olist thật từ Kaggle (TUỲ CHỌN).

Không bắt buộc: mọi bài tập và capstone chạy được với dữ liệu giả từ data/generate_olist.py
(cùng tên tệp, cùng cột). Dùng bộ thật khi muốn số liệu "đời thực" cho portfolio.

Chuẩn bị Kaggle API token (một lần):
  1. Đăng nhập https://www.kaggle.com -> Settings -> API -> "Generate New Token".
     Kaggle hiện token dạng KGAT_... Ghi vào setup/.env (đã nằm trong .gitignore):
         KAGGLE_API_TOKEN=KGAT_...
     Hoặc đặt biến môi trường KAGGLE_API_TOKEN.
  2. Token kiểu cũ vẫn dùng được: tệp ~/.kaggle/kaggle.json chứa {"username": "...", "key": "..."}
     (chmod 600), hoặc biến môi trường KAGGLE_USERNAME và KAGGLE_KEY.
  3. Mở trang dataset một lần trên web và bấm chấp nhận điều khoản nếu Kaggle yêu cầu:
         https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Chạy:
    uv run python data/download_olist.py                 # ghi vào data/raw/ (ghi đè dữ liệu giả)
    uv run python data/download_olist.py --out data/raw_real

Script tải qua kagglehub (client chính thức của Kaggle, cache ở ~/.cache/kagglehub).
Nếu đã cài Kaggle CLI, lệnh tương đương:
    kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import kagglehub

DATASET = "olistbr/brazilian-ecommerce"
DEFAULT_OUT = Path(__file__).resolve().parent / "raw"
EXPECTED = [
    "olist_customers_dataset.csv", "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv", "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv", "olist_orders_dataset.csv",
    "olist_products_dataset.csv", "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]


ENV_FILE = Path(__file__).resolve().parent.parent / "setup" / ".env"


def _from_env_file(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.strip().partition("=")
        if sep and name.strip() == key:
            return value.strip().strip('"').strip("'") or None
    return None


def ensure_kaggle_credentials(env_file: Path = ENV_FILE) -> bool:
    """Đưa KAGGLE_API_TOKEN từ setup/.env vào môi trường (cho kagglehub); True nếu có token nào dùng được."""
    if not os.environ.get("KAGGLE_API_TOKEN"):
        token = _from_env_file(env_file, "KAGGLE_API_TOKEN")
        if token:
            os.environ["KAGGLE_API_TOKEN"] = token
    if os.environ.get("KAGGLE_API_TOKEN"):
        return True
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    return (Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json").exists()


def kaggle_download(ref: str, out: Path, files: list[str]) -> list[Path]:
    """Tải dataset Kaggle qua kagglehub (client chính thức, có cache) rồi chép đúng các tệp cần vào out."""
    cache = Path(kagglehub.dataset_download(ref))
    found = {p.name: p for p in cache.rglob("*") if p.is_file()}
    missing = [name for name in files if name not in found]
    if missing:
        raise SystemExit(f"Dataset {ref} thiếu {missing}. Có: {sorted(found)}")
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name in files:
        target = out / name
        shutil.copyfile(found[name], target)
        written.append(target)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Tải bộ Olist thật từ Kaggle.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not ensure_kaggle_credentials():
        sys.exit(
            "Chưa có Kaggle token (KAGGLE_API_TOKEN trong setup/.env). Xem hướng dẫn ở đầu tệp data/download_olist.py.\n"
            "Không có token vẫn học được: uv run python data/generate_olist.py"
        )

    print(f"Đang tải {DATASET} (~45 MB)...")
    for path in kaggle_download(DATASET, args.out, EXPECTED):
        print(f"  {path}")

    print(f"Xong: 9 tệp CSV trong {args.out.resolve()}")


if __name__ == "__main__":
    main()
