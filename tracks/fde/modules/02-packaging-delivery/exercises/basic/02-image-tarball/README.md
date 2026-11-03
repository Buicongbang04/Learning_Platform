---
title: Soi image tarball trước khi mang đi
level: basic
services: []
files:
  - path: starter/image_tar.py
    note: 2 hàm TODO
  - path: tests/fixtures/hello-amd64.tar
    note: "docker save của hello-world (linux/amd64), không sửa"
  - path: tests/fixtures/hello-arm64.tar
    note: "docker save của hello-world (linux/arm64), không sửa"
  - path: tests/test_image_tar.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/basic/02-image-tarball -q
---

## Mục tiêu

Ở máy không ra internet, `docker load` là đường duy nhất đưa image vào. Phát hiện tarball hỏng hay **sai kiến trúc** lúc
đã ngồi trong phòng máy của khách nghĩa là mất một chuyến đi. Bài này viết bước kiểm tra chạy trên laptop của bạn, ngay
sau `docker save`, không cần Docker: đọc thẳng cấu trúc tar.

## Đề bài

Hai tệp trong `tests/fixtures/` là output thật của `docker save` (Docker 29, image store containerd) cho image
`hello-world` ghim digest `sha256:c567b231f65614688711a75f31518a064258a51d442117a3e771a3a8fdba78ef`, tag lại thành
`hello-world:linux-pinned`, một bản `linux/amd64`, một bản `linux/arm64`. Mở bằng `tar -tvf` để xem: có `manifest.json`
(định dạng docker-archive: danh sách, mỗi phần tử có `Config`, `RepoTags`, `Layers`), `index.json` + `oci-layout` (OCI
layout), và blob trong `blobs/sha256/<hex>`, tên blob chính là sha256 nội dung của nó.

Viết trong `starter/image_tar.py`:

**`inspect_image(path) -> dict`**, đọc phần tử đầu của `manifest.json`:

| Khoá | Giá trị |
| --- | --- |
| `tags` | `RepoTags` (danh sách; `null` ⇒ `[]`) |
| `platform` | `"<os>/<architecture>"` lấy từ **config blob** (bỏ qua `variant`) |
| `config` | `"sha256:<hex>"` của config blob |
| `layers` | danh sách `"sha256:<hex>"` theo thứ tự trong `Layers` |
| `size` | tổng số byte của các blob layer trong tar |

**`check_image(path, platform) -> list[str]`**, rỗng nghĩa là mang đi được. Mỗi vấn đề bắt đầu bằng đúng một trong các
dạng sau:

| Dạng | Khi nào |
| --- | --- |
| `không đọc được: <chi tiết>` | Không phải tar, tar hỏng, không có/không đọc được `manifest.json` (vấn đề duy nhất trả về) |
| `cần đúng 1 image, có <n>` | `manifest.json` có số phần tử khác 1 (vấn đề duy nhất trả về) |
| `thiếu blob: <đường dẫn trong tar>` | `Config` hoặc một `Layers` không có trong tar |
| `sai digest: <đường dẫn trong tar>` | Blob dưới `blobs/sha256/` có sha256 nội dung khác tên tệp |
| `sai nền tảng: <có>, cần <platform>` | `platform` của config (dạng như trên) khác tham số |
| `không có tag` | `RepoTags` rỗng hoặc `null` (lưu bằng image ID: load xong không có tên để chạy) |

Tar bị cắt cụt ở bất kỳ đâu phải ra ít nhất một vấn đề thuộc các dạng trên.

## Tiêu chí đạt

- `test_inspect_amd64`, `test_inspect_arm64`: đúng 5 khoá và giá trị trên hai tarball thật.
- `test_check_clean_tarball`: tarball amd64 với `linux/amd64` ⇒ `[]`.
- `test_check_wrong_platform`: arm64 khi cần amd64 (và ngược lại) ⇒ đúng một dòng `sai nền tảng: …`.
- `test_check_tampered_layer`, `test_check_missing_layer`, `test_check_untagged`: lật một bit trong layer, bỏ layer, xoá
  `RepoTags` ⇒ đúng một vấn đề tương ứng.
- `test_check_truncated` (cắt giữa layer, ngay trước và giữa `manifest.json`), `test_check_not_a_tar` (một trang HTML
  lỗi tải về đặt tên `.tar`) ⇒ có vấn đề, đúng dạng.

## Gợi ý

### Gợi ý 1

`tarfile.open(path)` + `extractfile(member)` đọc từng tệp trong tar mà không giải nén ra đĩa. Băm blob theo khối, layer
thật có thể vài trăm MB.

### Gợi ý 2

Kiến trúc của image không nằm trong `manifest.json` mà trong config blob mà nó trỏ tới.

### Gợi ý 3

Tar cụt không phải lúc nào cũng làm `tarfile.open` lỗi: có khi nó chỉ "thấy ít tệp hơn", có khi lỗi lúc đọc nội dung một
tệp. Kiểm tra của bạn phải xử lý được cả hai, và không để exception thoát ra ngoài `check_image`.
