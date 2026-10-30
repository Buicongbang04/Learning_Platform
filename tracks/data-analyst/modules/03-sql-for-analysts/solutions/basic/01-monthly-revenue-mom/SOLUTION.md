# Lời giải: KPI tháng, MoM/YoY và so sánh khi tháng chưa đủ ngày

> `starter/run_query.py` là helper để chạy thử SQL trên dữ liệu thật, không được chấm và không có bản lời giải: giữ nguyên.

## Cách làm

### `monthly_kpis.sql`

1. **`valid`**: lọc dòng hợp lệ một lần ở CTE đầu, mọi bước sau dùng lại. Đặt định nghĩa ở một chỗ để không
   có hai con số "doanh thu" trong cùng một truy vấn.
2. **`bounds` + `spine`**: `generate_series(first_month, last_month, INTERVAL 1 MONTH)` sinh mọi tháng.
   `GROUP BY` chỉ trả tháng **có** dữ liệu; tháng không bán gì biến mất, và khi đó `lag(revenue)` so với tháng
   cách hai tháng, `lag(revenue, 12)` lệch một tháng mà không báo lỗi. Spine là cách duy nhất để "dòng trước"
   chắc chắn là "tháng trước".
3. **`agg`**: `count(DISTINCT invoice)` là số đơn (một hoá đơn nhiều dòng), `count(DISTINCT invoice_date::DATE)`
   là số ngày bán. Đếm `count(*)` sẽ ra số **dòng**, không phải số đơn.
4. **`filled`**: `LEFT JOIN` spine với `agg`, `coalesce(..., 0)`. `is_complete = last_day(month) <= last_date`.
5. **Window**: `revenue / NULLIF(lag(revenue) OVER (ORDER BY month), 0) - 1`. `NULLIF` biến 0 thành `NULL`, nên
   tháng sau tháng 0 có MoM `NULL` (không xác định) thay vì lỗi chia cho 0 hay `inf`. Luỹ kế năm:
   `sum(revenue) OVER (PARTITION BY year(month) ORDER BY month)`; frame mặc định khi có `ORDER BY` là
   `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, đúng nghĩa luỹ kế vì mỗi tháng chỉ có một dòng.

### `same_period_compare.sql`

- Mốc cắt từ dữ liệu: `max(invoice_date)::DATE`. Gõ cứng `2011-12-09` thì truy vấn sai ngay ngày mai khi có dữ
  liệu mới (và sai trên dữ liệu test).
- Năm kỳ dựng bằng một CTE `UNION ALL`, mỗi dòng có `start_date`, `end_date` và cột thứ tự. Đây là mẫu "bảng kỳ
  so sánh" dùng lại được cho mọi báo cáo: thêm kỳ là thêm một dòng.
- `LEFT JOIN valid v ON v.d BETWEEN start_date AND end_date` với `v.d = invoice_date::DATE`. So `TIMESTAMP` với
  `DATE '2011-11-09'` thì mốc là 00:00 ngày 9, mất mọi dòng trong ngày 9; ép về `DATE` trước khi so (hoặc dùng
  khoảng nửa mở `< ngày kế tiếp`) mới lấy đủ.
- `DATE '2011-03-30' - INTERVAL 1 MONTH` trong DuckDB là `2011-02-28` (kẹp về ngày cuối tháng). PostgreSQL cũng
  vậy; nếu công cụ khác không kẹp, dùng `least(..., last_day(...))`.

## Con số trên bộ thật

| Tháng | Doanh thu (GBP) | Đơn | Ngày bán | MoM | YoY |
| --- | --- | --- | --- | --- | --- |
| 12/2010 | 823 746.14 | 1 559 | 20 | -44.0% | -0.2% |
| 04/2011 | 537 808.62 | 1 246 | 21 | -25.1% | **-21.1%** |
| 09/2011 | 1 058 590.17 | 1 837 | 26 | +39.5% | +14.5% |
| 10/2011 | 1 154 979.30 | 2 040 | 26 | +9.1% | -0.9% |
| 11/2011 | 1 509 496.33 | 2 769 | 26 | +30.7% | +2.7% |
| 12/2011 (chưa đủ) | 638 810.68 | 819 | 8 | **-57.7%** | -22.5% |

| Kỳ | Từ | Đến | Doanh thu (GBP) |
| --- | --- | --- | --- |
| `mtd` | 2011-12-01 | 2011-12-09 | 638 810.68 |
| `mtd_prev_month` | 2011-11-01 | 2011-11-09 | 454 238.30 |
| `mtd_prev_year` | 2010-12-01 | 2010-12-09 | 438 852.65 |
| `ytd` | 2011-01-01 | 2011-12-09 | 9 842 956.40 |
| `ytd_prev_year` | 2010-01-01 | 2010-12-09 | 9 480 206.26 |

## Đáp án trắc nghiệm

- **naive-mom-dec (c)**: 638 810.68 / 1 509 496.33 - 1 = -57.7%. Con số đúng về số học, sai về ý nghĩa.
- **lfl-prev-month (a)**: 638 810.68 / 454 238.30 - 1 = +40.6%. Cùng 9 ngày đầu tháng, tháng 12 cao hơn.
- **ytd-growth (d)**: 9 842 956.40 / 9 480 206.26 - 1 = +3.8%. Luỹ kế năm là cách so ít nhạy với một tháng dở
  dang nhất, vì tháng dở dang chỉ là một phần nhỏ của tổng.
- **worst-yoy (b)**: 04/2011 -21.1% (một phần do lịch: Phục sinh và ngày nghỉ lễ, chỉ 21 ngày bán so với 23).
  12/2011 có YoY -22.5% thấp hơn nhưng là tháng chưa đủ, nên bị loại bởi điều kiện `is_complete`.
- **ceo-answer (a)**: tháng 12 mới có 8 ngày bán (dữ liệu tới 12:50 ngày 9/12). So cùng 9 ngày đầu tháng: +40.6%
  so với tháng 11, +45.6% so với cùng kỳ năm trước. Phương án "tháng 12 năm nào cũng cao điểm" đúng một phần (mùa vụ) nhưng không trả lời cách
  đo; "phải đợi hết tháng" bỏ lỡ việc so sánh công bằng làm được ngay. Lưu ý thêm: con số +45.6% là doanh thu **gộp**, trong
  đó có một hoá đơn 168 nghìn GBP bị huỷ 12 phút sau (xem module 08, bài Advanced 01). Bài sau về reconcile sẽ
  luyện thói quen kiểm con số trước khi gửi.
- **nullif-why (d)**: trong DuckDB 2.0 phép `/` trả `inf` khi chia số khác 0 cho 0 và `nan` khi `0 / 0`;
  PostgreSQL báo lỗi "division by zero". `NULLIF` làm hành vi rõ ràng và giống nhau ở mọi engine: `NULL` nghĩa là
  "không xác định", và các hàm tổng hợp bỏ qua nó thay vì bị `inf` làm hỏng.
- **lag-needs-spine (b)**: không có dòng 02/2011 thì từ 05/2011 lùi 12 **dòng** rơi vào 04/2010. LAG đếm dòng,
  không đếm tháng; truy vấn không báo lỗi, chỉ ra số sai.
- **inclusive-end (c)**: khoảng nửa mở `>= ngày đầu AND < ngày sau ngày cuối` đúng với mọi kiểu thời gian.
  Hai phương án dùng `BETWEEN` và `<=` so TIMESTAMP với `'2011-11-09'` tức 00:00 ngày 9, mất cả ngày 9; `date_trunc` lấy cả tháng 11.

## Sai lầm hay gặp

- `GROUP BY` rồi `LAG` mà không có spine: chạy đúng trên dữ liệu đầy đủ, sai lặng lẽ khi có tháng trống.
- Tính YoY bằng `lag(revenue, 12)` trên bảng theo **ngày**: 12 dòng là 12 ngày.
- Báo MoM của tháng đang chạy trên dashboard không kèm cờ "chưa đủ": người đọc thấy -58% và hoảng.
