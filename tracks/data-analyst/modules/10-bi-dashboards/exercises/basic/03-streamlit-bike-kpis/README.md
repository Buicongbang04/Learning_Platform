---
title: App KPI Bike Sharing bằng Streamlit + Plotly, chấm bằng AppTest
level: basic
services: []
files:
  - path: starter/app.py
    note: 5 hàm TODO + 3 TODO giao diện trong main()
  - path: tests/test_app.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run streamlit run tracks/data-analyst/modules/10-bi-dashboards/exercises/basic/03-streamlit-bike-kpis/starter/app.py
  - uv run pytest tracks/data-analyst/modules/10-bi-dashboards/exercises/basic/03-streamlit-bike-kpis -q
---

## Mục tiêu

Dựng một app KPI nhỏ cho trưởng vận hành Capital Bikeshare bằng Streamlit + Plotly, theo đúng khuôn của một
KPI dashboard: bộ lọc ở sidebar, hàng KPI tile có so cùng kỳ, trend theo tháng, bảng drill-down. Làm xong bạn biết
tách logic KPI thành hàm thuần để test, dùng `@st.cache_data` cho phần đọc dữ liệu, và test giao diện bằng
`streamlit.testing.v1.AppTest` không cần trình duyệt.

## Đề bài

Dữ liệu: `data/raw/bike-sharing-uci/day.csv` (731 ngày, 01/01/2011 tới 31/12/2012; `yr` = 0 là 2011; `casual` là
khách vãng lai, `registered` là thành viên, `cnt = casual + registered`). App đọc đường dẫn từ biến môi trường
`BIKE_DAY_CSV` nếu có (test dùng cách này để đưa dữ liệu nhỏ vào).

Trưởng vận hành hỏi: "năm nay, trong các mùa tôi chọn, lượt thuê và tỉ trọng khách vãng lai so với cùng kỳ năm
trước thế nào; ngày nào đông nhất để tôi xem lại đã đủ xe chưa?". Mở `starter/app.py`.

**Hàm thuần** (không gọi `st.*`, test gọi trực tiếp):

1. `load_day(path)`: đọc CSV, `dteday` kiểu ngày, thêm cột `year = 2011 + yr`.
2. `filter_days(df, year, seasons)`: lọc theo năm và danh sách mã mùa; `seasons` rỗng hoặc `None` thì không lọc
   mùa; index đánh lại từ 0.
3. `kpis(df)`: `{"days", "total", "per_day", "casual_share"}`; `casual_share` = **tổng** `casual` / **tổng**
   `cnt` (không phải trung bình tỉ lệ từng ngày, xem phần 2 của lý thuyết). Không có ngày nào: `days = 0`,
   `total = 0`, hai khoá còn lại `None`.
4. `yoy(current, previous)`: `current / previous - 1`; `None` khi một trong hai là `None` hoặc `previous` bằng 0.
5. `monthly(df)`: cột `month` (Timestamp ngày đầu tháng), `casual`, `registered`, `cnt` (tổng theo tháng), sắp
   theo `month`.

**Giao diện** trong `main()` (sidebar và phần tính `cur`, `prev` đã có sẵn):

- Sidebar: selectbox `Năm` (mặc định 2012), multiselect `Mùa` (mặc định cả 4 mùa; nhãn trong `SEASONS` ghi cả
  khoảng ngày vì mã 1 của UCI tên `spring` nhưng thực tế là 21/12-20/3).
- Ba `st.metric` trên một hàng (`st.columns(3)`), đúng nhãn và định dạng:

  | Nhãn | Giá trị | Delta (so với **cùng các mùa** năm trước) |
  | --- | --- | --- |
  | `Tổng lượt thuê` | `f"{total:,}"` | `fmt_delta_pct(yoy(...))`, ví dụ `+64.9%` |
  | `Lượt thuê TB/ngày` | `f"{per_day:,.0f}"` | `fmt_delta_pct(yoy(...))` |
  | `Tỉ trọng khách vãng lai` | `f"{share:.1%}"` | `fmt_delta_pp(...)`, ví dụ `-1.7 điểm %` |

  Năm 2011 không có năm trước: delta là `None` (Streamlit không hiện mũi tên). Tỉ trọng so bằng **điểm phần
  trăm**, không phải phần trăm của phần trăm.
- Một `st.plotly_chart`: stacked bar theo tháng (`registered` + `casual`) của phần dữ liệu đã lọc.
- `st.subheader("5 ngày đông nhất")` rồi `st.dataframe` 5 ngày `cnt` cao nhất, sắp giảm dần, cột `dteday`,
  `cnt`, `casual`, `registered`, `weathersit`, `temp`; cuối cùng `st.caption` ghi nguồn dữ liệu.

Chạy app bằng lệnh thứ hai ở trên, đổi năm và mùa để xem số đổi.

## Tiêu chí đạt

- Năm hàm thuần đúng trên dữ liệu nhỏ (gồm trường hợp rỗng và năm đầu không có năm trước).
- `AppTest`: sidebar đúng nhãn và mặc định, ba metric đúng nhãn/giá trị/delta, một plotly chart, bảng 5 ngày sắp
  giảm dần; đổi bộ lọc thì metric đổi theo, năm 2011 không có delta; app không lỗi.
- Trên bộ thật, mặc định (2012, cả 4 mùa): `Tổng lượt thuê` 2,049,576 (+64.9%), `Lượt thuê TB/ngày` 5,600
  (+64.4%), `Tỉ trọng khách vãng lai` 18.2% (-1.7 điểm %); ngày đông nhất 15/09/2012 (8 714 lượt).

## Gợi ý

### Gợi ý 1

Mỗi lần người dùng đổi bộ lọc, Streamlit chạy lại cả script: đọc CSV trong hàm có `@st.cache_data` (đã có sẵn
`cached`). Tính KPI năm trước bằng chính `filter_days(df, year - 1, seasons)` để delta so **cùng các mùa**, không
so với cả năm trước.

### Gợi ý 2

`c1, c2, c3 = st.columns(3)` rồi `c1.metric(label, value, delta=...)`. Với tháng: `df["dteday"].dt.to_period("M")
.dt.to_timestamp()`. Với biểu đồ: `go.Figure()`, hai lần `add_bar(...)`, `update_layout(barmode="stack")`. Khi
test báo lỗi trong app, chạy `uv run streamlit run ...` để xem traceback đầy đủ trên trình duyệt.
