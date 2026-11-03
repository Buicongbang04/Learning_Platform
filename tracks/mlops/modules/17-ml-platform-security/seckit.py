"""Tiện ích chung cho test module 17: cặp khoá EC sinh tại chỗ, model mẫu, pickle độc hại đã vô hại hoá.

Quy tắc an toàn của module:

- Payload pickle chỉ ghi một tệp đánh dấu vào thư mục tạm của test, không bao giờ gọi lệnh hệ thống hay mạng.
- Test không bao giờ nạp (unpickle) tệp model, trừ đúng một ca có chủ đích trong bài Intermediate 01 để chứng minh rủi ro,
  và ca đó chạy trong `tmp_path`.
- Quét model chỉ qua `mlopskit.modelscan_run` (container `--network none`, mount chỉ đọc).
"""

import pickle
from pathlib import Path

import numpy as np
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def ec_keypair(folder: Path, name: str = "signer") -> tuple[Path, Path]:
    """Sinh cặp khoá EC P-256 offline, trả `(private.pem, public.pem)` trong `folder`."""
    folder.mkdir(parents=True, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    private = folder / f"{name}.pem"
    public = folder / f"{name}.pub"
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
    private.chmod(0o600)
    public.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                     serialization.PublicFormat.SubjectPublicKeyInfo))
    return private, public


def safetensors_model(folder: Path, seed: int = 0) -> Path:
    """Thư mục model chỉ gồm trọng số safetensors và cấu hình JSON."""
    from safetensors.numpy import save_file

    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    save_file({"coef": rng.normal(size=10), "intercept": np.array([1.5])}, str(folder / "model.safetensors"),
              metadata={"format": "linear"})
    (folder / "config.json").write_text('{"features": 10, "target": "tip_amount"}\n', encoding="utf-8")
    return folder


class _ExecMarker:
    """`__reduce__` trỏ tới `builtins.exec`; đoạn code chỉ ghi chữ `pwned` vào tệp đánh dấu."""

    def __init__(self, marker: Path):
        self.code = f"open({str(marker)!r}, 'w').write('pwned')"

    def __reduce__(self):
        import builtins

        return (builtins.exec, (self.code,))


class _PathMarker:
    """`__reduce__` gọi `pathlib.Path.write_text` ghi tệp đánh dấu; không có tên nào trong danh sách chặn của modelscan."""

    def __init__(self, marker: Path):
        self.marker = Path(marker)

    def __reduce__(self):
        return (Path.write_text, (self.marker, "pwned"))


def marker_pickle(marker: Path) -> bytes:
    """Pickle trông như checkpoint (dict trọng số), nạp vào là chạy `exec` ghi `marker`. modelscan bắt được (CRITICAL)."""
    return pickle.dumps({"coef": [0.1, 0.2, 0.3], "intercept": 1.5, "hook": _ExecMarker(marker)}, protocol=4)


def stealth_pickle(marker: Path) -> bytes:
    """Pickle nạp vào là ghi `marker` qua `pathlib`; modelscan 0.8.8 không bắt (quét theo danh sách chặn)."""
    return pickle.dumps({"coef": [0.1, 0.2, 0.3], "hook": _PathMarker(marker)}, protocol=4)


def plain_pickle() -> bytes:
    """Pickle chỉ có số và list, không tham chiếu hàm nào."""
    return pickle.dumps({"coef": [0.1, 0.2, 0.3], "intercept": 1.5}, protocol=4)
