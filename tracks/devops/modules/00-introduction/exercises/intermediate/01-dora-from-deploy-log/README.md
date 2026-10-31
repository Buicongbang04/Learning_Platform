---
title: Tính DORA metrics từ log deploy, commit và incident
level: intermediate
services: []
files:
  - path: starter/dora.py
    note: 10 TODO
  - path: tests/fixtures/deploys.jsonl
    note: Log deploy một tuần của Olist Shop
  - path: tests/fixtures/commits.jsonl
    note: Thời điểm commit
  - path: tests/fixtures/incidents.jsonl
    note: Incident, có trường caused_by_deploy
  - path: tests/test_dora.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/00-introduction/exercises/intermediate/01-dora-from-deploy-log -q
---

## Mục tiêu

Tự tính bốn DORA key metrics từ dữ liệu thô thay vì đọc số trên dashboard của một công cụ, và tự quyết định (rồi
bảo vệ được) từng quy tắc đếm: deploy nào được đếm, thế nào là một failed change, lead time kết thúc ở đâu, khôi
phục tính từ lúc nào.

## Đề bài

Tuần 1–7/10/2026, Olist Shop (API và worker) có ba log JSON Lines trong `tests/fixtures/`:

- `deploys.jsonl`: `id`, `env` (`production`/`staging`), `status` (`success` khi bản mới đã chạy trên môi trường,
  `failed` khi pipeline dừng trước đó và môi trường không đổi), `finished_at`, `commits` (SHA có trong lần deploy),
  `rollback_of` (id của deploy bị rollback, `null` nếu là deploy thường).
- `commits.jsonl`: `sha`, `committed_at`.
- `incidents.jsonl`: `id`, `caused_by_deploy` (`null` nếu không do thay đổi gây ra), `started_at`, `resolved_at`.

Cửa sổ đo là `[start, end)` với `start`, `end` có múi giờ. Viết các hàm trong `starter/dora.py` theo **đúng** quy
tắc dưới đây (đây là quyết định đo lường của team, phần 3 của lý thuyết giải thích vì sao):

1. `parse_ts`: đọc ISO 8601, trả thời điểm UTC. Thiếu múi giờ thì `ValueError`; log không múi giờ là log không
   dùng được để đo.
2. `counted_deploys`: deploy được đếm là deploy `production`, `status == "success"`, **không phải** rollback, và
   `finished_at` nằm trong cửa sổ (so theo thời điểm, không theo chuỗi ngày). Sắp theo thời gian. `start >= end`
   thì `ValueError`.
3. `failed_change_ids`: deploy được đếm mà sau đó bị rollback (có deploy thành công trỏ `rollback_of` vào nó) hoặc
   gây ra ít nhất một incident. Mỗi deploy tính một lần dù có nhiều alert.
4. `deployment_frequency`: số deploy được đếm chia số ngày của cửa sổ.
5. `change_failure_rate`: số failed change chia số deploy được đếm; cửa sổ không có deploy thì `None`, không phải
   `0`.
6. `lead_times`: với mỗi SHA, thời gian từ `committed_at` tới deploy được đếm **sớm nhất** chứa nó mà không bị
   rollback (commit đã thực sự chạy trên production). SHA không có trong `commits.jsonl` thì bỏ qua.
7. `median_lead_time`: median của `lead_times`, rỗng thì `None`.
8. `recovery_times`: với mỗi failed change, thời gian từ `finished_at` của deploy lỗi tới sự kiện khôi phục **cuối
   cùng** (deploy rollback xong, hoặc incident liên quan được đóng). Còn incident liên quan chưa đóng thì chưa tính.
9. `median_recovery_time` và `dora_report`: trả dict `deploys_per_week`, `change_failure_rate`,
   `median_lead_time_hours`, `median_recovery_hours` (số thực hoặc `None`).

`load_jsonl` đã viết sẵn.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/00-introduction/exercises/intermediate/01-dora-from-deploy-log -q` pass toàn bộ.
- Xếp được bốn con số của tuần này vào bảng mức DORA 2024 và nói metric nào khó tin nhất với cỡ mẫu 9 deploy.
- Kể ra ít nhất ba chỗ trong log mà một cách đếm ngây thơ sẽ cho số sai (rollback, deploy `failed`, staging, cửa
  sổ theo múi giờ, deploy không khớp commit).

## Gợi ý

### Gợi ý 1

Đọc kỹ log trước khi code. Tự đánh dấu bằng tay: `d00` có `finished_at` ghi ngày 30/9 nhưng là 01:00 ngày 1/10
giờ Việt Nam; `d06` là rollback của `d05`; `d10` chứa một SHA không có trong `commits.jsonl`; incident `i03` không
do deploy nào gây ra; `i01` và `i04` cùng trỏ vào `d05`.

### Gợi ý 2

Tập rollback: `{d["rollback_of"] for d in deploys if d["rollback_of"]}`. `statistics.median` chạy được trên list
`timedelta` (chẵn phần tử thì lấy trung bình hai giá trị giữa). Đổi `timedelta` ra giờ bằng `td / timedelta(hours=1)`.
Với lead time, duyệt deploy theo thời gian và chỉ ghi SHA lần đầu gặp ở deploy không bị rollback.
