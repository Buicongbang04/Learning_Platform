"""Dựng bundle beacon-<version>.tar ngay trong máy (Python 3.8+), in manifest ra stdout.

    python3 make_bundle.py <version> <weights_mib> <out.tar> [--broken-app] [--broken-unit] [--bad-sha]

`models/weights.bin` là dữ liệu giả ngẫu nhiên, xác định theo version (openssl aes-128-ctr), sinh dạng luồng nên không
cần chỗ trống ngoài chính tệp tar. Manifest nằm đầu bundle.
"""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

KIT = Path(__file__).resolve().parent
CHUNK = 1 << 20
BROKEN_APP = 'import sys\nsys.exit("beacon: không đọc được cấu hình model")\n'


class Weights:
    def __init__(self, version: str, size: int) -> None:
        key = hashlib.sha256(version.encode()).hexdigest()[:32]
        self.proc = subprocess.Popen(
            ["openssl", "enc", "-aes-128-ctr", "-nosalt", "-K", key, "-iv", "0" * 32, "-in", "/dev/zero"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.left = size

    def read(self, n: int = -1) -> bytes:
        n = self.left if n is None or n < 0 else min(n, self.left)
        data = self.proc.stdout.read(n) if n else b""
        self.left -= len(data)
        if not self.left:
            self.close_stream()
        return data

    def close_stream(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()


def weights_sha(version: str, size: int) -> str:
    stream, sha = Weights(version, size), hashlib.sha256()
    while True:
        chunk = stream.read(CHUNK)
        if not chunk:
            return sha.hexdigest()
        sha.update(chunk)


def add(tar: tarfile.TarFile, name: str, data, size: int, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name)
    info.size, info.mode, info.mtime = size, mode, 1700000000
    tar.addfile(info, data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("weights_mib", type=int)
    parser.add_argument("out")
    parser.add_argument("--broken-app", action="store_true")
    parser.add_argument("--broken-unit", action="store_true")
    parser.add_argument("--bad-sha", action="store_true")
    args = parser.parse_args()
    app = BROKEN_APP.encode() if args.broken_app else (KIT / "beacon.py").read_bytes()
    small = {
        "app/beacon.py": app,
        "app/VERSION": (args.version + "\n").encode(),
        "config/beacon.env": (KIT / "beacon.env").read_bytes(),
        "systemd/beacon.service": (KIT / "beacon.service").read_bytes(),
    }
    if args.broken_unit:
        unit = small["systemd/beacon.service"].decode()
        small["systemd/beacon.service"] = "\n".join(
            line for line in unit.splitlines() if not line.startswith("ExecStart=")).encode() + b"\n"
    size = args.weights_mib * CHUNK
    files = {name: {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)} for name, data in small.items()}
    files["models/weights.bin"] = {"sha256": weights_sha(args.version, size), "size": size}
    if args.bad_sha:
        files["app/beacon.py"]["sha256"] = hashlib.sha256(b"tampered").hexdigest()
    manifest = {"name": "beacon", "version": args.version, "files": dict(sorted(files.items()))}
    text = (json.dumps(manifest, indent=2) + "\n").encode()
    root = "beacon-" + args.version
    part = args.out + ".part"
    with tarfile.open(part, "w", format=tarfile.PAX_FORMAT) as tar:
        add(tar, root + "/manifest.json", io.BytesIO(text), len(text))
        for name, data in sorted(small.items()):
            add(tar, root + "/" + name, io.BytesIO(data), len(data))
        stream = Weights(args.version, size)
        add(tar, root + "/models/weights.bin", stream, size)
        stream.close_stream()
    Path(part).rename(args.out)
    print(text.decode(), end="")


if __name__ == "__main__":
    main()
