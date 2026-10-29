# M09: Dashboard vận hành trên Metabase

## Mục tiêu

Phục vụ dữ liệu cho người dùng cuối: dashboard Metabase cho đội vận hành và kinh doanh, một app
Streamlit nhỏ cho trạng thái đơn gần thời gian thực, và một luồng Reverse ETL đơn giản. Dashboard chạy trên
Olist và NYC TLC **thật** và là phần "dashboard xem trên trình duyệt" của
[bài nộp cuối](../README.md) (mục Bài nộp cuối).

## Việc cần làm

1. Bật Metabase:

   ```bash
   docker compose -f setup/docker-compose.yml up -d postgres metabase
   # http://localhost:3000 → tạo tài khoản admin lần đầu
   ```

   Thêm database: host `postgres` (tên service trong mạng Docker), port `5432`, db `de`,
   user `analyst` (role chỉ đọc từ M08; nếu chưa có thì dùng `de`).
2. Tạo **serving layer**: view/materialized view `mart.*` trong Postgres cho dashboard
   (vd. `mart.revenue_daily`, `mart.seller_scorecard`, `mart.delivery_sla`), refresh trong DAG M05.
   Lưu SQL ở `project/models/mart/`.
3. Dashboard "Olist Operations" gồm ít nhất:
   - KPI: GMV tháng này, số đơn, AOV, tỉ lệ giao trễ, điểm review trung bình (so với tháng trước).
   - Line chart doanh thu theo ngày; bản đồ/bar doanh thu theo bang.
   - Bảng top seller trễ hạn (filter theo bang, danh mục).
   - Funnel trạng thái đơn từ `stream.order_status_live` (M07), auto-refresh 1 phút.
   - Điểm review theo nhóm trễ hạn (insight chính của notebook khám phá).
   - Filter dashboard: khoảng ngày, bang, danh mục.

   Thêm một tab/dashboard "NYC Taxi" đọc gold `nyc_zone_daily` của M06 (qua DuckDB hoặc nạp vào `mart.nyc_zone_daily`):
   chuyến theo ngày, top zone đón khách, tỉ lệ tip theo borough. Dữ liệu Olist dừng ở 2018 nên "tháng này" là
   tháng gần nhất có dữ liệu đủ (08/2018), không phải tháng hiện tại.
4. App Streamlit `project/dashboards/app.py`: trạng thái đơn live và tra cứu một `order_id`
   (đọc Postgres, cache bằng `st.cache_data(ttl=30)`).

   ```bash
   uv run streamlit run tracks/data-engineer/capstone/project/dashboards/app.py
   ```

5. **Reverse ETL**: script `project/dashboards/reverse_etl.py` xuất danh sách khách có review
   1–2 sao trong 7 ngày (đã mask, xem M10) thành CSV/JSON "gửi" cho đội CSKH (giả lập API bằng
   ghi tệp hoặc POST tới `httpbin`), idempotent theo ngày.
6. Export dashboard: dùng Metabase API (`GET /api/dashboard/:id`) lưu JSON vào
   `project/dashboards/metabase/`, và chụp ảnh màn hình.

## Kết quả nộp

- `project/models/mart/*.sql`, `project/dashboards/app.py`, `project/dashboards/reverse_etl.py`
- `project/dashboards/metabase/*.json` và ảnh dashboard trong README.

## Tiêu chí đạt

- [ ] Dashboard mở được trên trình duyệt (Metabase `http://localhost:3000` hoặc Streamlit `http://localhost:8501`) và
  chạy trên dữ liệu thật, không phải bộ giả lập.
- [ ] Dashboard trả lời được 4 câu hỏi kinh doanh Olist trong capstone README, và có ít nhất một card NYC TLC.
- [ ] Mỗi card đọc từ `mart.*`/gold, không join bảng `raw` trực tiếp; mỗi card tải < 2 giây.
- [ ] Số GMV trên dashboard khớp truy vấn SQL kiểm tra trên `dw`; tỉ lệ trễ và điểm review đúng hạn/trễ khớp
  `notebooks/report.md` (cùng định nghĩa).
- [ ] Ảnh dashboard có trong README portfolio.
- [ ] Funnel trạng thái đổi khi producer M07 đang chạy.
- [ ] Metabase kết nối bằng user chỉ đọc.
- [ ] Reverse ETL chạy lại cùng ngày không gửi trùng.
