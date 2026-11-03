"""Ký model bằng model-signing (khoá EC, offline), verify fail closed, và cổng deploy gộp verify + quét."""

import json
from pathlib import Path

from model_signing import signing, verifying


def _inside(path: Path, folder: Path) -> bool:
    return Path(path).resolve().is_relative_to(Path(folder).resolve())


def sign(model_dir: Path, private_key: Path, signature: Path) -> None:
    if _inside(signature, model_dir):
        raise ValueError("chữ ký phải nằm ngoài thư mục model")
    signing.Config().use_elliptic_key_signer(private_key=Path(private_key)).sign(Path(model_dir), Path(signature))


def verify(model_dir: Path, public_key: Path, signature: Path) -> bool:
    try:
        verifier = verifying.Config().use_elliptic_key_verifier(public_key=Path(public_key))
        verifier.verify(Path(model_dir), Path(signature))
    except Exception:
        return False
    return True


def scan_ok(result) -> bool:
    try:
        report = json.loads(result.stdout)
    except (TypeError, ValueError):
        return False
    if not isinstance(report, dict) or report.get("errors"):
        return False
    return result.returncode in (0, 3) and not report.get("issues")


def deploy_gate(model_dir: Path, signature: Path, public_key: Path, scan) -> dict:
    reasons = []
    if not verify(model_dir, public_key, signature):
        reasons.append("signature")
    if not scan_ok(scan(Path(model_dir))):
        reasons.append("scan")
    return {"allowed": not reasons, "reasons": reasons}
