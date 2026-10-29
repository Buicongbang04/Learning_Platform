---
title: Thiết kế thu thập đa nguồn - database, log, mobile, API, IoT trong một nền tảng
level: advanced
services: []
files:
  - path: starter/sources.yaml
    note: Hợp đồng thu thập cho 5 nguồn (mới có khung nguồn đầu)
  - path: starter/design.md
    note: Văn bản thiết kế 7 mục
  - path: tests/test_design.py
    note: Không sửa; chỉ kiểm hợp đồng tối thiểu
run:
  - uv run pytest tracks/data-engineer/modules/00-introduction/exercises/advanced/02-multi-source-collection-design -q
---

## Mục tiêu

Thiết kế phần **thu thập** cho một nền tảng nhận dữ liệu từ đủ năm loại nguồn của phần 4 lý thuyết, trả lời bằng
văn bản mọi câu hỏi ở phần 5 (data collection considerations) cho từng nguồn, và chứng minh thiết kế chạy lại được,
chịu được dữ liệu đến trễ, bảo vệ dữ liệu cá nhân.

## Đề bài

**Bài toán.** Một chuỗi bán lẻ kiểu Olist (bán online, có 40 cửa hàng trải nghiệm ở TP.HCM và Hà Nội) muốn trả lời:
doanh số online và lượng khách tới cửa hàng thay đổi thế nào theo **thời tiết** và **chất lượng không khí**, và hành vi
trên web/app trước khi mua. Nguồn:

| Nguồn | Mô tả | Gợi ý số liệu (lấy từ các bài trước) |
| --- | --- | --- |
| `orders_db` | PostgreSQL OLTP của hệ thống đơn hàng (bảng như Olist), trạng thái đơn đổi nhiều ngày sau | Olist ~100 nghìn đơn/2 năm |
| `web_access_log` | Access log của web server, Common Log Format | NASA: ~68 600 request/ngày, 108 byte/dòng |
| `app_events` | Event từ app mobile qua SDK (`event_id`, `event_time`, `user_id`...) | tự ước lượng |
| `weather_api` | Open-Meteo theo ngày cho 2 thành phố | basic 01: 2 request/năm-thành phố |
| `store_air_sensors` | Cảm biến khí trong 40 cửa hàng, mỗi phút, qua MQTT gateway | UCI: 84 byte/dòng, `-200` là thiếu |

Việc cần làm:

1. `starter/sources.yaml`: một mục cho mỗi nguồn với đủ các trường trong khung (type, pull/push, mode, tần suất,
   khoá incremental, khoá dedup, cửa sổ late data, chỗ lưu thô, cột PII, ít nhất 2 quality check, giới hạn phía
   nguồn, chủ sở hữu). Đây là bản nháp **data contract**.
2. `starter/design.md`: 7 mục `## Kiến trúc` (có sơ đồ mermaid), `## Lịch chạy và phụ thuộc`,
   `## Idempotency và chạy lại`, `## Dữ liệu đến trễ`, `## Bảo mật và PII`, `## Giám sát`,
   `## Chi phí và dung lượng` (có con số).

## Tiêu chí đạt

- Test pass: đủ 5 loại nguồn, mỗi nguồn đủ trường với giá trị hợp lệ; nguồn incremental/CDC có khoá; nguồn không có
  khoá dedup thì giải thích; mỗi nguồn một chỗ lưu thô riêng; database và mobile khai báo PII; nguồn push không dùng
  `full`; `design.md` đủ 7 mục, có mermaid, có dung lượng bằng số.
- Lựa chọn của từng nguồn có lý do gắn với đặc tính của nguồn đó (không chép một cấu hình cho cả 5).
- Rubric chi tiết trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đi từng nguồn qua checklist ở phần 5 của lý thuyết: khoá chính là gì, bản ghi có bị sửa không, đến trễ tối đa bao lâu,
có PII không, nguồn chịu tải được bao nhiêu. Câu trả lời điền thẳng vào `sources.yaml`. Đừng quên: đơn Olist đổi trạng
thái nhiều ngày sau, app gửi bù sau khi offline, log không có khoá.

### Gợi ý 2

Idempotency đến từ hai thứ: vùng thô ghi theo **partition xác định** (nguồn + ngày ingest) và ghi đè cả partition khi
chạy lại; vùng sạch **upsert theo khoá dedup**. Late data: partition theo event time phải được mở lại trong cửa sổ late
data; ngoài cửa sổ thì ghi vào bảng "đến quá trễ" và cảnh báo.
