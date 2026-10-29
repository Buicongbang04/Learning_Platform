# Báo cáo: động đất M≥4.5 toàn cầu năm 2024 (USGS)

## Bộ dữ liệu

- API USGS FDSN Event Web Service (`earthquake.usgs.gov/fdsnws/event/1/query`), public domain, không cần key.
- Tham số ghim: `minmagnitude=4.5`, `starttime=2024-01-01`, `endtime=2025-01-01`, `orderby=time-asc`, `format=geojson`,
  trang 1 000 bản ghi.
- Lượt 1 (full): 7 trang, 6 397 trận, ~5,0 MB JSON thô. Lượt 2 (incremental, `updatedafter` = watermark): 1 trang,
  1 bản ghi (chính bản ghi nằm đúng ở watermark, vì `updatedafter` tính cả mốc bằng).
- Mỗi bản ghi: `id`, `time`, `updated` (ms epoch), magnitude và loại, `place`, toạ độ và độ sâu, cờ tsunami, `status`.

## Làm sạch

- Gộp mọi `run-*/page-*.json`, upsert theo `id` giữ bản có `updated` lớn nhất: kết quả 6 397 dòng, `id` không trùng
  (bản ghi lấy lại ở lượt 2 không bị nhân đôi).
- `time`, `updated` từ mili giây epoch sang datetime UTC. `region` tách từ `place` ("15 km S of Hualien City, Taiwan"
  → "Taiwan"), bỏ đuôi " Earthquake" của tên sự kiện đặt riêng.
- Không lọc thêm: mọi bản ghi đều `type = earthquake`, `status = reviewed`, `mag ≥ 4.5`.
- Kết quả: `data/clean/usgs-earthquakes/events.parquet`, 6 397 dòng, 0,36 MB (từ 5 MB JSON).

## Insight

1. **Bản ghi bị sửa rất muộn, nên watermark phải theo `updated`**: trung vị `updated - time` là **70,8 ngày**,
   **100%** bản ghi được sửa sau hơn 30 ngày, 1% sau hơn 715 ngày; 89 trận năm 2024 còn được sửa trong năm 2026.
   Watermark theo `time` sẽ bỏ sót toàn bộ các bản sửa này (magnitude, vị trí, độ sâu thay đổi sau khi
   chuyên gia review). Với `updatedafter`, lượt chạy hằng đêm chỉ tốn **1 request** thay vì 7 của lần full.
2. **Trận lớn nhất mở đầu năm**: M**7,5** Noto Peninsula (Nhật Bản) ngày 2024-01-01; 10 trận M≥7 và 99 trận M≥6
   trong năm, 81 trận có cờ tsunami.
3. **Tháng 4 đột biến vì dư chấn**: **705** trận, so với 623 của tháng 1 (tháng nhiều thứ hai); 169 trận tháng 4 ở
   Đài Loan, sau trận M7.4 Hoa Liên ngày 2024-04-02 (UTC).
4. **Indonesia đứng đầu**: **605** trận, tiếp theo Philippines (427) và Nhật Bản (349 + 186 ở "Japan region"):
   đúng vành đai lửa Thái Bình Dương.
5. **Luật Gutenberg–Richter đúng trên dữ liệu thật**: b ≈ **1,13**, tức mỗi bậc magnitude ít hơn ~13 lần số trận
   (6 397 trận M≥4,5 nhưng chỉ 99 trận M≥6).

## Giới hạn

- Catalog còn được sửa: chạy lại sau vài tháng có thể lệch vài trận và vài chục phần trăm magnitude ở mức thập phân.
- `region` là chuỗi tự do: "Japan" và "Japan region" là hai giá trị; muốn chính xác phải gán theo toạ độ (reverse geocode).
- Ngưỡng M4.5 toàn cầu: dưới ngưỡng này catalog không đầy đủ ở vùng ít trạm đo, nên không so được số trận nhỏ giữa các vùng.
- Magnitude trộn nhiều thang (`mb`, `mww`...); so sánh trực tiếp chỉ gần đúng.
