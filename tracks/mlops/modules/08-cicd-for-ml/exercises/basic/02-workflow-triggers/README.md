---
title: Trigger cho workflow huấn luyện - push, path filter, schedule, dispatch
level: basic
services: []
files:
  - path: starter/ct.yml
    note: Workflow, thiếu trigger
  - path: tests/test_triggers.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/08-cicd-for-ml/exercises/basic/02-workflow-triggers -q
---

## Mục tiêu

Quyết định **khi nào** một pipeline chạy lại model: mỗi lần push thì quá tốn, chỉ chạy tay thì model cũ đi mà không ai biết.
Bạn chọn bốn loại trigger cho một workflow huấn luyện và biết từng loại làm gì.

## Đề bài

Trong `starter/ct.yml` (workflow `ct`, đã có job `train` chỉ in sự kiện kích hoạt) viết khoá `on:` và `permissions:`:

1. `push` chỉ trên nhánh `main` và chỉ khi đổi `params.yaml` hoặc `data.dvc` (đúng hai đường dẫn này, bằng `paths:`).
2. `pull_request` với cùng bộ lọc đường dẫn.
3. `schedule` đúng một cron chạy mỗi thứ Hai, dạng `phút giờ * * 1`, cả phút và giờ là số, khác 00:00 UTC (giờ đó GitHub
   rất tải và lịch hay bị trễ). Nhớ rằng cron của GitHub tính theo UTC và chỉ chạy trên nhánh mặc định.
4. `workflow_dispatch` với input `reason` (`type: string`, `required: true`) để người chạy tay phải ghi lý do.
5. `permissions: { contents: read }` ở cấp workflow, vì job này không cần quyền ghi.

Test đọc YAML (PyYAML đọc khoá `on` thành `True`, helper `cikit` đã xử lý) rồi chạy `act -l` cho từng sự kiện để xác nhận job
`train` còn được liệt kê.

## Tiêu chí đạt

- `push`: `branches == ["main"]`, `paths` gồm đúng `params.yaml` và `data.dvc`.
- `pull_request`: cùng `paths`.
- Một cron duy nhất đúng dạng, không phải 00:00.
- `workflow_dispatch.inputs.reason` bắt buộc, kiểu string.
- `permissions` đúng bằng `{contents: read}`.
- `act -l` cho `push`, `pull_request`, `schedule`, `workflow_dispatch` đều thoát 0 và liệt kê `train`.

## Gợi ý

### Gợi ý 1

`paths:` và `branches:` đặt bên trong từng sự kiện, không phải ở cấp `on`. Hai bộ lọc cùng có mặt thì phải thoả cả hai.
`schedule:` là danh sách các mục `- cron: "..."`; nhớ đặt trong dấu nháy vì chuỗi có dấu `*`.

### Gợi ý 2

Dạng `phút giờ * * 1`: `30 2 * * 1` là 02:30 UTC thứ Hai, tức 09:30 giờ Việt Nam. Khi cần chạy tay, `workflow_dispatch` cho
nút "Run workflow" trong tab Actions; `inputs` hiện thành ô nhập trong form đó.
