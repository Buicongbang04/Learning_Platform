---
title: Preflight so với REQUIREMENTS.yaml
level: basic
services: []
files:
  - path: starter/preflight.py
    note: preflight() và main() còn TODO
  - path: tests/test_preflight.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/01-site-survey/exercises/basic/02-preflight -q
---

## Mục tiêu

Biến báo cáo survey thành quyết định: máy này cài được `quillo` không, cái gì **chặn** (blocker: có người khác, thường là IT
khách, phải làm trước ngày cài) và cái gì chỉ cần **lưu ý** (warning: FDE tự xử lý được trong buổi cài nếu đã chuẩn bị).

## Đề bài

Viết trong `starter/preflight.py`:

- `preflight(survey: dict, requirements: dict) -> list[dict]`: `survey` là JSON 13 khoá của bài 01, `requirements` là
  nội dung `tracks/fde/product/REQUIREMENTS.yaml` đã nạp. Trả danh sách phát hiện, mỗi phát hiện là dict đúng ba khoá
  `check`, `severity` (`blocker` hoặc `warning`), `detail` (một câu cho người đọc). Mỗi `check` xuất hiện tối đa một
  lần; máy đạt hết thì trả `[]`.
- `main(argv) -> int`: `python preflight.py <survey.json> <REQUIREMENTS.yaml>` in danh sách phát hiện dạng JSON ra
  stdout và trả mã thoát `1` nếu có ít nhất một blocker, `0` nếu không.

Mọi ngưỡng lấy từ `requirements` (test đổi ngưỡng để bắt code đặt cứng). Quy tắc từng `check`; ô "Chấp nhận" là những
mức test coi là đúng, "không báo" nghĩa là không có phát hiện cho check đó. Chỗ có hai mức là chỗ cần phán đoán: chọn một
và giải thích trong `detail`.

| `check` | Tình huống | Chấp nhận |
| --- | --- | --- |
| `os` | `os_id` không có trong `os`, hoặc `os_version` thấp hơn `min` (so theo **số**, `8.10` mới hơn `8.9`) | blocker |
| `cpus` | `cpus` < `min_cpus` | blocker |
| `mem` | `mem_mb` < 90% `min_mem_mb` | blocker |
| `mem` | 90% `min_mem_mb` ≤ `mem_mb` < `min_mem_mb` (máy "4 GB" thường báo `MemTotal` ~3,8 GB) | warning hoặc blocker |
| `disk` | `disk_free_gb_max` < `min_disk_free_gb` | blocker |
| `disk` | `min_disk_free_gb` ≤ `disk_free_gb_max` < 2 × `min_disk_free_gb` | không báo hoặc warning |
| `runtime` | `runtime` là `null` hoặc tên không có trong danh sách `runtime` (vd. `podman>=4.0` ⇒ tên `podman`) | blocker |
| `sudo` | `sudo` false và `runtime` là `docker` | warning hoặc blocker |
| `sudo` | `sudo` false và `runtime` là `podman` (rootless chạy được không cần root) | không báo hoặc warning |
| `selinux` | `enforcing` | không báo hoặc warning |
| `egress` | `none` hoặc `proxy` | không báo hoặc warning |
| `gpu` | mọi trường hợp (`gpu: optional`) | không báo |

Mọi tình huống không có trong bảng (vd. đủ RAM, `selinux` `permissive`, `egress` `open`) ⇒ không báo. Với blocker của
`cpus`, `mem`, `disk`, `detail` phải ghi cả **giá trị đo được** và **mức yêu cầu** đúng như chúng xuất hiện trong dữ liệu
(vd. `6.0` và `10`), để IT khách đọc là hiểu không cần mở tệp yêu cầu.

Survey không có phiên bản runtime và không có trạng thái cổng `18080`: preflight từ JSON không kiểm được hai yêu cầu đó.
Bài 03 kiểm cổng tại chỗ; phiên bản runtime bạn hỏi trong pre-visit (Advanced 02).

## Tiêu chí đạt

- Mọi test trong `tests/test_preflight.py` pass: định dạng phát hiện, các ca theo bảng trên, bốn hồ sơ khách (dữ liệu
  survey đo thật, RAM mặc định 2048 MB nên `mem` luôn là blocker), ngưỡng đọc từ `requirements`, CLI in JSON và mã thoát.
- Ca bắt buộc: `hospital` có blocker `disk` (đĩa 8 GB, còn 6,0 GiB); `bank` (không sudo, Podman rootless) **không** có
  blocker `sudo`.

## Gợi ý

### Gợi ý 1

So phiên bản bằng tuple số: tách mọi cụm chữ số rồi so tuple. So chuỗi sẽ cho `"8.10" < "8.9"`.

### Gợi ý 2

Mục `runtime` trong yêu cầu là chuỗi kiểu pip (`docker>=20.10`): chỉ cần phần tên trước toán tử để so với survey.

### Gợi ý 3

Viết `detail` cho người không đọc code: "Còn trống 6.0 GiB ở /, cần tối thiểu 10 GiB" tốt hơn "disk fail".
