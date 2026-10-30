---
title: Dashboard doanh số cho Head of Sales trên Metabase - KPI tháng đủ, field filter, bố cục, kiểm lưới
level: intermediate
services: [postgres, metabase]
files:
  - path: starter/kpi_dashboard.py
    note: 9 TODO - 4 SQL, bố cục, payload card, dashcards, validate_layout, upsert dashboard
  - path: tests/test_kpi_dashboard.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile bi up -d postgres metabase
  - uv run python setup/bi/load_da.py
  - uv run python setup/bi/init_bi.py
  - uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/intermediate/02-metabase-sales-dashboard/starter/kpi_dashboard.py
  - uv run pytest tracks/data-analyst/modules/10-bi-dashboards/exercises/intermediate/02-metabase-sales-dashboard -q
---

## Mục tiêu

Head of Sales mở dashboard sáng thứ Hai và hỏi: "tháng vừa rồi bán bao nhiêu, hơn hay kém tháng trước, xu
hướng thế nào, sản phẩm nào kéo doanh thu; và nếu tôi chọn Germany thì sao?". Bạn dựng dashboard 4 card trên
Metabase bằng API với các quyết định thiết kế ở phần 7 của lý thuyết: KPI dùng **tháng đủ gần nhất** (không để
tháng dở dang báo "sụt 58%"), một bộ lọc Quốc gia nối vào **mọi** card, bố cục KPI → trend → breakdown → chi
tiết, và kiểm bố cục bằng code trước khi đẩy lên.

## Đề bài

Bảng `da.online_retail_ii` như bài Basic 02 (dòng hợp lệ, cột `revenue` là doanh thu gộp; dữ liệu tới
09/12/2011 12:50). Mở `starter/kpi_dashboard.py`. Hằng `BOUNDS` (CTE `bounds` với cột `last_month`) đã có sẵn:
tháng đủ gần nhất tính trên **toàn bộ** dữ liệu, nên lọc Germany không làm mốc tháng đổi theo.

Mọi SQL là một câu `SELECT` (được dùng `WITH {BOUNDS}`), chạy được trên Postgres và DuckDB, có **field filter**
`WHERE {{country}}` (hoặc `AND {{country}}`) trên bảng **không đặt alias** (phần 4 lý thuyết giải thích vì sao),
và chỉ dùng tháng đủ. Làm tròn tiền 2 số, tỉ lệ 4 số: `ROUND(CAST(x AS NUMERIC(18, 6)), n)`.

1. **`KPI_SQL`**: một dòng `month` (= `last_month`), `revenue` (doanh thu tháng đó của nước đang lọc), `mom_pct`
   (so với tháng trước, `NULL` khi tháng trước bằng 0).
2. **`TREND_SQL`**: `month`, `revenue` theo tháng, chỉ tháng `<= last_month`, tăng dần.
3. **`TOP_PRODUCTS_SQL`**: `stockcode`, `description` (`MIN`), `revenue` của tháng `last_month`; chỉ mã **sản
   phẩm** (ký tự đầu là chữ số; bỏ `POST`, `DOT`, `M`, `BANK CHARGES`...); sắp `revenue` giảm dần rồi `stockcode`;
   10 dòng.
4. **`MONTHLY_TABLE_SQL`**: `month`, `orders` (hoá đơn khác nhau), `customers` (khách có mã khác nhau), `aov`
   (`revenue / orders`); tháng `<= last_month`; mới nhất lên đầu.
5. **`LAYOUT`**: `key -> (row, col, size_x, size_y)` trên lưới 24 cột: KPI ở góc trái trên (row 0, col 0), trend
   cùng hàng bên phải, `top_products` và `monthly_table` ở hàng dưới trend; không chồng, không tràn.
6. **`card_payload(key, ids, prefix)`**: payload `POST /api/card` cho card `key` trong `CARDS` (tên, display, SQL
   đã khai báo), `template-tags` có tag `country` kiểu `dimension` trỏ vào `["field", country_field_id, None]`,
   `widget-type` `"string/="`.
7. **`dashcards(card_ids)`**: danh sách dashcard cho `PUT /api/dashboard/<id>`: `id` âm (-1, -2...: dashcard
   mới), `card_id`, vị trí theo `LAYOUT`, `parameter_mappings` nối tham số `country` vào
   `["dimension", ["template-tag", "country"]]` của **từng** card.
8. **`validate_layout(cards)`**: danh sách lỗi (chuỗi): kích thước < 1, tràn lưới (`col < 0`, `row < 0`,
   `col + size_x > 24`), hai card chồng nhau (chỉ chạm cạnh thì không tính). Bố cục đúng trả `[]`.
9. **`upsert_dashboard(session, name, card_ids)`**: tìm dashboard chưa archive theo tên, chưa có thì
   `POST /api/dashboard` với `parameters: [PARAMETER]`; kiểm `validate_layout` (có lỗi thì `raise ValueError`);
   rồi `PUT /api/dashboard/<id>` với `parameters` và `dashcards`. Chạy lại không nhân đôi card trên dashboard.

`find_ids`, `upsert_card` (đã làm ở Basic 02) và `publish` có sẵn. Chạy script, mở dashboard, chọn Germany ở bộ
lọc Quốc gia và xem cả bốn card đổi. Test offline chạy SQL trên DuckDB bằng cách thay `{{country}}` giống
Metabase (`1 = 1` khi trống, `"da"."online_retail_ii"."country" = '...'` khi chọn); phần Metabase thật tự skip
khi chưa bật, khi chạy thì dùng tên riêng `test-<mã> · ...` và xoá khi xong.

## Tiêu chí đạt

- `KPI_SQL` chọn đúng tháng đủ (dữ liệu tới giữa tháng thì lùi một tháng; tới ngày cuối tháng thì giữ), mốc
  không đổi khi lọc nước, `mom_pct` đúng.
- Trend và bảng chi tiết bỏ tháng chưa đủ; top sản phẩm bỏ mã không phải sản phẩm; mọi card lọc được theo nước.
- `dashcards` nối bộ lọc vào mọi card; `validate_layout` bắt được chồng, tràn, kích thước 0.
- Trên Metabase thật: KPI tháng 11/2011 = 1 509 496.33 GBP, MoM +30.69% (tháng 10: 1 154 979.30); chọn Germany:
  28 025.02 GBP, MoM -11.42%; trend 24 tháng, kết thúc 11/2011; top 1 tháng 11/2011 là `23084` RABBIT NIGHT LIGHT
  (34 556.72); Germany là `22423` (1 215.30); bảng chi tiết tháng 11/2011: 2 769 hoá đơn, 1 664 khách.

## Gợi ý

### Gợi ý 1

KPI: CTE `monthly` (tháng, tổng doanh thu, có `WHERE {{country}}`), rồi
`FROM bounds b LEFT JOIN monthly cur ON cur.month = b.last_month LEFT JOIN monthly prev ON prev.month =
CAST(b.last_month - INTERVAL '1 month' AS DATE)`. `LEFT JOIN` từ `bounds` để nước không bán gì trong tháng vẫn
ra một dòng (doanh thu 0) thay vì card trống. Các SQL còn lại: `FROM da.online_retail_ii, bounds WHERE
{{country}} AND ...`.

### Gợi ý 2

Hai hình chữ nhật chồng nhau khi `a.col < b.col + b.size_x and b.col < a.col + a.size_x` và điều kiện tương tự
theo hàng; dùng `<` (không phải `<=`) để hai card chạm cạnh không bị tính là chồng. Không lọc mã sản phẩm thì
`DOT` (DOTCOM POSTAGE, 36 905.40 GBP tháng 11/2011) đứng đầu "top sản phẩm": phí ship không phải câu trả lời
Head of Sales cần.
