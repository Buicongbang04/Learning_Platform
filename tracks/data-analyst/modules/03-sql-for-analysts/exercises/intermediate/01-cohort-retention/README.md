---
title: Cohort retention theo tháng bằng SQL - ma trận long và bảng tóm tắt cho slide
level: intermediate
services: []
files:
  - path: starter/cohort_retention.sql
    note: 1 TODO - ma trận cohort dạng long
  - path: starter/retention_summary.sql
    note: 1 TODO - m1/m3/m6/m12, NULL khi chưa quan sát được
  - path: starter/run_query.py
    note: Chạy thử SQL trên dữ liệu thật, không cần sửa
  - path: tests/test_cohort.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run python tracks/data-analyst/modules/03-sql-for-analysts/exercises/intermediate/01-cohort-retention/starter/run_query.py cohort_retention.sql --rows 30
  - uv run pytest tracks/data-analyst/modules/03-sql-for-analysts/exercises/intermediate/01-cohort-retention -q
---

## Mục tiêu

Head of CRM hỏi: **"Khách mới của mình có quay lại không, và các cohort gần đây có tốt hơn trước không?"**.
Bài này dựng câu trả lời hoàn toàn bằng SQL: ma trận cohort dạng long (để vẽ heatmap hoặc nạp vào BI) và bảng
tóm tắt dạng wide (để đặt lên slide), với ba chi tiết hay làm sai: tháng chưa đủ, ô "chưa quan sát được"
khác ô "không ai quay lại", và cohort đầu tiên bị cắt trái.

## Đề bài

Bảng `online_retail` như các bài trước (hai sheet, dữ liệu gốc). Định nghĩa dùng chung của track:

- **Khách**: `customer_id` khác NULL, chỉ tính dòng hợp lệ (không `C`, `quantity > 0`, `price > 0`).
- **Cohort** của khách = tháng (ngày 1) của dòng hợp lệ đầu tiên của khách trên **toàn bộ dữ liệu**.
- **Retention tháng k** = số khách của cohort có ít nhất một dòng hợp lệ ở tháng thứ k sau tháng cohort, chia
  cho cỡ cohort (k = 0 luôn là 1).
- **Tháng đủ cuối cùng**: tháng chứa ngày cuối có dữ liệu nếu ngày đó là ngày cuối tháng, ngược lại là tháng
  liền trước (bộ thật: 11/2011). Không tính hoạt động và không tạo cohort ở tháng sau tháng này. Lấy mốc từ dữ
  liệu, không gõ cứng.

1. **`cohort_retention.sql`**: mỗi cohort (từ cohort đầu tới tháng đủ cuối cùng) có một dòng cho **mọi** `k`
   từ 0 tới tháng đủ cuối cùng, kể cả `k` không ai quay lại (`active_customers = 0`). Cột: `cohort_month` (DATE),
   `month_number` (k), `cohort_size`, `active_customers`, `retention` (làm tròn 4). Sắp theo `cohort_month,
   month_number`.
2. **`retention_summary.sql`**: mỗi cohort một dòng, cột `cohort_month, cohort_size, m1, m3, m6, m12` là
   retention tháng 1, 3, 6, 12 (làm tròn 4). Ô mà tháng `cohort_month + k` **sau** tháng đủ cuối cùng là `NULL`
   (chưa quan sát được); ô quan sát được mà không ai quay lại là `0`.

Sau khi test pass, chạy hai truy vấn trên bộ thật bằng `run_query.py`, (tuỳ chọn) vẽ heatmap từ kết quả long, rồi
làm phần trắc nghiệm trong app.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: cohort tính theo lần mua hợp lệ đầu (đơn huỷ và giá 0 không tính), khách mua
  nhiều lần trong tháng đếm một lần, ô 0 có mặt, tháng chưa đủ bị loại, `NULL` khác `0` trong bảng tóm tắt.
- Trên bộ thật: 24 cohort (12/2009 tới 11/2011), 300 dòng long, tổng cỡ cohort 5 850; cohort 12/2009 có 955
  khách, retention tháng 1 là 35.3%; cohort 10/2011 có m1 32.1%, m3 `NULL`.
- Trắc nghiệm: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Ba CTE nền: `first_month` (`min(month)` theo khách), `activity` (`SELECT DISTINCT customer_id, cohort_month,
date_diff('month', cohort_month, month)`), và `last_complete`. Đếm khách active theo `(cohort_month, k)` rồi
chia cho cỡ cohort. Thiếu `DISTINCT` thì khách mua ba lần trong tháng được đếm ba lần.

### Gợi ý 2

Để ô 0 có mặt: dựng lưới `(cohort, k)` bằng `generate_series(0, date_diff('month', cohort_month, last_m))` rồi
`LEFT JOIN` số đếm vào, `coalesce(..., 0)`. Bảng wide: `count(DISTINCT customer_id) FILTER (WHERE k = 3)` cho từng
cột, bọc trong `CASE WHEN cohort_month + INTERVAL 3 MONTH <= last_m THEN ... END` để ô chưa quan sát được thành
`NULL`.
