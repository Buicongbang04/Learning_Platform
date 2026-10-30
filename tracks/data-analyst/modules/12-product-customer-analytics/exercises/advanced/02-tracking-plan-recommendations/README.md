---
title: Tracking plan cho khối "Thường mua kèm" và script kiểm log trước khi ra mắt
level: advanced
services: []
files:
  - path: starter/tracking_plan.yaml
    note: Sự kiện, thuộc tính, kiểu, owner, metric
  - path: starter/validate_events.py
    note: 2 hàm TODO - kiểm log so với plan
  - path: starter/PLAN.md
    note: Metric, quyết định, phân khúc, QA, rủi ro (250-900 từ)
  - path: tests/test_tracking_plan.py
    note: Không sửa
run:
  - uv run pytest tracks/data-analyst/modules/12-product-customer-analytics/exercises/advanced/02-tracking-plan-recommendations -q
---

## Mục tiêu

Thiết kế dữ liệu sự kiện **trước** khi tính năng ra mắt: bắt đầu từ câu hỏi và metric, đặt tên và kiểu cho từng sự
kiện, quyết định gửi từ client hay server, chuẩn bị sẵn thuộc tính để tách phân khúc, và viết script kiểm log tự động
để không mất dữ liệu của những tuần đầu.

## Đề bài

Sau bài Intermediate 02, team product quyết định làm khối **"Thường mua kèm"** trên trang sản phẩm của cửa hàng
Online Retail: hiện 3-4 sản phẩm lấy từ luật market basket (dự phòng là hàng bán chạy khi sản phẩm không có luật), ra
mắt dưới dạng A/B test. PM hỏi: **"Cần ghi những gì để sau 4 tuần trả lời được khối này có tăng doanh thu không, và cho
ai?"**. Bài học từ phần 2 của lý thuyết: log Retailrocket không có phiên, nguồn thêm giỏ, tình trạng còn hàng, nên
nhiều câu hỏi không trả lời được. Làm ba việc:

1. **`starter/tracking_plan.yaml`**: `feature`, `common_properties` (bắt buộc có `anonymous_id`, `session_id`,
   `event_time` bắt buộc và `user_id` tuỳ chọn), `events` (ít nhất 4, ít nhất 2 sự kiện `recommendation_...`). Mỗi sự
   kiện có `trigger`, `owner`, `metrics` (danh sách), `properties`; mỗi thuộc tính có `type` (`string`, `integer`,
   `number`, `boolean`, `timestamp`, `array`), `required`, và `enum` nếu là tập giá trị cố định. Tên sự kiện
   snake_case dạng object_action. Không có dữ liệu cá nhân.
2. **`starter/validate_events.py`**: `validate_event(event, plan)` trả danh sách lỗi đã sắp xếp (`unknown_event`,
   `missing:<thuộc tính>`, `type:<thuộc tính>`, `enum:<thuộc tính>`, `extra:<thuộc tính>`; quy tắc từng kiểu trong
   docstring), `validate_log(events, plan)` đếm lỗi theo sự kiện.
3. **`starter/PLAN.md`** theo khung có sẵn: metric chính, phụ, guardrail có công thức từ sự kiện; bảng sự kiện và các
   quyết định khó; phân tích phân khúc sau ra mắt (gợi ý: phân khúc RFM của bài Intermediate 01); QA trước ra mắt;
   rủi ro và quyền riêng tư.

## Tiêu chí đạt

- Test của validator pass trên plan và sự kiện mẫu sinh trong test: sự kiện lạ, thiếu thuộc tính bắt buộc (kể cả thuộc
  tính chung, kể cả giá trị `None`), sai kiểu (bool không phải số), giá trị ngoài enum, thuộc tính thừa, đếm lỗi.
- `tracking_plan.yaml` hợp lệ theo các quy tắc ở đề, và mọi sự kiện mẫu dựng từ chính plan (đủ thuộc tính bắt buộc)
  qua được validator của bạn.
- `PLAN.md` không còn TODO, 250-900 từ, đủ mục. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đi ngược từ metric: "doanh thu mỗi người xem" cần biết ai đã **thấy** khối (impression, kèm nhóm A/B) và đơn hàng của
họ; "attach rate" cần biết món trong đơn có đến từ gợi ý không. Câu hỏi "khi nào tính là đã thấy" (render hay hiện
trong viewport) đổi CTR gấp nhiều lần: ghi rõ trong `trigger`. Giao dịch (thêm giỏ, đơn hàng) gửi từ server.

### Gợi ý 2

Validator: gộp `common_properties` với `properties` của sự kiện thành một bảng quy tắc; duyệt từng quy tắc (thiếu?
sai kiểu? ngoài enum?), rồi duyệt thuộc tính đã gửi để tìm thuộc tính thừa. Nhớ `isinstance(True, int)` là `True`
trong Python. `validate_log`: một dòng mỗi `(event, issue)`, `value_counts()`, rồi sắp.
