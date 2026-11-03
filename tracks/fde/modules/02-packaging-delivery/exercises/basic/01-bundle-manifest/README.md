---
title: Manifest sha256 cho bundle
level: basic
services: []
files:
  - path: starter/manifest.py
    note: 2 hàm TODO; CLI make/verify đã có sẵn
  - path: tests/test_manifest.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/basic/01-bundle-manifest -q
---

## Mục tiêu

Bundle đi qua USB, cổng truyền tệp của khách, máy quét virus, đôi khi qua tay ba người. Trước khi cài, bạn (và IT khách)
phải trả lời được "đây có đúng là thứ đã đóng gói không" bằng một lệnh, không bằng niềm tin. Bài này viết phần lõi mà
installer nào của bạn cũng sẽ gọi: tạo manifest sha256 lúc đóng gói và đối chiếu lúc cài.

## Đề bài

Viết hai hàm trong `starter/manifest.py`:

**`make_manifest(root) -> dict`** trả về:

```json
{"files": {"app/VERSION": {"sha256": "<64 ký tự hex>", "size": 6}, "models/weights.bin": {"sha256": "...", "size": 300000}}}
```

- Đúng một khoá `files`. Khoá con là đường dẫn **tương đối** so với `root`, dạng POSIX (`/`), sắp xếp tăng dần.
- Liệt kê mọi tệp thường ở mọi độ sâu, kể cả tệp rỗng; bỏ qua thư mục (kể cả thư mục rỗng) và bỏ `manifest.json` ở
  ngay `root` (manifest không tự băm chính nó).
- Gặp symlink (hay tệp đặc biệt) trong cây thì `raise ValueError`: bundle giao cho khách không chứa link trỏ ra ngoài.
- Tệp model có thể vài GB: đọc và băm **theo khối**, không nạp cả tệp vào RAM (test đo RAM đỉnh khi băm tệp 40 MiB,
  phải dưới 8 MiB).

**`verify_manifest(root, manifest) -> list[str]`** trả danh sách vấn đề (rỗng = nguyên vẹn, thứ tự không quan trọng),
mỗi vấn đề đúng một trong các dạng:

| Dạng | Khi nào |
| --- | --- |
| `thiếu: <đường dẫn>` | Có trong manifest, không có trong `root` |
| `thừa: <đường dẫn>` | Có trong `root` (trừ `manifest.json` ở gốc), không có trong manifest |
| `sai sha256: <đường dẫn>` | Có cả hai nhưng nội dung khác (kể cả bị cắt cụt), hoặc trong `root` nó là symlink |
| `đường dẫn không an toàn: <đường dẫn>` | Khoá trong manifest là đường dẫn tuyệt đối hoặc có `..`; **không** được đọc tệp đó |

`python manifest.py make <thư mục>` / `verify <thư mục>` đã viết sẵn để bạn thử tay.

## Tiêu chí đạt

- `test_make_manifest_lists_every_file`, `test_manifest_json_is_not_listed`: đúng định dạng, đủ tệp, sắp xếp, bỏ
  `manifest.json` ở gốc, thư mục rỗng không xuất hiện.
- `test_symlink_rejected`: symlink trong cây ⇒ `ValueError`.
- `test_hashing_streams_large_files`: RAM đỉnh (đo bằng `tracemalloc`) dưới 8 MiB khi băm tệp 40 MiB.
- `test_verify_*`: bundle sạch ⇒ `[]`; xoá một tệp, thêm một tệp, lật một byte, sửa một tệp nhỏ, cắt cụt, đổi tệp thành
  symlink, chèn đường dẫn `../…` và đường dẫn tuyệt đối vào manifest ⇒ đúng danh sách vấn đề như bảng trên.

## Gợi ý

### Gợi ý 1

`os.walk` liệt kê symlink tới thư mục trong danh sách thư mục, không phải danh sách tệp. Kiểm loại bằng `lstat`, không
bằng `is_file()` (hàm này đi theo link).

### Gợi ý 2

Python 3.11+ có `hashlib.file_digest`; tự đọc theo khối 1 MiB trong vòng lặp cũng được.

### Gợi ý 3

`PurePosixPath(name).parts` cho biết có `..` hay không mà không đụng tới đĩa. Kiểm tra trước khi ghép với `root`.
