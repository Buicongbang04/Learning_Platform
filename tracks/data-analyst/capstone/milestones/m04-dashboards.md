# M04: Dashboard Metabase/Superset và Streamlit

## Mục tiêu

Dựng **cùng một dashboard điều hành** bằng hai cách: một công cụ BI (Metabase hoặc Superset) cho người
dùng tự khám phá, và một app Streamlit cho trường hợp cần logic tuỳ biến. Hai bản phải ra **cùng số** vì
cùng đọc star schema và `METRICS.md` của M03. Cuối milestone bạn có một nhận định có căn cứ: với tổ chức
này, nên duy trì công cụ nào.

Kiến thức: module 10 (`10-bi-dashboards`) mục 4 (Metabase), mục 5 (Superset), mục 6 (Streamlit + Plotly),
mục 7 (thiết kế KPI dashboard). Bài gần nhất:
`modules/10-bi-dashboards/exercises/intermediate/02-metabase-sales-dashboard`,
`modules/10-bi-dashboards/exercises/intermediate/01-superset-bike-demand`,
`modules/10-bi-dashboards/exercises/basic/03-streamlit-bike-kpis`,
`modules/10-bi-dashboards/exercises/advanced/01-exec-dashboard-spec`,
`modules/10-bi-dashboards/exercises/advanced/02-self-serve-audit`.

## Việc cần làm

1. **Spec trước khi kéo thả** (`reports/DASHBOARD.md`): người dùng (Giám đốc kinh doanh, trưởng nhóm
   marketing), 3–5 câu họ hỏi mỗi tuần, KPI trả lời từng câu, bộ lọc, tần suất làm mới, và điều dashboard
   **không** trả lời. Dùng khung của bài `advanced/01-exec-dashboard-spec`.
2. **Đưa star schema tới công cụ BI**: Metabase/Superset trong `setup/` đọc Postgres
   (`docker compose -f setup/docker-compose.yml --profile bi up -d`, cổng trong `setup/.env`). Viết
   `src/dunnhumby_da/export_pg.py` đẩy các bảng mart (không phải dữ liệu thô 2,6 triệu dòng nếu không
   cần: một bảng tổng hợp theo tuần × ngành × cửa hàng là đủ cho phần lớn biểu đồ) vào schema riêng,
   ví dụ `dunnhumby`. Ghi rõ bảng nào là tổng hợp và grain của nó.
3. **Dashboard BI** (tối thiểu 6 thẻ):
   - KPI tiles: doanh thu ròng, số basket, AOV, hộ hoạt động 4 tuần, tỷ lệ giảm giá, kỳ gần nhất **đủ** so
     với kỳ trước.
   - Doanh thu theo tuần (đánh dấu tuần chưa đủ và giai đoạn nạp panel).
   - Tỷ trọng ngành hàng theo "tháng".
   - Top cửa hàng trong nhóm quy mô đã chọn ở M02.
   - Bộ lọc: khoảng tuần, ngành hàng, có/không nhân khẩu học.
4. **App Streamlit** (`dashboards/streamlit_app.py`): cùng KPI và ít nhất 3 biểu đồ trên, đọc DuckDB của
   M03 (không đọc CSV). Thêm một phần BI khó làm: ví dụ chọn một commodity rồi xem các commodity hay mua
   kèm, hoặc slider ngưỡng quy mô cửa hàng. Cache truy vấn (`st.cache_data`).
5. **Đối chiếu số**: bảng trong `DASHBOARD.md` đặt từng KPI cạnh nhau (BI, Streamlit, SQL M03) cho cùng bộ
   lọc; phải khớp tới đơn vị làm tròn. Lệch là do định nghĩa trùng lặp: sửa để cả hai đọc `METRICS.md`.
6. **So sánh công cụ** ngắn (bảng): thời gian dựng, ai sửa được, phân quyền, version control, chi phí vận
   hành, giới hạn bạn gặp. Kết luận một câu cho tổ chức giả định này.
7. Chụp màn hình hai dashboard vào `reports/img/`; xuất định nghĩa dashboard nếu công cụ cho phép
   (Metabase API / Superset export) để dựng lại được.

## Kết quả nộp

- `project/src/dunnhumby_da/export_pg.py`, `project/dashboards/streamlit_app.py`.
- `project/dashboards/bi_export/` (tệp xuất từ Metabase/Superset nếu có).
- `project/reports/DASHBOARD.md` (spec, bảng đối chiếu số, so sánh công cụ) và ảnh chụp.

## Tiêu chí đạt

- [ ] Có spec ghi người dùng, câu hỏi, KPI và điều dashboard không trả lời.
- [ ] KPI tiles so sánh kỳ đủ với kỳ đủ; tuần chưa đủ không làm KPI "giảm" giả.
- [ ] Hai dashboard ra cùng số cho cùng bộ lọc, có bảng đối chiếu.
- [ ] Streamlit đọc star schema, có cache, có ít nhất một tính năng tương tác vượt quá BI kéo thả.
- [ ] So sánh công cụ dựa trên trải nghiệm thật, kết luận rõ ràng.
- [ ] Dashboard dựng lại được từ repo (lệnh + tệp xuất), không chỉ tồn tại trong một container.
