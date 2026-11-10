"""Ký model bằng model-signing (khoá EC, offline), verify fail closed, và cổng deploy gộp verify + quét."""

from pathlib import Path


def sign(model_dir: Path, private_key: Path, signature: Path) -> None:
    # TODO 1: ký cả thư mục model bằng khoá EC; từ chối khi chữ ký nằm trong thư mục model
    raise NotImplementedError


def verify(model_dir: Path, public_key: Path, signature: Path) -> bool:
    # TODO 2: True chỉ khi chữ ký hợp lệ với đúng khoá công khai này và nội dung chưa đổi; mọi lỗi khác là False
    raise NotImplementedError


def deploy_gate(model_dir: Path, signature: Path, public_key: Path, scan) -> dict:
    # TODO 3: {"allowed": bool, "reasons": [...]} với "signature", "scan" theo thứ tự này
    raise NotImplementedError
