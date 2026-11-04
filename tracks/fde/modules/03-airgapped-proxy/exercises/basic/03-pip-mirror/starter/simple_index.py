from pathlib import Path


def normalize(name: str) -> str:
    raise NotImplementedError("TODO 1: chuẩn hoá tên project theo PEP 503")


def build_index(dist_dir: Path, out_dir: Path) -> dict[str, list[str]]:
    raise NotImplementedError("TODO 2: dựng mirror kiểu simple index từ thư mục wheel/sdist")
