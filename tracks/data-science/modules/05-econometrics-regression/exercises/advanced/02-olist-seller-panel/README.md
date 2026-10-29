---
title: Panel seller × tháng trên Olist - giao trễ và review xấu
level: advanced
services: []
files:
  - path: starter/seller_panel.ipynb
    note: seller_month_panel, fit_specs + phân tích tự do
  - path: starter/REPORT.md
    note: Báo cáo cho Head of Marketplace Quality
  - path: tests/test_seller_panel.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/05-econometrics-regression/exercises/advanced/02-olist-seller-panel/starter/seller_panel.ipynb
  - uv run pytest tracks/data-science/modules/05-econometrics-regression/exercises/advanced/02-olist-seller-panel -q
---

## Mục tiêu

Tự dựng một panel từ dữ liệu giao dịch, dùng fixed effects để loại các confounder không đổi theo
seller và theo tháng, đánh giá hệ số còn lại đáng tin tới đâu, và viết báo cáo cho người ra quyết
định mà không nói quá điều dữ liệu cho phép.

## Đề bài

Câu hỏi của Head of Marketplace Quality: "Nếu một seller giảm tỉ lệ giao trễ, tỉ lệ review xấu của
họ giảm bao nhiêu?"

1. `seller_month_panel(orders, reviews, items, start, end, min_orders, min_months)` trong notebook,
   đúng theo docstring (định nghĩa giao trễ, review, đơn giao xong giống mọi module trong track).
2. `fit_specs(panel)`: `bad_rate ~ late_rate` với pooled, seller FE, two-way FE (seller + tháng),
   không trọng số, SE cluster theo seller. Trả bảng `coef`, `se`.
3. Phân tích thêm: trọng số theo số đơn, độ nhạy theo `min_orders`, biến trễ, nhóm seller… tuỳ bạn.
4. `starter/REPORT.md` theo khung có sẵn.

## Tiêu chí đạt

- `seller_month_panel` đúng trên dữ liệu nhỏ trong test: review mới nhất, loại đơn nhiều seller, đơn
  chưa giao, đơn ngoài khoảng thời gian, áp đúng thứ tự hai bộ lọc.
- `fit_specs` đúng cấu trúc; trên dữ liệu mô phỏng có confounder theo seller và theo tháng, two-way FE
  gần hệ số thật còn pooled lệch lên.
- Trên Olist thật: 3 322 ô, 313 seller; hệ số two-way FE khoảng 0.48, nhỏ hơn pooled.
- `REPORT.md` không còn TODO, ít nhất 300 từ.
- Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đơn một seller: `items.groupby("order_id").seller_id.nunique() == 1`. Tháng:
`order_purchase_timestamp.dt.to_period("M").dt.to_timestamp()`. Lọc `min_orders` trước, rồi mới đếm
số tháng còn lại của mỗi seller.

### Gợi ý 2

Mỗi ô có trung vị khoảng 11 đơn, nên `late_rate` của một ô đo "tỉ lệ trễ thật" của seller tháng đó với
nhiều nhiễu. Fixed effects loại phần biến thiên giữa seller, phần còn lại có tỉ lệ nhiễu cao hơn; sai
số đo lường ở biến giải thích kéo hệ số về 0. Thử `min_orders=20` và so sánh.
