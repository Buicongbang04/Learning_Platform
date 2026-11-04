"""Ký cả thư mục model bằng khoá EC offline (model-signing), verify fail closed."""

from pathlib import Path


def _inside(path: Path, folder: Path) -> bool:
    return Path(path).resolve().is_relative_to(Path(folder).resolve())


def sign(model_dir: Path, private_key: Path, signature: Path) -> None:
    from model_signing import signing

    if _inside(signature, model_dir):
        raise ValueError("chữ ký phải nằm ngoài thư mục model")
    Path(signature).parent.mkdir(parents=True, exist_ok=True)
    signing.Config().use_elliptic_key_signer(private_key=Path(private_key)).sign(Path(model_dir), Path(signature))


def verify(model_dir: Path, public_key: Path, signature: Path) -> bool:
    try:
        from model_signing import verifying

        verifying.Config().use_elliptic_key_verifier(public_key=Path(public_key)).verify(Path(model_dir), Path(signature))
    except Exception:
        return False
    return True
