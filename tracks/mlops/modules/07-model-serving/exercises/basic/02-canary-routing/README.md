---
title: Định tuyến canary và A/B bằng hash ổn định
level: basic
services: []
files:
  - path: starter/routing.py
    note: Hiện dùng random, viết lại ba hàm
  - path: tests/test_routing.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/07-model-serving/exercises/basic/02-canary-routing -q
---

## Mục tiêu

Chia traffic giữa hai model theo trọng số mà vẫn tái lập được: cùng id luôn về cùng một nhánh, ở mọi tiến trình và mọi lần chạy.

## Đề bài

`starter/routing.py` đang chọn nhánh bằng `random.random()`, nên cùng một request lúc vào stable lúc vào canary. Viết lại ba hàm:

- `bucket(request_id, salt="") -> float` trong [0, 1): SHA-256 của chuỗi `f"{salt}:{request_id}"`, lấy 8 byte đầu (big-endian) chia cho `2**64`. Không dùng `hash()` của Python (đổi theo tiến trình) hay `random`.
- `route(request_id, canary_weight, salt="") -> "canary" | "stable"`: `canary` khi `bucket < canary_weight`. `canary_weight` ngoài [0, 1] thì `ValueError`. Trọng số 0 thì mọi request về `stable`, trọng số 1 thì về `canary`.
- `assign_variant(user_id, experiment, weights) -> str` cho A/B nhiều nhánh: `salt` là tên `experiment`; duyệt các nhánh **theo thứ tự tên tăng dần** (không theo thứ tự dict) và cộng dồn trọng số để chọn nhánh chứa `bucket`. `weights` rỗng, có trọng số âm hoặc tổng khác 1 (sai số 1e-9) thì `ValueError`. Nhánh trọng số 0 không bao giờ được chọn.

Test kiểm: tỉ lệ canary trong ±3% so với trọng số trên 2000 request (`req-0` tới `req-1999`) cho các trọng số 0.05, 0.1, 0.25, 0.5; cùng id cùng nhánh, kể cả giữa các tiến trình có `PYTHONHASHSEED` khác nhau; tăng trọng số chỉ thêm id vào canary, không đưa id nào từ canary về stable; hai thí nghiệm khác salt độc lập nhau (với trọng số 0.5, khoảng 25% id nằm trong cả hai, cho phép 20% tới 30%); A/B ba nhánh đúng tỉ lệ ±3% trên 3000 người dùng.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/07-model-serving/exercises/basic/02-canary-routing -q` pass.
- Giải thích được vì sao ném đồng xu mỗi request là sai cho canary, và khi nào nên băm `user_id` thay vì `request_id`.
- Nói được hệ quả nếu hai thí nghiệm dùng chung salt.

## Gợi ý

### Gợi ý 1

`hashlib.sha256(...).digest()[:8]` rồi `int.from_bytes(..., "big") / 2**64`.

### Gợi ý 2

Với `assign_variant`, `sorted(weights)` cho thứ tự cố định; nhớ trả nhánh cuối cùng có trọng số dương nếu sai số làm tổng cộng dồn hụt một chút.
