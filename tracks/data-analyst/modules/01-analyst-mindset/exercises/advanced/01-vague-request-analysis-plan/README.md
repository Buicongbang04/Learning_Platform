---
title: Biến yêu cầu mơ hồ của CEO thành analysis plan - "khách quen không quay lại như trước"
level: advanced
services: []
files:
  - path: starter/baseline.ipynb
    note: 1 hàm TODO (baseline khách mới / quay lại) + kiểm dữ liệu cắt đầu
  - path: starter/ANALYSIS_PLAN.md
    note: Kế hoạch một trang gửi CEO duyệt
  - path: tests/test_plan.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/01-analyst-mindset/exercises/advanced/01-vague-request-analysis-plan/starter/baseline.ipynb
  - uv run pytest tracks/data-analyst/modules/01-analyst-mindset/exercises/advanced/01-vague-request-analysis-plan -q
---

## Mục tiêu

Làm việc một DA senior làm trước khi phân tích: nhận một câu "cảm giác" của CEO, tính một baseline nhanh để biết
vấn đề lớn cỡ nào và định nghĩa có bẫy gì, rồi viết analysis plan một trang (quyết định, câu hỏi đóng khung, câu hỏi
làm rõ, cây giả thuyết, metric, giới hạn, phương pháp, phạm vi) đủ để CEO duyệt hoặc sửa hướng.

## Đề bài

Bộ `online-retail-ii`, hai sheet `Year 2009-2010` và `Year 2010-2011` (trùng nhau 01–09/12/2010). Tháng 12/2011, CEO
nhắn: *"Cảm giác của tôi là khách quen không còn quay lại nhiều như trước. Tìm hiểu giúp tôi, tôi cần biết có nên dồn
ngân sách 2012 vào chương trình khách thân thiết không."* Mở `starter/baseline.ipynb`:

1. `customer_baseline(tx)`: mỗi tháng số khách hoạt động, khách mới (tháng của hoá đơn hợp lệ đầu tiên **trong dữ liệu
   được đưa vào**), khách quay lại, tỉ lệ quay lại, doanh thu khách có mã, phần doanh thu từ khách quay lại.
2. Chạy baseline trên sheet `Year 2010-2011`, rồi (cell tuỳ chọn) trên hai sheet ghép lại. So số "khách mới" hai cách
   và giải thích chênh lệch.
3. Viết `starter/ANALYSIS_PLAN.md` theo khung tám mục, 300–900 từ, mục "Giả thuyết" có ít nhất ba giả thuyết dạng gạch
   đầu dòng, mục "Dữ liệu và giới hạn" nêu con số baseline. Bài **không** yêu cầu làm hết phân tích; kế hoạch phải đủ
   rõ để người khác làm theo.

## Tiêu chí đạt

- `customer_baseline` đúng trên dữ liệu nhỏ: bỏ đơn huỷ và dòng không mã, khách có đơn đầu bị huỷ được tính mới ở
  tháng của đơn hợp lệ đầu tiên, dữ liệu cắt đầu làm khách cũ thành "mới".
- Trên sheet `Year 2010-2011`: tháng 12/2010 cả 885 khách là "mới"; tháng 11/2011 có 1 664 khách, 323 mới, 1 341 quay
  lại, khách quay lại mang 88.2% doanh thu khách có mã.
- `ANALYSIS_PLAN.md` không còn TODO, đủ tám mục theo thứ tự. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Tháng đầu của mỗi khách: `sales.groupby("Customer ID")["month"].transform("min")`. So nó với tháng của từng dòng là ra
cờ "mới". Đếm `nunique` khách theo tháng cho cả hai nhóm.

### Gợi ý 2

Trước khi viết giả thuyết, nhìn hai bảng: "khách mới" tháng 1/2011 khi chỉ dùng một sheet và khi ghép hai sheet. Rồi so
số khách mới mùa thu 2011 với mùa thu 2010. "Khách quen không quay lại" và "ít khách mới hơn" tạo ra cùng một cảm giác
cho đội sales, nhưng dẫn tới hai quyết định ngân sách khác nhau.
