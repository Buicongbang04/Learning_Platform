import json
import sys
from pathlib import Path


def inspect_image(path: Path) -> dict:
    """{"tags", "platform", "config", "layers", "size"} của tarball `docker save` (xem README)."""
    raise NotImplementedError("TODO: đọc manifest.json, config blob, danh sách layer")


def check_image(path: Path, platform: str) -> list[str]:
    """Danh sách vấn đề trước khi mang tarball tới khách có nền tảng `platform` (vd. linux/amd64); rỗng là đạt."""
    raise NotImplementedError("TODO: tar đọc được, đủ blob, đúng digest, đúng nền tảng, có tag")


if __name__ == "__main__":
    tar, want = Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "linux/amd64"
    print(json.dumps({"image": inspect_image(tar), "problems": check_image(tar, want)}, indent=2, ensure_ascii=False))
