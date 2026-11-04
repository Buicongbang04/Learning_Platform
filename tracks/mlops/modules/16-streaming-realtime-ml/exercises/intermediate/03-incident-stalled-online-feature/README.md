---
title: "Sự cố: feature online đứng yên dù topic vẫn có dữ liệu"
level: intermediate
services: []
files:
  - path: starter/zone_stream.py
    note: Bản đang chạy production; sửa ở đây
  - path: tests/fixtures/events.jsonl
    note: Log sự kiện phát lại từ topic (chuyến taxi thật 05/03/2019)
  - path: tests/test_zone_stream.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/16-streaming-realtime-ml/exercises/intermediate/03-incident-stalled-online-feature -q
---

## Mục tiêu

Chẩn đoán và sửa một sự cố streaming từ triệu chứng, như khi trực on-call: không ai nói cho bạn nguyên nhân, bạn có log, có mã đang
chạy, và có một bộ đếm. Sau khi sửa, viết lại ngắn gọn nguyên nhân gốc và một biện pháp để lần sau phát hiện sớm hơn.

## Đề bài

**Báo cáo lúc 10:05 (UTC), ngày 05/03/2019.** Model ETA dùng feature `trips` và `avg_fare` 15 phút của từng zone, do
`starter/zone_stream.py` tính từ topic chuyến xe rồi đẩy bản mới nhất mỗi zone (`snapshot()`) lên online store. Đội serving báo: từ
khoảng 09:00, feature của cả ba zone không đổi nữa. Dashboard Kafka bình thường: producer vẫn gửi đều, consumer lag gần 0, không
có lỗi nào trong log của consumer. Không ai deploy consumer trong tuần. Bộ đếm `stats["skipped"]` tăng vọt từ khoảng 08:50.

`tests/fixtures/events.jsonl` là log phát lại đúng những gì consumer đọc được từ 08:00 tới 10:00, theo thứ tự đọc. Mỗi dòng có
`event_id`, `zone_id`, `fare`, `pickup_at` (thời điểm đón, chuỗi ISO 8601 do gateway gửi lên) và `received_at` (thời điểm broker
nhận, UTC).

Việc của bạn:

1. Tìm nguyên nhân gốc (đọc log và mã, tự chạy lại log qua `ZoneStream`).
2. Sửa `starter/zone_stream.py`, giữ nguyên giao diện: `ZoneStream(window_s, hold_s)`, `ingest(event) -> list[dict]`, `flush()`,
   `snapshot()`, `stats` với bốn khoá. Hành vi khác giữ như cũ: cửa sổ tumbling 15 phút theo thời điểm đón, cùng quy tắc trùng lặp,
   cùng `hold_s` cho sự kiện đến muộn.
3. Thêm một quy tắc phòng vệ test có kiểm: sự kiện có thời điểm đón **muộn hơn `received_at` quá 300 giây** là dữ liệu hỏng (thiết
   bị sai đồng hồ): không tính vào feature, không ảnh hưởng sự kiện khác, đếm vào `stats["rejected"]`.

Test chạy log qua mã của bạn và so với kết quả mong đợi trong `tests/fixtures/expected.json`: bản mới nhất của mỗi zone sau khi đọc
hết log, mọi cửa sổ phát ra (cả lúc `flush`), bốn bộ đếm; thêm một ca chèn đúng một sự kiện có thời điểm đón sau `received_at` ba
ngày. Một test khác chạy bản đang chạy production (`tests/fixtures/zone_stream.v1.py`) để xác nhận nó tái hiện đúng triệu chứng.

## Tiêu chí đạt

- Test pass.
- Bạn viết được nguyên nhân gốc trong ba câu: cái gì đổi, tại sao mã cũ hiểu sai nó, và tại sao một lỗi chỉ kéo dài vài phút lại làm
  feature đứng yên cả giờ sau đó.
- Bạn đề xuất được một cảnh báo bắt sự cố này trong vài phút (gợi ý: so sánh giữa thời gian xử lý và một đại lượng bên trong
  consumer), và một kiểm tra ở hợp đồng dữ liệu phía producer.

## Gợi ý

### Gợi ý 1

Đếm xem từ 09:00 những sự kiện nào bị tính là `skipped`, và so `pickup_at` của chúng với các sự kiện được nhận ngay trước đó. Có
dòng nào trong log trông khác các dòng còn lại không?

### Gợi ý 2

In giá trị bên trong `ZoneStream` quyết định một sự kiện là `skipped`, sau mỗi sự kiện, quanh mốc 08:50–09:00. Nó tăng đều theo
luồng hay nhảy một bước lớn? Bước nhảy đó đến từ sự kiện nào?
