"""Chuyển Penn-Fudan sang định dạng dataset của ultralytics YOLO (detect hoặc segment).

Định dạng YOLO: mỗi ảnh `images/<split>/<tên>.png` có một tệp nhãn `labels/<split>/<tên>.txt`, mỗi dòng
một vật thể, mọi toạ độ chia cho kích thước ảnh (về [0, 1]):
    detect:   "<class> <cx> <cy> <w> <h>"
    segment:  "<class> <x1> <y1> <x2> <y2> ..."   (đa giác viền của mask, ít nhất 3 đỉnh)
Một tệp data.yaml trỏ tới hai thư mục ảnh và khai báo tên lớp. Penn-Fudan chỉ có một lớp: 0 = person.

Chạy:  uv run python prepare_data.py --out <thư mục> [--task segment]
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def mask_to_yolo_lines(mask: np.ndarray) -> list[str]:
    """mask (H, W) số nguyên (0 nền, k > 0 người thứ k) → một dòng "0 cx cy w h" cho mỗi người, theo id tăng dần.

    Hộp theo quy ước cạnh pixel (pixel c chiếm [c, c+1)), chia cho W (trục x) và H (trục y), 6 chữ số thập phân.
    """
    # TODO
    raise NotImplementedError


def mask_to_polygon_lines(mask: np.ndarray) -> list[str]:
    """Như mask_to_yolo_lines nhưng cho task segment: "0 x1 y1 x2 y2 ..." là viền ngoài lớn nhất của mỗi người
    (cv2.findContours), toạ độ chia W, H, 6 chữ số thập phân. Bỏ người có viền dưới 3 đỉnh."""
    # TODO
    raise NotImplementedError


def split_names(names: list[str], val_frac: float, seed: int) -> tuple[list[str], list[str]]:
    """Chia tên ảnh thành (train, val), val có round(len * val_frac) ảnh, chọn ngẫu nhiên bằng random.Random(seed)
    trên danh sách đã sắp. Hai danh sách trả về đều đã sắp, không giao nhau, cùng seed cho cùng kết quả."""
    # TODO
    raise NotImplementedError


def write_yolo_dataset(root: Path, out: Path, val_frac: float = 0.2, seed: int = 0, task: str = "detect") -> Path:
    """root = .../PennFudanPed (có PNGImages/, PedMasks/). Ghi out/images/{train,val}/*.png (symlink tới ảnh gốc),
    out/labels/{train,val}/*.txt và out/data.yaml; trả đường dẫn data.yaml.

    data.yaml gồm `path: <out tuyệt đối>`, `train: images/train`, `val: images/val`, `names: {0: person}`.
    """
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    repo = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
    ap.add_argument("--root", type=Path, default=repo / "data/raw/penn-fudan/PennFudanPed")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--task", choices=["detect", "segment"], default="detect")
    ap.add_argument("--val-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    print(write_yolo_dataset(args.root, args.out, args.val_frac, args.seed, args.task))
