"""SBOM CycloneDX cho môi trường serving bằng cyclonedx-py, và các phép kiểm trên SBOM."""

from pathlib import Path


def generate(source: Path, out: Path, kind: str = "requirements", timeout: int = 300) -> dict:
    # TODO 1: chạy cyclonedx-py (requirements hoặc environment), CycloneDX 1.6 JSON, ghi ra out, trả dict
    raise NotImplementedError


def packages(sbom: dict) -> dict[str, str | None]:
    # TODO 2: {tên chuẩn hoá: version hoặc None}
    raise NotImplementedError


def unpinned(sbom: dict) -> list[str]:
    # TODO 3
    raise NotImplementedError


def diff(old: dict, new: dict) -> dict:
    # TODO 4: {"added": [...], "removed": [...], "changed": {tên: [cũ, mới]}}
    raise NotImplementedError


def check(sbom: dict, required: dict[str, str]) -> list[str]:
    # TODO 5: unpinned:<tên>, missing:<tên>, mismatch:<tên>, đã sắp xếp
    raise NotImplementedError
