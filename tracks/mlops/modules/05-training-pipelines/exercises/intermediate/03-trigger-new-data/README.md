---
title: Trigger continuous training theo dữ liệu mới - chỉ train khi hash dữ liệu đổi
level: intermediate
services: []
files:
  - path: starter/trigger.py
    note: 1 hàm và 1 flow TODO
  - path: tests/test_trigger.py
    note: Không sửa
  - path: tests/conftest.py
    note: Dựng Prefect tạm, không sửa
run:
  - uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/intermediate/03-trigger-new-data -q
---

## Mục tiêu

Viết trigger "có dữ liệu mới" cho continuous training: flow chạy theo lịch nhưng chỉ train khi nội dung dữ liệu thật sự đổi và đủ
đáng kể, và trạng thái "đã train" chỉ được ghi khi train thành công.

## Đề bài

Trong `starter/trigger.py` cài `file_sha256(path)` (sha256 các byte của tệp) và flow Prefect
`ct_flow(data_path, state_path, train_fn, min_new_rows=0, force=False)`. `train_fn(path)` là hàm train do người gọi truyền vào
(test đếm số lần nó được gọi). Tệp dữ liệu là CSV có một dòng header; số dòng dữ liệu là số dòng không rỗng trừ đi header.
`state_path` là JSON `{"last_data_sha256": ..., "rows": ...}` của lần train thành công gần nhất.

Quy tắc test ép:

- chưa có state (lần đầu): luôn train, ghi state; trả `{"status": "trained", "data_sha256": ...}`; bỏ qua `min_new_rows`;
- hash trùng state: trả `{"status": "skipped", "reason": "unchanged"}`, không gọi `train_fn`; `touch` tệp (đổi mtime) không
  làm train lại;
- hash đổi nhưng số dòng mới (`rows` hiện tại trừ `rows` trong state) **nhỏ hơn** `min_new_rows`: trả
  `{"status": "skipped", "reason": "too_few_new_rows"}` và **không** cập nhật state (để dữ liệu tích luỹ tới ngưỡng); đúng bằng
  ngưỡng thì train;
- `force=True` luôn train, kể cả khi hash trùng hoặc ít dòng mới;
- `train_fn` ném lỗi thì lỗi lan ra ngoài và state giữ nguyên (không có state mới nếu chưa từng thành công), để lần chạy sau
  thử lại;
- tệp không tồn tại thì `FileNotFoundError`; tệp chỉ có header thì `ValueError`; cả hai xảy ra trước khi gọi `train_fn` và không
  ghi state.

## Tiêu chí đạt

- Chạy hai lần liên tiếp trên cùng dữ liệu: lần hai `skipped`, `train_fn` chỉ được gọi một lần.
- Thêm dòng vào tệp: lần chạy kế `trained`, state có `rows` mới.
- Train hỏng không làm mất khả năng thử lại ở lần chạy sau.

## Gợi ý

### Gợi ý 1

Thứ tự trong flow: kiểm tệp (tồn tại, không rỗng), tính hash và số dòng, đọc state, quyết định skip hay train, gọi `train_fn`,
**rồi mới** ghi state. Ghi state trước khi train là lỗi kinh điển: train hỏng mà hệ thống tin là đã xong.

### Gợi ý 2

Đọc tệp theo từng dòng để đếm, đừng nạp cả tệp vào bộ nhớ chỉ để đếm dòng. Ghi state bằng `json.dumps` thẳng vào tệp là đủ cho
bài này; ở production ghi qua tên tạm rồi đổi tên.
