---
title: Doanh thu theo tháng, MoM/YoY và so sánh khi tháng chưa đủ ngày (DuckDB)
level: basic
services: []
files:
  - path: starter/monthly_kpis.sql
    note: 1 TODO - KPI tháng, MoM, YoY, luỹ kế năm
  - path: starter/same_period_compare.sql
    note: 1 TODO - so sánh cùng số ngày
  - path: starter/run_query.py
    note: Chạy thử SQL trên dữ liệu thật, không cần sửa
  - path: tests/test_monthly.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run python tracks/data-analyst/modules/03-sql-for-analysts/exercises/basic/01-monthly-revenue-mom/starter/run_query.py monthly_kpis.sql
  - uv run pytest tracks/data-analyst/modules/03-sql-for-analysts/exercises/basic/01-monthly-revenue-mom -q
---

## Mục tiêu

Viết bằng SQL bảng KPI tháng mà CEO hay hỏi (doanh thu, số đơn, MoM, YoY, luỹ kế năm), và biết trả lời câu
"tháng này đang kém tháng trước à?" khi tháng hiện tại mới chạy được vài ngày: so cùng số ngày, không so
tháng dở dang với tháng đủ.

## Đề bài

Test nạp bộ `online-retail-ii` (cả hai sheet, đã bỏ phần trùng 01-09/12/2010) vào bảng DuckDB
`online_retail`, giữ nguyên dữ liệu gốc (1 044 848 dòng, 01/12/2009 tới 09/12/2011 12:50):

| Cột | Kiểu | Ghi chú |
| --- | --- | --- |
| `invoice` | VARCHAR | bắt đầu bằng `C` là hoá đơn huỷ |
| `stock_code`, `description` | VARCHAR | mã và tên hàng |
| `quantity` | INTEGER | âm ở dòng huỷ / điều chỉnh |
| `invoice_date` | TIMESTAMP | có giờ phút |
| `price` | DOUBLE | GBP, có dòng giá 0 |
| `customer_id` | INTEGER | NULL là khách vãng lai |
| `country` | VARCHAR | |

Dòng hợp lệ theo định nghĩa chung của track: `invoice` không bắt đầu bằng `C`, `quantity > 0`, `price > 0`;
doanh thu dòng = `quantity * price` (doanh thu gộp). Mỗi tệp `.sql` là **một** câu `SELECT` (được dùng `WITH`).
Chạy thử trên dữ liệu thật bằng `starter/run_query.py` (lệnh ở trên).

1. **`monthly_kpis.sql`**: mỗi tháng từ tháng đầu tới tháng cuối có dữ liệu **một dòng**, kể cả tháng không
   có dòng hợp lệ nào (doanh thu 0). Cột theo thứ tự, sắp theo `month`:
   - `month`: ngày đầu tháng, kiểu `DATE`;
   - `revenue` (làm tròn 2 số), `orders` (số hoá đơn khác nhau), `active_days` (số ngày lịch có bán);
   - `mom_pct`: `revenue / revenue tháng trước - 1`, làm tròn 4 số; `NULL` ở tháng đầu **và khi tháng trước
     bằng 0**;
   - `yoy_pct`: như trên nhưng so với cùng tháng năm trước; `NULL` khi chưa có tháng đó hoặc tháng đó bằng 0;
   - `ytd_revenue`: doanh thu luỹ kế từ tháng 1 của cùng năm tới tháng này (reset mỗi năm);
   - `is_complete`: `TRUE` khi dữ liệu đã tới ngày cuối của tháng đó (ngày cuối có dữ liệu ≥ ngày cuối tháng).
2. **`same_period_compare.sql`**: đúng năm dòng, cột `period, start_date, end_date, revenue`, theo thứ tự:

   | `period` | Kỳ (tính cả `end_date`) |
   | --- | --- |
   | `mtd` | ngày 1 của tháng cuối có dữ liệu tới ngày cuối có dữ liệu |
   | `mtd_prev_month` | cùng các ngày đó ở tháng trước (tháng trước ngắn hơn thì dừng ở ngày cuối tháng) |
   | `mtd_prev_year` | cùng các ngày đó ở năm trước |
   | `ytd` | 1/1 của năm cuối tới ngày cuối có dữ liệu |
   | `ytd_prev_year` | cùng kỳ năm trước |

   Mốc cắt **lấy từ dữ liệu** (`max(invoice_date)`), không gõ cứng `2011-12-09`: test chạy cả trên dữ liệu nhỏ
   kết thúc ngày khác. Kỳ không có dòng nào có doanh thu 0.

Sau khi test pass, làm phần trắc nghiệm trong app: đọc kết quả hai truy vấn trên dữ liệu thật và trả lời câu
hỏi của CEO.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: tháng trống có mặt với 0, MoM `NULL` khi tháng trước bằng 0, YoY đúng 12 tháng,
  luỹ kế reset đầu năm, `is_complete` đúng; năm kỳ so sánh đúng ngày bắt đầu/kết thúc, kể cả tháng 2 ngắn.
- Trên bộ thật: 25 tháng; 11/2011 doanh thu 1 509 496.33 GBP, MoM +30.7%, YoY +2.7%; 12/2011 chỉ 8 ngày bán,
  `is_complete = FALSE`; luỹ kế 2011 tới 9/12 là 9 842 956.40 GBP.
- Trắc nghiệm: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Tháng liên tục: sinh "xương sống" tháng bằng `generate_series(first_month, last_month, INTERVAL 1 MONTH)`
rồi `LEFT JOIN` bảng tổng hợp vào và `coalesce(..., 0)`. Có spine thì `lag(revenue, 12)` mới chắc chắn là
cùng tháng năm trước. Chia an toàn: `revenue / NULLIF(prev, 0) - 1`.

### Gợi ý 2

`last_day(month)` cho ngày cuối tháng. Luỹ kế năm: `sum(revenue) OVER (PARTITION BY year(month) ORDER BY month)`.
Với kỳ so sánh, dựng một CTE nhỏ năm dòng (`UNION ALL`) chứa `start_date`, `end_date`, rồi `LEFT JOIN` dòng
hợp lệ theo `invoice_date::DATE BETWEEN start_date AND end_date`. `DATE - INTERVAL 1 MONTH` trong DuckDB tự kẹp
về ngày cuối tháng (30/03 thành 28/02).
