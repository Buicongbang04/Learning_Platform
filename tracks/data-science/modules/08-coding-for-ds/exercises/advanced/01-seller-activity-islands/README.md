---
title: Seller của Olist hoạt động liên tục bao lâu?
level: advanced
services: []
files:
  - path: starter/streaks.sql
    note: Gaps-and-islands
  - path: starter/spells.sql
    note: Đợt hoạt động cho phép nghỉ 1 tháng
  - path: starter/ANALYSIS.md
    note: Phân tích cho Seller Success
  - path: tests/test_islands.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/08-coding-for-ds/exercises/advanced/01-seller-activity-islands -q
---

## Mục tiêu

Biến kỹ thuật gaps-and-islands thành một phân tích có quyết định: định nghĩa "seller hoạt động" và
"seller rời bỏ", đo trên Olist thật, và viết khuyến nghị cho đội Seller Success. Bài kiểm cả SQL lẫn
khả năng chọn định nghĩa và bảo vệ nó.

## Đề bài

Bảng: `orders`, `order_items`. **Tháng hoạt động** của seller là tháng mua (`order_purchase_timestamp`)
có ít nhất một đơn giao xong chứa món của seller, chỉ xét đơn mua trước `2018-09-01`.

1. `starter/streaks.sql`: mỗi chuỗi tháng hoạt động **liên tiếp** của mỗi seller. Cột `seller_id`,
   `start_month`, `end_month`, `n_months`; sắp theo `seller_id`, `start_month`.
2. `starter/spells.sql`: mỗi **đợt hoạt động**, cho phép nghỉ tối đa 1 tháng ở giữa (nghỉ từ 2 tháng
   liên tiếp thì đợt kết thúc). Cột `seller_id`, `start_month`, `end_month`, `active_months` (số tháng
   có bán), `span_months` (số tháng từ đầu tới cuối đợt, tính cả hai đầu).
3. `starter/ANALYSIS.md`: phân tích cho trưởng nhóm Seller Success theo khung có sẵn: định nghĩa (và
   con số thay đổi thế nào khi đổi định nghĩa), kết quả chính, khuyến nghị (can thiệp với ai, khi nào,
   đo hiệu quả thế nào), hạn chế. Mọi con số phải đến từ query bạn chạy.

## Tiêu chí đạt

- Hai query đúng trên dữ liệu test: đơn có nhiều món của cùng seller, đơn có món của hai seller, chuỗi
  qua năm mới, đơn huỷ / chưa giao / mua sau 2018-08-31 bị loại.
- Trên Olist thật: 5 183 chuỗi của 2 970 seller, 35 seller có chuỗi 20 tháng; 3 914 đợt, 735 seller
  có hơn một đợt.
- `ANALYSIS.md` không còn TODO, ít nhất 350 từ.
- Nội dung phân tích chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`streaks.sql`: đổi tháng thành số nguyên (`DATE_DIFF('month', DATE '2000-01-01', month)`), trừ
`ROW_NUMBER() OVER (PARTITION BY seller_id ORDER BY month)`, hiệu là khoá nhóm. Nhớ `DISTINCT` trước
khi đánh số. Đừng đặt alias `months` (DuckDB coi là từ khoá).

### Gợi ý 2

`spells.sql`: `LAG(month)` lấy tháng hoạt động trước; `is_new = 1` khi khoảng cách lớn hơn 2 tháng hoặc
là dòng đầu (LAG trả NULL); `SUM(is_new) OVER (PARTITION BY seller_id ORDER BY month)` ra số thứ tự đợt.
Khi phân tích "rời bỏ", nhớ rằng dữ liệu dừng ở 2018-08: seller có tháng cuối là 2018-07 chưa thể bị
coi là đã rời bỏ (right-censoring).
