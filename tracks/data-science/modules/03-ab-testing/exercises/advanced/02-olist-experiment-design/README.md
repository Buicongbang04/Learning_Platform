---
title: Viết tài liệu thiết kế thí nghiệm cho Olist
level: advanced
services: []
files:
  - path: starter/design.py
    note: Hàm baseline()
  - path: starter/DESIGN.md
    note: Tài liệu pre-registration
  - path: tests/test_design.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/03-ab-testing/exercises/advanced/02-olist-experiment-design -q
---

## Mục tiêu

Thiết kế một thí nghiệm thật từ con số nền thật, viết thành tài liệu pre-registration đủ để một DS
khác review và đội vận hành triển khai. Đây cũng là milestone A/B của capstone.

## Đề bài

Olist muốn giảm review 1–2 sao. Ý tưởng: khi model dự đoán một đơn có nguy cơ giao trễ, nhắn tin
chủ động cho khách (xin lỗi, báo ngày giao mới, tặng voucher nhỏ).

1. `baseline(orders, reviews) -> dict` trong `starter/design.py`, theo docstring: `bad_review_rate`,
   `late_rate`, `bad_review_rate_late`, `delivered_per_week`. Chú ý: một đơn có thể có nhiều review.
2. Chạy `baseline` trên Olist thật (đọc CSV ở `data/raw/`, parse các cột ngày).
3. Viết `starter/DESIGN.md` theo khung có sẵn. Dùng hàm cỡ mẫu của bài Basic 02 để tính power.

## Tiêu chí đạt

- `baseline` đúng trên dữ liệu nhỏ trong test (dedupe review, lọc đơn giao xong, bỏ tuần dở dang).
- Trên Olist thật: `bad_review_rate` ≈ 12.8%, `late_rate` ≈ 8.1%, review xấu ở đơn trễ trên 50%.
- `DESIGN.md` không còn TODO, ít nhất 400 từ.
- Nội dung thiết kế chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")`.
Số đơn theo tuần: `set_index("order_purchase_timestamp").resample("W").size()` (tuần mặc định kết
thúc Chủ nhật, tuần không có đơn được điền 0), rồi bỏ phần tử đầu và cuối.

### Gợi ý 2

Tổng thể của thí nghiệm là **đơn có nguy cơ trễ**, không phải mọi đơn. Baseline review xấu của tổng
thể này (khoảng 54% nếu dự đoán hoàn hảo, thấp hơn khi model có sai số) khác hẳn 12.8%, và số đơn
mỗi tuần cũng chỉ còn một phần nhỏ. Cả hai thay đổi phép tính cỡ mẫu và thời lượng. Cũng nhìn kỹ
`delivered_per_week`: trung vị trên toàn bộ dữ liệu có phản ánh traffic hiện tại không?
