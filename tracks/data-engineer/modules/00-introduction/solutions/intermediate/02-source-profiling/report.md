# Báo cáo: profile bốn nguồn dữ liệu thật của module 00

## Bộ dữ liệu

| Nguồn | Loại | Khoảng thời gian | Bản ghi |
| --- | --- | --- | --- |
| `nasa-http-logs` | log web, append-only | 01/07 → 28/07/1995 | 1 891 714 |
| `air-quality-uci` | IoT, cảm biến theo giờ | 10/03/2004 → 04/04/2005 | 9 357 |
| `usgs-earthquakes` | API phân trang, bản ghi bị sửa | năm 2024 (2 lượt thu thập) | 6 398 dòng thô, 6 397 trận |
| `open-meteo` | API, một request mỗi thành phố | năm 2023, 2 thành phố | 730 |

## Làm sạch

- Profiler chỉ đo, không sửa dữ liệu. "Thiếu" = null **hoặc** giá trị sentinel đã khai báo (`-200` cho IoT).
- Khoá để đếm trùng: IoT `ts`; USGS `id`; Open-Meteo `(city, ts)`; log không có khoá nên chỉ đếm dòng trùng hoàn toàn.
- Dung lượng thô: log là text sau giải nén, IoT là CSV trong zip, API là tổng JSON đã cache. Parquet nén `zstd`.
- Kết quả: `data/clean/source-profiles/profiles.parquet` (một dòng mỗi nguồn) và mẫu Parquet từng nguồn trong `samples/`.

## Insight

| | Log NASA | IoT UCI | USGS | Open-Meteo |
| --- | --- | --- | --- | --- |
| Bản ghi/ngày | **68 629** | 24,0 | 17,5 | 2,0 |
| Khoảng cách trung vị | 1 giây | 3 600 giây | ~51 phút | 1 ngày |
| Khoảng lặng dài nhất | 1 326 giây (13/07 23:48 UTC) | 3 600 giây (không lỗ hổng) | 13,7 giờ | 1 ngày |
| Trùng | 835 dòng giống hệt | 0 | **1 id** (lấy lại ở watermark) | 0 |
| Thiếu / sentinel | 0 | **16 701 ô `-200`**, `NMHC(GT)` 90,2% | 0 | 0 |
| Byte/dòng thô → Parquet | 108 → 7,9 (**×13,7**) | 84 → 28 (×3,0) | 777 → 25 (**×31**) | 38 → 15 (×2,5) |
| Thô mỗi năm | **2,7 GB** | 0,7 MB | 5 MB | 28 KB |

Khuyến nghị:

1. **Log NASA**: velocity cao nhất (gấp ~2 900 lần IoT) nhưng 2,7 GB/năm vẫn vừa một máy. Thu thập **batch theo giờ**,
   agent đẩy tệp log đã xoay vòng (push), ghi Parquet phân vùng theo ngày (nén ×13,7). Không dedup (835 dòng trùng là
   request thật). Cảnh báo khi khoảng lặng > 10 phút vào giờ hành chính (đúng sự cố tối 13/07) và khi tỉ lệ dòng hỏng tăng.
2. **IoT UCI**: rất đều (24 dòng/ngày, không lỗ hổng thời gian) nhưng chất lượng là vấn đề chính: 16 701 ô sentinel.
   Thu thập **push qua MQTT, micro-batch**; khoá `(sensor_id, ts)` để upsert khi thiết bị gửi bù. Validate `-200` ngay
   khi ingest; cảnh báo theo cột (một máy phân tích chết như `NMHC(GT)`) khác với cảnh báo mất kết nối (cả trạm im lặng).
3. **USGS**: ít bản ghi nhưng JSON rất "béo" (777 byte/dòng, Parquet nhỏ hơn 31 lần) và **bản ghi bị sửa**: profile thấy
   1 id trùng giữa hai lượt. **Pull batch hằng đêm, incremental theo `updated`**, upsert theo `id`; lưu JSON thô vì rẻ.
4. **Open-Meteo**: 730 dòng/năm cho 2 thành phố, không vấn đề chất lượng. **Pull batch hằng ngày** (hoặc full reload theo
   năm); rủi ro duy nhất là rate limit và tham số model, không phải volume.

Kết luận chung: không nguồn nào cần streaming theo số đo; chỉ cảnh báo vận hành (log, IoT) có thể cần độ trễ phút.

## Giới hạn

- Profile một lần trên dữ liệu lịch sử không cho biết **độ trễ đến** (late data) của nguồn thật: USGS phải nhìn `updated`,
  IoT thật cần thời điểm nhận ở gateway, không có trong bộ UCI.
- Velocity trung bình che giấu đỉnh: log NASA có ngày 134 nghìn request; năng lực hệ thống phải tính theo đỉnh.
- Ngoại suy một năm giả định tốc độ không đổi; log 1995 hay một trạm IoT không đại diện cho hệ thống hiện đại (hàng nghìn
  trạm, log hàng TB/ngày): giá trị nằm ở phương pháp đo, không ở con số tuyệt đối.
