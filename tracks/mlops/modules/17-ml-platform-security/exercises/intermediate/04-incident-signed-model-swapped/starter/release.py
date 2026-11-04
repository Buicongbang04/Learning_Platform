"""Đưa một bản phát hành model đã ký từ registry về đĩa của node serving."""

import hashlib
import shutil
import uuid
from pathlib import Path

from model_signing import verifying


class Rejected(Exception):
    pass


def _check(bundle: Path, signature: Path, public_key: Path) -> None:
    try:
        verifying.Config().use_elliptic_key_verifier(public_key=public_key).verify(bundle, signature)
    except Exception as exc:
        raise Rejected(f"chữ ký không hợp lệ cho {bundle.name}") from exc


def _key(signature: Path) -> str:
    return hashlib.sha256(signature.read_bytes()).hexdigest()[:16]


def _copy(bundle: Path, target: Path) -> None:
    partial = target.with_name(f".{target.name}.{uuid.uuid4().hex[:8]}")
    shutil.copytree(bundle, partial)
    partial.rename(target)


def stage(bundle: Path, signature: Path, public_key: Path, cache_root: Path) -> Path:
    """Trả thư mục trên node mà serving sẽ nạp model từ đó."""
    bundle, signature, public_key, cache_root = map(Path, (bundle, signature, public_key, cache_root))
    _check(bundle, signature, public_key)
    target = cache_root / _key(signature)
    if not target.is_dir():
        cache_root.mkdir(parents=True, exist_ok=True)
        _copy(bundle, target)
    return target
