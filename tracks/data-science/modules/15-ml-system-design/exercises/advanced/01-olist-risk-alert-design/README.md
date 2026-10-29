---
title: Design doc hệ thống cảnh báo đơn rủi ro cho Olist
level: advanced
services: []
files:
  - path: starter/policy.py
    note: 3 hàm TODO
  - path: starter/DESIGN.md
    note: Design doc 12 mục
  - path: tests/test_policy.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/15-ml-system-design/exercises/advanced/01-olist-risk-alert-design -q
---

## Mục tiêu

Viết một design doc đủ để DS và kỹ sư khác review, đội CSKH vận hành, và PM đo được thành công: đi trọn
tám bước của khung system design trên một hệ thống thật, với số liệu thật và các đánh đổi viết ra rõ
ràng. Đây cũng là bản thiết kế cho milestone cuối của capstone.

## Đề bài

Olist muốn giảm review 1–2 sao bằng cách cảnh báo đơn có nguy cơ giao trễ để CSKH chủ động liên hệ
**trước khi** đơn tới tay khách. Vì hành động xảy ra trước khi giao, thời điểm dự đoán phải là lúc đặt
hàng hoặc lúc giao cho vận chuyển, và mọi thông tin sau thời điểm đó (ngày giao thực tế, trễ hay không,
review) là leak. Đó là khác biệt có chủ đích với model review xấu "lúc đơn vừa giao" của module 10/11,
nơi ngày giao là feature hợp lệ: **thời điểm dự đoán đi theo hành động**.

1. Trong `starter/policy.py`:
   - `weekly_late_volume(orders, start, end)`: số đơn trễ mỗi tuần, để lập kế hoạch năng lực.
   - `hybrid_alerts(scores, weeks, threshold, cap_per_week)`: chính sách lai ngưỡng + trần mỗi tuần.
   - `choose_policy(...)`: vét cạn lưới (ngưỡng, trần) theo giá trị tiền, hoà thì chọn ít cảnh báo hơn.
2. Dùng model của bài Intermediate 01 (hoặc của bạn): chọn chính sách trên **validation**, báo cáo trên
   **test**.
3. Viết `starter/DESIGN.md` theo khung 12 mục có sẵn. Dùng số liệu từ các bài Basic và Intermediate của
   module.

## Tiêu chí đạt

- Ba hàm đúng trên dữ liệu nhỏ và khớp vét cạn tham chiếu trên dữ liệu giả lập.
- Trên Olist thật: 61 tuần trong 06/2017 – 07/2018, trung vị 61 đơn trễ mỗi tuần, tuần tệ nhất 565.
- `DESIGN.md` đủ 12 mục (giữ nguyên tiêu đề), không còn TODO, ít nhất 1 200 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`o.order_purchase_timestamp.dt.to_period("W-SUN").dt.end_time.dt.normalize()` cho ngày Chủ nhật của tuần.
`pd.date_range(start, end, freq="W-SUN", inclusive="left")` cho đủ các tuần, rồi `reindex(..., fill_value=0)`.

### Gợi ý 2

Design doc tốt viết **đánh đổi**, không chỉ lựa chọn: vì sao lúc giao vận chuyển chứ không phải lúc đặt
hàng, vì sao batch, vì sao có trần, holdout bao nhiêu và mất gì. Mục "Phương án đã loại" là chỗ người
review đọc kỹ nhất. Nếu kết luận trung thực là "ra mắt luật trước, model sau" thì viết đúng như vậy.
