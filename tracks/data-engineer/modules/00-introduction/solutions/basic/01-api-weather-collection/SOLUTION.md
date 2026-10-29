# Lời giải: thu thập thời tiết từ Open-Meteo

## Cách làm

1. **Ghim mọi thứ** trong `build_params`: toạ độ, khoảng ngày, biến, `timezone` (ngày tính theo giờ Việt Nam,
   không phải UTC) và `models=era5` (mặc định `best_match` có thể đổi nguồn theo thời gian, làm số liệu không tái lập).
2. **`fetch_json`** là một vòng thử có giới hạn:
   - luôn truyền `timeout` (không có timeout, một kết nối treo sẽ treo cả pipeline);
   - tách lỗi **tạm thời** (429, 5xx, lỗi mạng) khỏi lỗi **vĩnh viễn** (400, 404): gọi lại lỗi vĩnh viễn chỉ
     phí quota và che mất bug ở tham số;
   - backoff luỹ thừa `2**k`; ưu tiên `Retry-After` vì đó là server nói thẳng cần chờ bao lâu;
   - `sleep` được truyền vào nên test không phải chờ thật và không cần mạng.
   Production thêm **jitter** (nhân ngẫu nhiên 0,5–1,5) để nhiều worker không cùng thử lại một lúc.
3. **`collect`** cache response thô, tên tệp chứa khoảng ngày; có rồi thì bỏ qua: chạy lại notebook là
   idempotent và không tốn request. Ghi qua tệp tạm rồi `replace` (atomic trên cùng ổ đĩa).
4. **`parse_daily` / `clean`**: parse tách khỏi gọi API; `clean` bỏ ngày toàn null và trùng khoá `(city, date)`.
5. **`insights`**: `groupby` theo thành phố rồi theo tháng.
6. **`write_clean`**: ghi đè qua tệp tạm.

## Vì sao lưu thô trước khi parse

Gọi API tốn quota, chậm, và dữ liệu nguồn có thể đổi. Tệp thô là "bronze": phát hiện bug parse thì chạy lại
từ tệp. Đây cũng là bằng chứng nguồn đã trả gì vào thời điểm đó.

## Con số tham chiếu (2023, ERA5)

| | TP.HCM | Hà Nội |
| --- | --- | --- |
| `annual_rain_mm` | 1 826,3 | 1 502,0 |
| `rainy_season_share` | 0,824 | 0,836 |
| `hottest_month` / `coldest_month` | 4 / 1 | 7 / 1 |
| `amplitude_c` | 3,33 | 13,64 |
| `max_temp` (`max_temp_date`) | 36,1 (2023-05-06) | 39,8 (2023-05-17) |
| `hot_days` | 7 | 47 |
| `rainy_days` | 220 | 151 |
