"""Đưa một bản phát hành model đã ký từ registry về đĩa của node serving."""

import hashlib
import shutil
import uuid
from pathlib import Path

from model_signing import verifying


class Rejected(Exception):
    pass


def _verified(folder: Path, signature: Path, public_key: Path) -> bool:
    try:
        verifying.Config().use_elliptic_key_verifier(public_key=public_key).verify(folder, signature)
    except Exception:
        return False
    return True


def _key(signature: Path) -> str:
    return hashlib.sha256(signature.read_bytes()).hexdigest()[:16]


def stage(bundle: Path, signature: Path, public_key: Path, cache_root: Path) -> Path:
    """Trả thư mục trên node mà serving sẽ nạp model từ đó; nội dung thư mục này đã được verify."""
    bundle, signature, public_key, cache_root = map(Path, (bundle, signature, public_key, cache_root))
    if not _verified(bundle, signature, public_key):
        raise Rejected(f"chữ ký không hợp lệ cho {bundle.name}")
    target = cache_root / _key(signature)
    if target.is_dir():
        if _verified(target, signature, public_key):
            return target
        shutil.rmtree(target)
    cache_root.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f".{target.name}.{uuid.uuid4().hex[:8]}")
    shutil.copytree(bundle, partial)
    if not _verified(partial, signature, public_key):
        shutil.rmtree(partial)
        raise Rejected(f"bản chép của {bundle.name} không khớp chữ ký")
    partial.rename(target)
    return target
