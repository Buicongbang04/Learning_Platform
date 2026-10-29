"""Tải các bộ dữ liệu thật dùng trong track AI & Data Scientist.

Mỗi bộ ghi vào data/raw/<tên>/ (không commit). Test của bài tập tự skip khi bộ chưa được tải.

Bộ trên Kaggle cần token: KAGGLE_API_TOKEN=KGAT_... trong setup/.env (cách lấy token xem đầu tệp
data/download_olist.py). Bộ tải từ URL công khai không cần token.

Chạy:
    uv run python data/download_dataset.py --list            # liệt kê các bộ
    uv run python data/download_dataset.py cookie-cats       # ghi vào data/raw/cookie-cats/
    uv run python data/download_dataset.py hillstrom --out /tmp/hillstrom

Bộ Olist thật dùng script riêng (ghi thẳng vào data/raw/): uv run python data/download_olist.py
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_olist import ENV_FILE, ensure_kaggle_credentials, kaggle_download  # noqa: E402

RAW = Path(__file__).resolve().parent / "raw"


@dataclass(frozen=True)
class Dataset:
    source: Literal["kaggle", "url"]
    ref: str            # "owner/slug" trên Kaggle, hoặc URL tải trực tiếp
    files: list[str]    # tệp cần giữ (bộ url: đúng một tệp, là tên lưu xuống)
    license: str
    homepage: str
    about: str = ""


DATASETS: dict[str, Dataset] = {
    "cookie-cats": Dataset(
        "kaggle", "yufengsui/mobile-games-ab-testing", ["cookie_cats.csv"],
        license="Không ghi rõ trên Kaggle (dữ liệu công khai của Tactile Games qua DataCamp)",
        homepage="https://www.kaggle.com/datasets/yufengsui/mobile-games-ab-testing",
        about="A/B test vị trí gate (level 30 vs 40) của game Cookie Cats, ~90k người chơi",
    ),
    "ab-data": Dataset(
        "kaggle", "zhangluyuan/ab-testing", ["ab_data.csv"],
        license="Không ghi rõ trên Kaggle (dữ liệu khoá Udacity A/B Testing)",
        homepage="https://www.kaggle.com/datasets/zhangluyuan/ab-testing",
        about="A/B test landing page, ~290k phiên, có cả dòng gán nhóm sai",
    ),
    "hillstrom": Dataset(
        "url",
        "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv",
        ["hillstrom.csv"],
        license="Kevin Hillstrom công bố cho MineThatData E-Mail Analytics Challenge (2008), dùng tự do cho học tập",
        homepage="https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html",
        about="Thí nghiệm email ngẫu nhiên 3 nhánh, 64k khách: visit, conversion, spend",
    ),
}


def _no_token() -> SystemExit:
    return SystemExit(
        "Chưa có Kaggle token. Thêm KAGGLE_API_TOKEN=KGAT_... vào setup/.env "
        "(hướng dẫn ở đầu tệp data/download_olist.py)."
    )


def download(name: str, out: Path) -> list[Path]:
    ds = DATASETS[name]
    if ds.source == "url":
        out.mkdir(parents=True, exist_ok=True)
        resp = requests.get(ds.ref, timeout=300)
        resp.raise_for_status()
        target = out / ds.files[0]
        target.write_bytes(resp.content)
        return [target]

    if not ensure_kaggle_credentials(env_file=ENV_FILE):
        raise _no_token()
    return kaggle_download(ds.ref, out, ds.files)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Tải bộ dữ liệu thật cho track AI & Data Scientist.")
    parser.add_argument("name", nargs="?", choices=sorted(DATASETS))
    parser.add_argument("--out", type=Path, help="mặc định data/raw/<tên>/")
    parser.add_argument("--list", action="store_true", help="liệt kê các bộ")
    args = parser.parse_args(argv)

    if args.list or not args.name:
        for key, ds in DATASETS.items():
            print(f"{key:12} {ds.about}\n{'':12} {ds.homepage}")
        return
    for path in download(args.name, args.out or RAW / args.name):
        print(f"  {path}")


if __name__ == "__main__":
    main()
