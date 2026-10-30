---
title: Hai question doanh thu trên Metabase tạo bằng API (SQL và query builder)
level: basic
services: [postgres, metabase]
files:
  - path: starter/metabase_questions.py
    note: 4 TODO - tra id bảng/cột, payload SQL, payload MBQL, upsert
  - path: tests/test_metabase_questions.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile bi up -d postgres metabase
  - uv run python setup/bi/load_da.py
  - uv run python setup/bi/init_bi.py
  - uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/basic/02-metabase-revenue-questions/starter/metabase_questions.py
  - uv run pytest tracks/data-analyst/modules/10-bi-dashboards/exercises/basic/02-metabase-revenue-questions -q
---

## Mục tiêu

Dựng hai question mà team Sales hỏi nhiều nhất ("doanh thu tháng này thế nào?", "nước nào mua nhiều nhất?") trên
Metabase **bằng code**: một question native SQL và một question query builder (MBQL), chạy lại bao nhiêu lần cũng
không sinh bản trùng. Làm xong bạn hiểu Metabase là một REST API, biết khi nào dùng SQL, khi nào dùng query
builder, và vì sao script dựng dashboard phải idempotent.

## Đề bài

Bảng `da.online_retail_ii` trong Postgres (database `de` của Metabase) chứa 1 019 654 dòng hợp lệ của Online
Retail II (đã bỏ hoá đơn huỷ, `quantity <= 0`, `price <= 0`, phần trùng hai sheet), từ 01/12/2009 tới
09/12/2011 12:50. Cột: `invoice`, `stockcode`, `description`, `quantity`, `invoicedate` (timestamp), `price`,
`customer_id` (NULL là khách vãng lai), `country`, `revenue` (`quantity * price`, doanh thu gộp).

Mở `starter/metabase_questions.py`. Mọi hàm nhận `session` là `requests.Session` của `setup/bi/clients.py`
(gọi bằng đường dẫn tương đối `/api/...`). Viết bốn hàm:

1. **`find_table(session)`**: trả `{"database_id", "table_id", "fields": {tên cột: id cột}}` của
   `da.online_retail_ii`. Endpoint `GET /api/database` (danh sách nằm trong khoá `data`) và
   `GET /api/database/<id>/metadata`. Bảng cùng tên có thể nằm ở schema khác: lọc theo **cả** schema và tên.
2. **`monthly_revenue_card(database_id, name)`**: payload `POST /api/card` cho question native SQL, `display`
   `"line"`. SQL trả 5 cột theo thứ tự, sắp theo `month`:
   - `month`: ngày đầu tháng, kiểu `DATE`;
   - `revenue`: tổng `revenue`, làm tròn 2 số;
   - `orders`: số hoá đơn khác nhau (bảng có grain **dòng hàng**, không phải hoá đơn);
   - `customers`: số khách có mã khác nhau (khách vãng lai không tính);
   - `aov`: `revenue / orders`, làm tròn 2 số.

   Viết SQL chạy được trên cả Postgres và DuckDB (test chạy trên DuckDB): `CAST(... AS DATE)`,
   `ROUND(CAST(x AS NUMERIC), 2)` thay vì cú pháp `::` riêng của Postgres.
3. **`country_revenue_card(ids, name)`**: payload question **query builder** (`dataset_query.type = "query"`),
   `display` `"row"`: `source-table` là id bảng; tổng `revenue` (`["sum", ["field", id, None]]`); nhóm theo
   `country`; sắp giảm dần theo phép tổng hợp đầu tiên (`["desc", ["aggregation", 0]]`); `limit` 10.
4. **`upsert_card(session, card)`**: `GET /api/card`; nếu có card **chưa archive** cùng tên thì
   `PUT /api/card/<id>` và trả id đó, chưa có thì `POST /api/card` và trả id mới.

`publish()` đã viết sẵn: tạo hai question tên bắt đầu bằng `DA10 · `. Chạy script (lệnh thứ tư ở trên) rồi mở
link in ra để xem question trên giao diện. Thử click một cột của question "Top 10 quốc gia" (drill-through) và
làm tương tự với question SQL để thấy khác biệt.

Test chạy hai phần: phần **offline** (Metabase giả trong bộ nhớ + DuckDB) luôn chạy; phần **Metabase thật** tự
skip khi chưa bật BI, khi chạy thì tạo question với tên riêng `test-<mã> · ...` và xoá sau khi xong.

## Tiêu chí đạt

- `find_table` lấy đúng bảng trong schema `da` dù schema khác có bảng cùng tên.
- SQL đúng trên dữ liệu nhỏ: `orders` đếm hoá đơn khác nhau, `customers` bỏ NULL, `month` kiểu DATE.
- Question query builder là MBQL đúng cấu trúc (không phải SQL).
- `upsert_card` chạy hai lần không tạo card trùng; card trùng tên đã archive không tính; không đụng card khác.
- Trên Metabase thật: 25 tháng, tổng doanh thu 20 533 741.92 GBP; tháng 11/2011 doanh thu 1 509 496.33 GBP,
  2 769 hoá đơn, 1 664 khách, AOV 545.14; top 4 nước United Kingdom (17 465 896.34), EIRE, Netherlands,
  Germany.

## Gợi ý

### Gợi ý 1

Mở http://localhost:3000, tạo thử một question bằng giao diện rồi mở DevTools (tab Network) xem trình duyệt gửi
gì lên `POST /api/card`: payload của bạn chỉ cần các khoá `name`, `display`, `visualization_settings`,
`dataset_query` (thêm `description` thì tốt hơn: ghi định nghĩa doanh thu và ghi chú tháng 12/2011 chưa đủ).

### Gợi ý 2

`orders` là `COUNT(DISTINCT invoice)`, `customers` là `COUNT(DISTINCT customer_id)` (COUNT bỏ NULL sẵn).
`month` là `CAST(date_trunc('month', invoicedate) AS DATE)`. Trong `upsert_card`, lọc
`c["name"] == card["name"] and not c.get("archived")`, rồi gọi `raise_for_status()` sau mỗi `POST`/`PUT` để lỗi
API không bị nuốt.
