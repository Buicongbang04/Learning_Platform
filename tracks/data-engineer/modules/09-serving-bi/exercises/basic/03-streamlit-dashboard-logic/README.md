---
title: Tách logic dashboard Streamlit để test được
level: basic
services: []
files:
  - path: starter/dashboard_logic.py
    note: 6 TODO
  - path: starter/app.py
    note: UI Streamlit đã viết sẵn, chỉ đọc và chạy thử
  - path: tests/test_dashboard_logic.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/basic/03-streamlit-dashboard-logic -q
  - uv run streamlit run tracks/data-engineer/modules/09-serving-bi/exercises/basic/03-streamlit-dashboard-logic/starter/app.py
---

## Mục tiêu

Viết phần logic của một dashboard vận hành (lọc, KPI, % thay đổi, chuỗi thời gian, format tiền, trạng thái màu)
thành các hàm thuần Python có unit test, để `app.py` của Streamlit chỉ còn nhiệm vụ vẽ.

## Đề bài

`starter/app.py` đã dựng sẵn giao diện: sidebar chọn khoảng ngày và state, 4 KPI tile có so sánh với kỳ trước,
biểu đồ theo ngày. Nó gọi các hàm trong `starter/dashboard_logic.py`, bạn cần viết:

1. `filter_orders(df, start, end, states=None)`: lọc `order_date` trong `[start, end]` (cả hai đầu, nhận chuỗi hoặc
   `date`) và theo danh sách state (None hoặc rỗng là lấy hết). Trả DataFrame mới, index từ 0.
2. `compute_kpis(df)`: `orders`, `revenue`, `aov`, `late_rate`. `late_rate` tính trên **đơn** delivered, không trên
   dòng item. Không có đơn thì `aov = 0.0`; không có đơn delivered thì `late_rate = None`.
3. `pct_change(current, previous)`: % thay đổi làm tròn 1 chữ số; `None` khi kỳ trước là 0 hoặc None.
4. `daily_series(df, start, end)`: đủ mọi ngày trong khoảng, ngày trống điền 0 (biểu đồ line không bị nối tắt qua
   ngày không có đơn).
5. `format_brl(value)`: `1234.5` → `"R$ 1.234,50"`, số âm có dấu `-` trước `R$`, `None` → `"n/a"`.
6. `kpi_status(value, target, higher_is_better=True, warn_margin=0.1)`: `ok`, `warn`, `bad` hoặc `unknown`.

Chi tiết đầu vào/đầu ra ở docstring từng hàm và trong test.

## Tiêu chí đạt

- 7 test pass, không cần mở trình duyệt.
- `dashboard_logic.py` không import `streamlit`.
- Chạy `uv run streamlit run …/starter/app.py` hiện dashboard không lỗi.

## Gợi ý

### Gợi ý 1

`Series.between(start, end)` đã bao cả hai đầu. Chuyển `start`, `end` sang `pd.Timestamp` trước khi so sánh. Với
`late_rate`, lấy các dòng delivered rồi `drop_duplicates("order_id")` để đưa về grain đơn hàng, sau đó
`is_late.mean()`.

### Gợi ý 2

Chuỗi ngày đầy đủ: `pd.date_range(start, end, freq="D")` rồi `groupby("order_date").agg(...)` và
`.reindex(days, fill_value=0)`. Định dạng kiểu Brazil: format `f"{x:,.2f}"` ra `1,234.50`, rồi đổi `,` và `.` cho nhau
qua một ký tự trung gian.
