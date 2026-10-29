# Báo cáo: thời tiết TP.HCM và Hà Nội năm 2023 (Open-Meteo, ERA5)

## Bộ dữ liệu

- API Open-Meteo Historical Weather (`archive-api.open-meteo.com/v1/archive`), không cần key, dữ liệu
  CC BY 4.0, nguồn gốc là tái phân tích ERA5 của ECMWF/Copernicus.
- Tham số ghim: TP.HCM (10.82, 106.63), Hà Nội (21.03, 105.85); 2023-01-01 → 2023-12-31; biến theo ngày
  `temperature_2m_max/min/mean`, `precipitation_sum`; `timezone=Asia/Bangkok` (GMT+7); `models=era5`.
- 2 request, 2 tệp JSON thô ~14 KB mỗi tệp trong `data/raw/open-meteo/`. API trả về ô lưới gần nhất:
  (10.75, 106.75) cao 7 m và (21.0, 105.75) cao 24 m.

## Làm sạch

- Response lưu nguyên trạng trước khi parse: parse sai thì sửa code và chạy lại từ tệp, không gọi API lần nữa
  (và không bị ảnh hưởng nếu nguồn đổi dữ liệu).
- Parse khoá `daily` thành bảng `city, date, tmax, tmin, tmean, precip_mm`. Năm 2023 không có ngày null hay trùng;
  `clean` vẫn bỏ ngày toàn null (API trả `null` cho ngày chưa có dữ liệu) và trùng `(city, date)` để chạy an toàn
  khi hai lần thu thập chồng khoảng ngày.
- Kết quả: `data/clean/open-meteo/daily.parquet`, 730 dòng (365 ngày × 2 thành phố).

## Insight

1. **Hà Nội có mùa đông, TP.HCM thì không**: biên độ nhiệt năm (tháng nóng nhất trừ tháng lạnh nhất) của Hà Nội
   là **13,6 °C** (17,1 °C tháng 1 → 30,8 °C tháng 7), TP.HCM chỉ **3,3 °C** (26,2 → 29,5 °C), gấp hơn 4 lần.
2. **TP.HCM nóng nhất vào tháng 4, trước mùa mưa**: mây và mưa từ tháng 5 kéo nhiệt độ xuống; Hà Nội nóng nhất
   tháng 7, giữa mùa hè.
3. **Hà Nội nắng nóng gay gắt hơn**: **47** ngày `tmax` ≥ 35 °C, đỉnh **39,8 °C** ngày 17/05/2023; TP.HCM chỉ
   **7** ngày, cao nhất 36,1 °C.
4. **Mùa mưa rõ rệt ở cả hai nơi**: **82%** (TP.HCM, 1 826 mm/năm) và **84%** (Hà Nội, 1 502 mm/năm) lượng mưa rơi
   trong tháng 5–10. TP.HCM mưa đều hơn: 220 ngày mưa ≥ 1 mm so với 151 ngày của Hà Nội. Tháng 3 TP.HCM gần như
   không mưa (1,4 mm).

## Giới hạn

- ERA5 là **tái phân tích** trên lưới ~25 km, không phải số đo trạm: nhiệt độ cực trị bị làm mượt (trạm Láng
  có thể ghi cao hơn), mưa rào cục bộ của TP.HCM bị dàn đều.
- Một điểm lưới đại diện cho cả thành phố; ô gần nhất của TP.HCM lệch ~15 km về phía đông nam.
- Một năm (2023, năm có El Niño mạnh lên cuối năm) không đại diện cho khí hậu; muốn kết luận cần 30 năm.
