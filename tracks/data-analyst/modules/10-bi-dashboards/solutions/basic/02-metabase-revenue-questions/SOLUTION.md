# Lời giải: hai question doanh thu trên Metabase

## Cách làm

1. **`find_table`**: `GET /api/database` (bản Metabase mới trả `{"data": [...], "total": n}`; viết
   `dbs["data"] if isinstance(dbs, dict) else dbs` để chạy được cả bản cũ trả list), lấy database tên `de`, rồi
   `GET /api/database/<id>/metadata` và chọn bảng có **cả** `schema == "da"` và `name == "online_retail_ii"`. Không
   tìm thấy thì `LookupError` kèm lệnh cần chạy (`init_bi.py`, `load_da.py`), để người dùng biết sửa gì.
2. **`monthly_revenue_card`**: payload `display: "line"`, `dataset_query.type = "native"`, SQL:

   ```sql
   SELECT CAST(date_trunc('month', invoicedate) AS DATE) AS month,
          ROUND(CAST(SUM(revenue) AS NUMERIC), 2) AS revenue,
          COUNT(DISTINCT invoice) AS orders,
          COUNT(DISTINCT customer_id) AS customers,
          ROUND(CAST(SUM(revenue) / COUNT(DISTINCT invoice) AS NUMERIC), 2) AS aov
   FROM da.online_retail_ii
   GROUP BY 1
   ORDER BY 1
   ```

   Thêm `description` ghi định nghĩa doanh thu và "tháng 12/2011 chỉ có dữ liệu tới ngày 9", và
   `visualization_settings` chọn `month` làm trục, `revenue` làm đường.
3. **`country_revenue_card`**: MBQL `{"source-table", "aggregation": [["sum", ["field", id_revenue, None]]],
   "breakout": [["field", id_country, None]], "order-by": [["desc", ["aggregation", 0]]], "limit": 10}`,
   `display: "row"` (bar ngang, nhãn nước dễ đọc).
4. **`upsert_card`**: lọc `GET /api/card` theo tên và `not archived`; có thì `PUT /api/card/<id>` với cả payload,
   chưa có thì `POST`. `raise_for_status()` sau mỗi lần ghi.

## Vì sao như vậy

- **Grain dòng hàng**: một hoá đơn có nhiều dòng, nên `COUNT(*)` đếm dòng hàng, không phải đơn. Tháng 11/2011 có
  2 769 hoá đơn nhưng 83 369 dòng; AOV tính bằng `COUNT(*)` ra 18.11 GBP thay vì 545.14, nhỏ hơn khoảng 30 lần.
- **`COUNT(DISTINCT customer_id)` bỏ NULL sẵn**: khách vãng lai không có mã, không tính là khách. Doanh thu của họ
  vẫn nằm trong `revenue` và `orders`; ghi rõ điều này nếu đặt "doanh thu mỗi khách" lên dashboard.
- **SQL native hay query builder**: question tháng cần 5 cột tính trong một câu (đếm distinct, chia), viết SQL gọn
  hơn; question top nước dựng được bằng builder, và builder cho drill-through (click United Kingdom để xem theo
  tháng, theo sản phẩm). Câu nào dựng được bằng builder thì ưu tiên builder: người khác sửa được, Metabase hiểu
  ngữ nghĩa cột.
- **Lọc theo schema**: kho Metabase thật thường có cùng tên bảng ở `public`, `staging`, `mart`. Lấy nhầm bảng thì
  question vẫn chạy, chỉ là số sai, lỗi khó thấy nhất.
- **Idempotent**: script dựng dashboard sẽ được chạy lại (sửa SQL, deploy môi trường mới). Không upsert thì mỗi lần
  chạy thêm một bản trùng, đúng loại rác mà bài Advanced 02 phải dọn. Card đã archive không tính là có sẵn: tạo
  mới thay vì sửa một card người khác đã bỏ.

## Con số tham chiếu (Metabase thật, `da.online_retail_ii`)

| Đại lượng | Giá trị |
| --- | --- |
| Số tháng | 25 (12/2009 tới 12/2011; tháng 12/2011 chỉ tới ngày 9) |
| Tổng doanh thu gộp | 20 533 741.92 GBP |
| Tháng 11/2011 | 1 509 496.33 GBP, 2 769 hoá đơn, 1 664 khách, AOV 545.14 |
| Tháng 12/2011 (dở dang) | 638 810.68 GBP, tức "giảm 58%" nếu đọc ngây thơ |
| Top nước | United Kingdom 17 465 896.34 (85% tổng), EIRE 659 149.00, Netherlands 554 039.74, Germany 425 578.38 |

United Kingdom chiếm 85% doanh thu: row chart top 10 nước cho thấy ngay một thị trường áp đảo. Nếu câu hỏi là
"thị trường nước ngoài nào đáng đầu tư", question tiếp theo nên bỏ UK hoặc vẽ riêng.

## Sai lầm hay gặp

- Lấy bảng đầu tiên có tên `online_retail_ii` mà không xét schema.
- `COUNT(invoice)` thay vì `COUNT(DISTINCT invoice)`.
- Dùng cú pháp `::numeric` của Postgres: chạy trên Metabase nhưng test DuckDB không chạy (và khó chuyển warehouse).
- `upsert_card` so tên nhưng quên `archived`, hoặc `POST` mỗi lần chạy.
