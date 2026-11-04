---
title: Image sẽ nằm ở đâu — đo đĩa đúng chỗ
level: intermediate
services: []
files:
  - path: starter/storage_report.sh
    note: 3 TODO, POSIX sh
  - path: tests/test_storage_report.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - nice -n 15 uv run python -m fdekit prepare bank
  - uv run pytest tracks/fde/modules/01-site-survey/exercises/intermediate/02-where-data-lands -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

`df /` báo còn 18 GB không có nghĩa là `quillo` có 18 GB. Image, container và volume nằm ở thư mục dữ liệu của container
runtime, và ở khách thật thư mục đó rất hay nằm trên một volume khác. Bài này đo dung lượng **ở đúng chỗ dữ liệu sẽ
nằm**, với user thường.

## Đề bài

Viết `starter/storage_report.sh`. Chạy `sh storage_report.sh`, in ra stdout đúng một object JSON với 5 khoá **theo thứ
tự**:

| Khoá | Giá trị |
| --- | --- |
| `runtime` | `docker` nếu Docker daemon trả lời user này, ngược lại `podman` nếu Podman chạy được, không thì `null` |
| `data_root` | Thư mục runtime đó **thật sự** dùng để lưu image/container cho user này (đường dẫn tuyệt đối), `null` nếu không có runtime |
| `data_mount` | Điểm mount của filesystem chứa `data_root` |
| `data_free_gb` | Dung lượng còn trống cho user thường trên filesystem đó, GiB, làm tròn 2 chữ số thập phân |
| `inodes_free_pct` | Phần trăm inode còn trống trên filesystem đó, số nguyên (bỏ phần lẻ) |

Ràng buộc: POSIX `sh`, không `sudo`, thoát `0` trong 30 giây. Thư mục dữ liệu có thể thuộc root và user thường không
liệt kê được bên trong.

Test chạy script hai lần trên mỗi máy, đổi cấu hình ở giữa như IT khách hay làm:

- `lab-open` (Docker): lần một như mặc định; rồi IT gắn một volume riêng 2 GB và chuyển thư mục dữ liệu của Docker sang
  đó (cấu hình daemon, restart Docker); chạy lần hai.
- `bank` (Podman rootless, không sudo): lần một như mặc định; rồi cấu hình lưu trữ của user được đổi sang một chỗ khác
  (đường dẫn ngẫu nhiên); chạy lần hai.

## Tiêu chí đạt

- `test_docker_data_root_moved_by_it`, `test_rootless_podman_storage`: mỗi lần chạy, script thoát `0` trong ≤30 s, stdout
  là JSON đúng 5 khoá theo thứ tự trên.
- `runtime`, `data_root`, `data_mount` khớp đúng giá trị đo trong cùng VM (trước và sau khi đổi cấu hình).
- `data_free_gb` lệch không quá 0,05 GiB so với cột Available của `df` tại `data_root`; `inodes_free_pct` là số nguyên,
  lệch không quá 1 so với `IFree / Inodes × 100` của `df -i` tại đó.

## Gợi ý

### Gợi ý 1

Đừng đoán đường dẫn từ tài liệu hay từ tệp cấu hình hệ thống: hỏi chính runtime. Cả hai có `info` với `--format` theo Go
template; tìm trường thư mục gốc trong `docker info --format '{{json .}}'` và `podman info --format json`.

### Gợi ý 2

`df <đường dẫn>` chỉ cần `stat` được chính đường dẫn đó, không cần đọc bên trong. `df -P` cho định dạng ổn định; cột cuối
là điểm mount.

### Gợi ý 3

Podman rootless và Podman chạy bằng root đọc **hai** cấu hình lưu trữ khác nhau. Tệp trong `/etc/containers/` không nói
cho bạn biết user này lưu ở đâu.
