# Lời giải: app KPI Bike Sharing bằng Streamlit

## Cách làm

1. **`load_day`**: `pd.read_csv(path, parse_dates=["dteday"])`, `df["year"] = 2011 + df["yr"]`.
2. **`filter_days`**: mask `df["year"] == year`; nếu `seasons` có phần tử thì thêm `& df["season"].isin(seasons)`;
   `reset_index(drop=True)`. Danh sách rỗng và `None` cùng nghĩa "không lọc mùa" (`if seasons:`).
3. **`kpis`**: `days = len(df)`, `total = int(df["cnt"].sum())`, `per_day = total / days`, `casual_share =
   df["casual"].sum() / total`; rỗng thì hai khoá cuối `None` (không chia cho 0, không trả `nan`).
4. **`yoy`**: `None` nếu `current is None or not previous` (gồm `None` và 0), ngược lại `current / previous - 1`.
5. **`monthly`**: `month = dteday.dt.to_period("M").dt.to_timestamp()`, `groupby("month")` tổng ba cột, sắp tăng.
6. **Giao diện**: `st.columns(3)`, ba `metric` với `delta` từ `fmt_delta_pct` / `fmt_delta_pp` (hiện `"n/a"` khi
   giá trị `None`); `go.Figure` hai `add_bar` + `barmode="stack"` đưa vào `st.plotly_chart`; `nlargest(5, "cnt")`
   cho bảng drill-down; `st.caption` ghi nguồn.

## Vì sao như vậy

- **Hàm thuần tách khỏi UI**: KPI là phần dễ sai nhất và test được bằng pytest thông thường; phần `st.*` chỉ hiển
  thị. `AppTest` kiểm phần nối hai thứ (nhãn, mặc định, delta đổi khi đổi bộ lọc).
- **Tỉ trọng là tổng/tổng**: trung bình tỉ lệ từng ngày cân mỗi ngày như nhau dù ngày đông gấp mười ngày vắng.
  Trên dữ liệu nhỏ của test, năm 2012: tổng/tổng 12.5%, trung bình tỉ lệ ngày ra số khác.
- **So cùng các mùa của năm trước**: chọn mùa 1 năm 2012 thì so với mùa 1 năm 2011, không với cả năm 2011.
  Delta của tỉ trọng là **điểm phần trăm** (18.2% so với 19.9% là -1.7 điểm %), không phải -8.6%.
- **Năm đầu không có delta**: `delta=None` thì Streamlit không vẽ mũi tên. Hiện "+0%" hoặc "-100%" cho năm không có
  dữ liệu so sánh là nói sai.
- **`@st.cache_data`**: mỗi lần đổi bộ lọc, script chạy lại từ đầu; không cache thì đọc lại CSV mỗi lần. Hàm cache
  nhận `path` dạng chuỗi để Streamlit băm được tham số.
- **Nhãn mùa có khoảng ngày**: mã 1 của UCI tên `spring` nhưng là 21/12-20/3 (module 08). Hiện cả khoảng ngày
  tránh việc trưởng vận hành đọc "mùa xuân ế nhất".

## Con số tham chiếu (`day.csv` thật)

| Bộ lọc | Tổng lượt thuê | TB/ngày | Tỉ trọng vãng lai |
| --- | --- | --- | --- |
| 2012, cả 4 mùa (mặc định) | 2,049,576 (+64.9%) | 5,600 (+64.4%) | 18.2% (-1.7 điểm %) |
| 2011, cả 4 mùa | 1,243,103 (không delta) | 3,406 | 19.9% |
| 2012, mùa 3 (21/6-22/9) | 641,479 | | 20.4% (2011: 22.7%) |

Năm 2012 có 366 ngày nên tổng tăng 64.9% nhưng TB/ngày tăng 64.4%. Ngày đông nhất 2012 là 15/09/2012 (8 714 lượt,
3 160 vãng lai); bốn ngày tiếp theo: 29/09, 22/09, 23/03, 19/05/2012. Tỉ trọng vãng lai giảm dù số lượt vãng lai
tăng: thành viên tăng nhanh hơn.

## Sai lầm hay gặp

- Tính `casual_share` bằng `(df.casual / df.cnt).mean()`.
- Delta so với cả năm trước dù đang lọc mùa.
- Đọc CSV ngoài hàm cache, hoặc gọi `st.*` trong hàm KPI làm test hàm thuần lỗi.
- `selectbox` năm mặc định 2011 (phần tử đầu của danh sách tăng dần): dashboard nên mở ở kỳ mới nhất.
