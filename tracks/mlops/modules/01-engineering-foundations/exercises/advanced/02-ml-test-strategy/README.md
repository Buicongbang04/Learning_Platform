---
title: Thiết kế chiến lược test cho dịch vụ ETA
level: advanced
services: []
files:
  - path: starter/test-strategy.yaml
    note: Điền các lớp test, chính sách flaky, giới hạn
  - path: tests/test_strategy.py
    note: Kiểm cấu trúc và ngân sách, không chấm nội dung
run:
  - uv run pytest tracks/mlops/modules/01-engineering-foundations/exercises/advanced/02-ml-test-strategy -q
---

## Mục tiêu

Quyết định lớp test nào chạy ở đâu (PR, hằng đêm, trước release) để mỗi loại lỗi ML bị bắt ở nơi rẻ nhất mà PR vẫn dưới 10 phút.

## Đề bài

Dịch vụ ETA cho taxi NYC có: hàm tạo feature, luật làm sạch dữ liệu, model GBM train hằng tuần, API `/predict` và image Docker. Đội 4 người, CI tối đa 10 phút cho một PR.
Viết `starter/test-strategy.yaml`:

- Ít nhất 6 lớp test, mỗi lớp có `name`, `kind` (`unit`, `data`, `model-behavior`, `model-quality`, `contract`, `smoke`), `what`, `catches` (một lỗi thật mà lớp này bắt được và lớp khác bỏ sót), `runs_on` (`pr`, `nightly`, `release`), `budget_seconds`.
- Phải có ít nhất các kind `unit`, `data`, `model-behavior`, `model-quality`.
- Tổng `budget_seconds` của lớp `pr` không quá `pr_budget_seconds`, và `pr_budget_seconds` không quá 600.
- `flaky_policy`: `max_retries` (0 hoặc 1), `quarantine`, `owner`, `deadline_days`.
- `gaps`: ít nhất 3 rủi ro ML bạn cố ý **không** bắt bằng CI, mỗi mục có `risk` và `reason`.

Các ràng buộc test kiểm thêm: `name` duy nhất; `what` và `catches` dài ít nhất 20 ký tự và `catches` khác nhau giữa các lớp và khác `what` của chính lớp đó; có ít nhất một lớp `runs_on` khác `pr`; `budget_seconds` là số nguyên dương; lớp `model-quality` chạy ở `pr` chỉ khi `budget_seconds` không quá 120; `flaky_policy.owner` khác rỗng và `deadline_days` dương; mỗi `gaps` có `risk` từ 10 ký tự và `reason` từ 20 ký tự. Test chỉ kiểm cấu trúc và ngân sách; nội dung chấm theo rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Đủ lớp, đủ kind, các trường hợp lệ và mô tả cụ thể.
- Tổng thời gian lớp PR nằm trong ngân sách; lớp train nặng không nằm trong PR.
- Mỗi lớp bắt một lỗi khác nhau.
- Chính sách flaky có giới hạn retry, cách ly có hạn và người chịu trách nhiệm.
- `gaps` nói thật điều CI không bắt được.

## Gợi ý

### Gợi ý 1

Bắt đầu từ danh sách lỗi đã từng hoặc dễ xảy ra, rồi hỏi "lớp rẻ nhất bắt nó là gì", không bắt đầu từ danh sách loại test trong sách.

### Gợi ý 2

Đo thời gian thật bằng `pytest --durations` trên mẫu nhỏ trước khi điền `budget_seconds`; ngân sách mơ hồ không phải ngân sách.

### Gợi ý 3

Nếu bạn không viết được `gaps`, bạn chưa nghĩ tới monitoring ở module 09-10: CI chỉ thấy dữ liệu đã có, production thấy dữ liệu mới.
