# Lời giải: dashboard nhu cầu xe đạp trên Superset

## Cách làm

1. **Dataset ảo**: SQL trên `da.bike_hour` với `CAST(dteday AS DATE) AS day`, `CASE WHEN workingday = 1 THEN
   'Ngày làm việc' ELSE 'Ngày nghỉ' END AS day_type`, `CASE weathersit WHEN 1 THEN '1 · Quang, ít mây' ... END AS
   weather`, rồi `hr`, `season`, `cnt`, `casual`, `registered`. Nhãn có số thứ tự ở đầu (`1 · `, `2 · `...) để sắp
   theo chữ cũng là sắp theo mức thời tiết.
2. **Saved metric**: `SUM(cnt)`, `AVG(cnt)`, `SUM(casual) * 1.0 / NULLIF(SUM(cnt), 0)`.
3. **`upsert_dataset`**: tìm theo `table_name` bằng `rison_eq`; có thì `PUT {"sql": ...}` rồi
   `PUT /api/v1/dataset/<id>/refresh`; chưa có thì `POST`. Đọc metric hiện có, gán `id` cho metric cùng tên, `PUT
   {"metrics": [...]}`. Superset tạo sẵn metric `count` cho dataset mới; gửi danh sách metric là thay toàn bộ, nên
   `count` bị bỏ (chart không dùng nó).
4. **`chart_payloads`**: với mỗi chart, `params` = `{"viz_type", "datasource": "<id>__table", "row_limit", ...form}`,
   `query_context` = `{"datasource": {"id", "type": "table"}, "queries": [{columns, metrics, orderby, row_limit}],
   "form_data": params, "result_format": "json", "result_type": "full"}`; cả hai `json.dumps(...,
   ensure_ascii=False)`.
5. **`upsert_chart`**: tìm theo `slice_name`, `PUT` hoặc `POST`.
6. **`dashboard_layout`**: `width = 12 // per_row`; chia `chart_ids` thành từng nhóm `per_row`; dựng
   `ROOT_ID → GRID_ID → ROW-n → CHART-<id>` với `parents` là đường đi từ gốc.
7. **`upsert_dashboard`**: tìm theo `dashboard_title`, tạo nếu chưa có (`published: true`), `PUT position_json`,
   rồi `PUT /api/v1/chart/<id> {"dashboards": [dashboard_id]}` cho từng chart. Quan hệ chart-dashboard là nhiều-
   nhiều và nằm ở phía chart; chỉ đặt `position_json` thì dashboard có bố cục nhưng `GET .../charts` vẫn rỗng.

## Vì sao như vậy

- **Logic ở dataset, không ở chart**: nhãn loại ngày, nhãn thời tiết, định nghĩa tỉ trọng đặt một lần ở dataset
  ảo; mọi chart (và người dùng tự tạo chart mới) dùng chung. Đặt `CASE` trong từng chart thì sau ba tháng sẽ có
  ba cách gọi tên thời tiết.
- **Tỉ trọng là biểu thức tổng hợp**: `SUM(casual) / SUM(cnt)` tính sau khi lọc nên đúng ở mọi lát cắt (lọc mùa,
  loại ngày). `* 1.0` tránh chia nguyên trên Postgres (`bigint / bigint` ra 0), `NULLIF` tránh lỗi chia cho 0 khi
  bộ lọc không còn giờ nào.
- **`params` và `query_context`**: giao diện Explore đọc `params` (form_data) để vẽ; API `/chart/<id>/data/`, cache
  warm-up, báo cáo email chạy lại query từ `query_context`. Chart tạo bằng API mà thiếu `query_context` vẫn mở
  được trên giao diện nhưng gọi API lấy dữ liệu sẽ lỗi.
- **Refresh sau khi đổi SQL**: Superset lưu danh sách cột của dataset ảo; đổi SQL mà không refresh thì cột mới
  không hiện, cột đã bỏ vẫn còn và chart dùng nó lỗi lúc chạy.
- **Trung bình mỗi giờ, không phải tổng**: số giờ mỗi nhóm khác nhau (ngày làm việc nhiều gấp đôi ngày nghỉ; trời
  mưa lớn chỉ 3 giờ). So tổng thì nhóm có nhiều giờ luôn "thắng".

## Con số tham chiếu (Superset thật, `da.bike_hour`)

| Chart | Giá trị |
| --- | --- |
| Theo giờ, ngày làm việc | Hai đỉnh đi làm: 8h 477.0, 17h 525.3 lượt/giờ; 13h chỉ 198.4 |
| Theo giờ, ngày nghỉ | Một đỉnh giữa trưa: 13h 372.7; 8h 105.7 |
| Theo thời tiết | Quang 204.87 (11 413 giờ), sương mù 175.17 (4 544), mưa/tuyết nhẹ 111.58 (1 419), mưa lớn 74.33 (**3 giờ**) |
| Tỉ trọng khách vãng lai | 18.83% (tổng/tổng trên 17 379 giờ) |

Đọc cho trưởng điều phối: ngày làm việc cần dồn xe cho hai khung 7-9h và 16-19h ở khu văn phòng; cuối tuần dời
sang giữa trưa. Cột "mưa lớn" chỉ có 3 giờ trong hai năm: không đủ để kết luận, nên gộp vào nhóm 3 hoặc ghi rõ n
trên chart (Superset cho thêm metric `COUNT(*)` vào tooltip). Mưa/tuyết nhẹ giảm khoảng 46% so với trời quang khi
so thẳng, nhưng ngày mưa rơi nhiều vào mùa lạnh; module 08 Advanced 02 so trong cùng tháng.

## Sai lầm hay gặp

- `SUM(casual) / SUM(cnt)` không nhân 1.0: Postgres trả 0.
- Gửi metric đã có mà thiếu `id`: Superset báo trùng tên.
- Quên refresh dataset sau khi đổi SQL.
- Chỉ đặt `position_json`, không gắn chart vào dashboard (hoặc ngược lại).
- `width` tổng một hàng vượt 12: Superset tự đẩy chart xuống, bố cục khác ý định.
