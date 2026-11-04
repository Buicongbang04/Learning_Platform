import io
import json
import tarfile
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
AMD64 = ex.fixtures / "hello-amd64.tar"
ARM64 = ex.fixtures / "hello-arm64.tar"
TAG = "hello-world:linux-pinned"
AMD64_LAYER = "4f55086f7dd096d48b0e49be066971a8ed996521c2e190aa21b2435a847198b4"
AMD64_CONFIG = "e2ac70e7319a02c5a477f5825259bd118b94e8b02c279c67afa63adab6d8685b"
ARM64_LAYER = "58dee6a49ef1c01bb8a00180d70f55b3527c8e7326a05b3c5135c4ff60cfb6d6"
PREFIXES = ("không đọc được", "thiếu blob", "sai digest", "sai nền tảng", "không có tag", "cần đúng 1 image")


def lib():
    return ex.module("image_tar.py")


def rewrite(source: Path, target: Path, change) -> Path:
    """Chép tar `source` sang `target`, `change(name, data)` trả bytes mới hoặc None để bỏ tệp."""
    with tarfile.open(source) as src, tarfile.open(target, "w") as dst:
        for member in src.getmembers():
            data = src.extractfile(member).read() if member.isfile() else None
            if data is not None:
                data = change(member.name, data)
                if data is None:
                    continue
                member.size = len(data)
                dst.addfile(member, io.BytesIO(data))
            else:
                dst.addfile(member)
    return target


def test_inspect_amd64():
    info = lib().inspect_image(AMD64)
    assert info == {
        "tags": [TAG],
        "platform": "linux/amd64",
        "config": f"sha256:{AMD64_CONFIG}",
        "layers": [f"sha256:{AMD64_LAYER}"],
        "size": 2415,
    }


def test_inspect_arm64():
    info = lib().inspect_image(ARM64)
    assert info["platform"] == "linux/arm64"
    assert info["layers"] == [f"sha256:{ARM64_LAYER}"]
    assert info["tags"] == [TAG]


def test_check_clean_tarball():
    assert lib().check_image(AMD64, "linux/amd64") == []


def test_check_wrong_platform():
    assert lib().check_image(ARM64, "linux/amd64") == ["sai nền tảng: linux/arm64, cần linux/amd64"]
    assert lib().check_image(AMD64, "linux/arm64") == ["sai nền tảng: linux/amd64, cần linux/arm64"]


def test_check_tampered_layer(tmp_path):
    def flip(name, data):
        return data[:-1] + bytes([data[-1] ^ 1]) if name.endswith(AMD64_LAYER) else data

    bad = rewrite(AMD64, tmp_path / "tampered.tar", flip)
    assert lib().check_image(bad, "linux/amd64") == [f"sai digest: blobs/sha256/{AMD64_LAYER}"]


def test_check_missing_layer(tmp_path):
    bad = rewrite(AMD64, tmp_path / "missing.tar", lambda name, data: None if name.endswith(AMD64_LAYER) else data)
    assert lib().check_image(bad, "linux/amd64") == [f"thiếu blob: blobs/sha256/{AMD64_LAYER}"]


def test_check_untagged(tmp_path):
    def untag(name, data):
        if name != "manifest.json":
            return data
        manifest = json.loads(data)
        manifest[0]["RepoTags"] = None
        return json.dumps(manifest).encode()

    bad = rewrite(AMD64, tmp_path / "untagged.tar", untag)
    assert lib().check_image(bad, "linux/amd64") == ["không có tag"]
    assert lib().inspect_image(bad)["tags"] == []


def cut_points() -> dict[str, int]:
    with tarfile.open(AMD64) as tar:
        members = {m.name: m for m in tar.getmembers()}
    layer = members[f"blobs/sha256/{AMD64_LAYER}"]
    manifest = members["manifest.json"]
    return {
        "giữa layer": layer.offset_data + layer.size // 2,
        "trước manifest.json": manifest.offset,
        "giữa manifest.json": manifest.offset_data + manifest.size // 2,
    }


@pytest.mark.parametrize("where", ["giữa layer", "trước manifest.json", "giữa manifest.json"])
def test_check_truncated(tmp_path, where):
    bad = tmp_path / "cut.tar"
    bad.write_bytes(AMD64.read_bytes()[: cut_points()[where]])
    problems = lib().check_image(bad, "linux/amd64")
    assert problems, f"Tar bị cắt ({where}) mà check_image không báo gì"
    assert all(p.startswith(PREFIXES) for p in problems), problems


def test_check_not_a_tar(tmp_path):
    bad = tmp_path / "image.tar"
    bad.write_text("<html>403 Forbidden</html>\n")
    problems = lib().check_image(bad, "linux/amd64")
    assert len(problems) == 1 and problems[0].startswith("không đọc được"), problems
