#!/usr/bin/env python3
"""fieldsync: đồng bộ bộ tài liệu kỹ thuật xuống máy ở xưởng.

  fieldsync build-index --assets DIR --out FILE [--max-open N]
      Chụp một ảnh nhất quán của DIR: mở mọi tệp, giữ khoá đọc (flock LOCK_SH) trên tất cả cùng lúc để không tệp nào
      bị ghi dở trong lúc băm, rồi ghi FILE (JSON: version, count, files{đường dẫn tương đối: sha256}).
      --max-open N: giữ tối đa N tệp mở cùng lúc (băm theo từng đợt N tệp; ảnh chỉ nhất quán trong từng đợt).
      Mặc định giữ mọi tệp mở. Mỗi tệp mở tốn một file descriptor; tiến trình cần `ulimit -n` lớn hơn N + 16.
  fieldsync --version
"""

import fcntl
import hashlib
import json
import os
import resource
import sys
from pathlib import Path

VERSION = "1.4.0"


def raise_nofile() -> None:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if hard != resource.RLIM_INFINITY and soft < hard:
        resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))


def snapshot(paths: list[Path], root: Path) -> dict[str, str]:
    handles = []
    try:
        for path in paths:
            handle = open(path, "rb")
            handles.append(handle)
            fcntl.flock(handle, fcntl.LOCK_SH)
        result = {}
        for path, handle in zip(paths, handles):
            result[path.relative_to(root).as_posix()] = hashlib.sha256(handle.read()).hexdigest()
        return result
    finally:
        for handle in handles:
            handle.close()


def build_index(assets: Path, out: Path, max_open: int | None) -> int:
    raise_nofile()
    paths = sorted(p for p in assets.rglob("*") if p.is_file())
    batch = max_open or len(paths) or 1
    files: dict[str, str] = {}
    for start in range(0, len(paths), batch):
        files.update(snapshot(paths[start:start + batch], assets))
    part = out.with_name(out.name + ".part")
    part.write_text(json.dumps({"version": VERSION, "count": len(files), "files": files}, indent=1), encoding="utf-8")
    os.replace(part, out)
    print(f"fieldsync: đã lập chỉ mục {len(files)} tệp vào {out}", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--version"]:
        print(f"fieldsync {VERSION}")
        return 0
    if argv[:1] != ["build-index"]:
        print(__doc__, file=sys.stderr)
        return 2
    args = argv[1:]
    options: dict[str, str] = {}
    while args:
        key = args.pop(0)
        if key not in ("--assets", "--out", "--max-open") or not args:
            print(__doc__, file=sys.stderr)
            return 2
        options[key] = args.pop(0)
    if "--assets" not in options or "--out" not in options:
        print(__doc__, file=sys.stderr)
        return 2
    max_open = int(options["--max-open"]) if "--max-open" in options else None
    if max_open is not None and max_open < 1:
        print("fieldsync: --max-open phải ≥ 1", file=sys.stderr)
        return 2
    return build_index(Path(options["--assets"]), Path(options["--out"]), max_open)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
