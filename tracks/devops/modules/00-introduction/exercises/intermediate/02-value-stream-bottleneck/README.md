---
title: Tìm nút thắt trong value stream từ commit tới production
level: intermediate
services: []
files:
  - path: starter/value_stream.py
    note: 7 TODO
  - path: tests/fixtures/changes.jsonl
    note: 8 pull request của Olist Shop
  - path: tests/test_value_stream.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/00-introduction/exercises/intermediate/02-value-stream-bottleneck -q
---

## Mục tiêu

Tách change lead time thành từng stage của vòng đời phần mềm để biết thời gian thực sự mất ở đâu, trước khi đề
xuất mua công cụ. Hiểu vì sao dùng median chứ không dùng mean khi tìm nút thắt, và vì sao flow efficiency thường
thấp tới mức bất ngờ.

## Đề bài

`tests/fixtures/changes.jsonl` có 8 pull request của Olist Shop. Mỗi dòng có `id` và sáu thời điểm (có múi giờ,
mỗi hệ thống ghi một offset): `first_commit_at`, `pr_opened_at`, `first_review_at`, `approved_at`, `merged_at`,
`deployed_at`. Thời điểm chưa xảy ra là `null`.

`STAGES` trong `starter/value_stream.py` đã khai báo năm stage theo thứ tự, mỗi stage là cặp (mốc đầu, mốc cuối):
`coding`, `review_wait`, `review`, `merge_wait`, `deploy_wait`. Viết các hàm:

1. `parse_ts`: thiếu múi giờ thì `ValueError`.
2. `stage_durations(change)`: dict stage → `timedelta`. Báo `ValueError` khi: chưa deploy; có `first_review_at`
   mà thiếu `approved_at` hoặc ngược lại; một mốc đứng trước mốc liền trước nó. PR **tự merge** (cả
   `first_review_at` và `approved_at` là `null`, thường là hotfix) thì `review_wait` và `review` bằng 0, còn
   `merge_wait` tính từ `pr_opened_at`.
3. `completed_changes`: các thay đổi đã deploy, giữ thứ tự.
4. `unreviewed`: id các PR đã merge mà không có review (cờ cho audit, không phải lỗi dữ liệu).
5. `stage_medians`: median từng stage trên các thay đổi đã deploy; không có thì `{}`.
6. `bottleneck`: stage có median lớn nhất, hoà thì chọn stage đứng trước; không có dữ liệu thì `None`.
7. `flow_efficiency(changes, active=("coding", "review"))`: tổng thời gian ở các stage `active` chia tổng lead time,
   cộng gộp trên mọi thay đổi đã deploy (không lấy trung bình của từng tỉ lệ); không có dữ liệu thì `None`.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/00-introduction/exercises/intermediate/02-value-stream-bottleneck -q` pass toàn bộ.
- Chỉ ra được stage nào sẽ bị chọn nhầm là nút thắt nếu dùng mean, và thay đổi nào gây ra điều đó.
- Đề xuất một thay đổi quy trình (không phải mua công cụ) cho nút thắt tìm được, kèm metric để biết nó có tác dụng.

## Gợi ý

### Gợi ý 1

Với PR tự merge, cách gọn nhất là coi như `first_review_at` và `approved_at` bằng `pr_opened_at`, rồi dùng chung
vòng lặp qua `STAGES`. Kiểm `timedelta < timedelta(0)` để bắt mốc sai thứ tự.

### Gợi ý 2

`max(STAGES, key=...)` trả phần tử đầu tiên khi có hoà, vì `STAGES` là dict giữ thứ tự khai báo. Cộng `timedelta`
bằng `sum(..., timedelta(0))`. Tỉ số hai `timedelta` là `float`.
