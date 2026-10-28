---
title: Viết unit và integration test cho pipeline đơn hàng (chấm bằng mutation testing)
level: intermediate
services: []
files:
  - path: starter/checks.py
    note: 7 TODO
  - path: tests/fixtures/pipeline.py
    note: Pipeline cần kiểm thử, đọc docstring để biết đặc tả. Không sửa
  - path: tests/fixtures/mutants.py
    note: Các bản lỗi dùng để chấm. Không sửa, nên đọc sau khi làm xong
  - path: tests/test_pipeline_testing.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/intermediate/03-pipeline-testing -q
---

## Mục tiêu

Tự viết được bộ test cho một pipeline dữ liệu: unit test cho hàm transform, functional test cho
quy tắc nghiệp vụ, integration test với database (SQLite), và hiểu thế nào là một bộ test "đủ tốt"
thông qua mutation testing.

## Đề bài

`tests/fixtures/pipeline.py` có ba hàm: `clean_orders`, `revenue_by_state`, `load_orders`. Docstring
đầu tệp là đặc tả. Viết các hàm `check_*` trong `starter/checks.py`; mỗi hàm nhận tham số `pipeline`
(một đối tượng có ba hàm trên) và dùng `assert` để kiểm tra một hành vi.

Bộ chấm làm hai việc:

1. Chạy mọi `check_*` trên pipeline **đúng**: tất cả phải pass.
2. Thay lần lượt từng hàm bằng một **mutant** (bản có bug cố ý, tổng cộng 7 mutant): với mỗi mutant,
   ít nhất một `check_*` phải fail (raise exception).

Bạn được thêm/bớt/đổi tên hàm check tuỳ ý (tối thiểu 4 hàm, tên bắt đầu `check_`), và nên tự tạo dữ
liệu nhỏ viết tay sao cho lộ được lỗi. Không đặt tên hàm bắt đầu bằng `test_`.

## Tiêu chí đạt

- Có ít nhất 4 hàm `check_*`.
- Mọi check pass trên pipeline đúng.
- Cả 7 mutant đều bị ít nhất một check bắt được.
- Có ít nhất một check dùng SQLite (`sqlite3.connect(":memory:")`) để kiểm tra `load_orders`.

## Gợi ý

### Gợi ý 1

Một test chỉ bắt được bug nếu **dữ liệu** làm lộ bug. Ví dụ: muốn bắt lỗi "giữ bản trùng đầu tiên
thay vì bản mới nhất", input phải có bản **cũ** đứng **trước** bản mới. Muốn bắt lỗi "quên sắp xếp",
thứ tự đúng phải khác thứ tự alphabet mà `groupby` tạo ra.

### Gợi ý 2

Danh sách hành vi cần phủ: bỏ `order_id` rỗng; chuẩn hoá status; dedup giữ bản mới nhất; loại đơn
`canceled` khỏi doanh thu; sắp doanh thu giảm dần; load hai lần không nhân đôi; load lần hai cập
nhật giá trị mới (upsert chứ không phải `INSERT OR IGNORE`).
