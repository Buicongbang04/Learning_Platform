---
title: Consumer Kafka tính feature cửa sổ 15 phút theo event time
level: intermediate
services: [kafka]
files:
  - path: starter/consumer.py
    note: 1 TODO
  - path: tests/test_consumer.py
    note: Không sửa
run:
  - docker compose -f setup/mlops/compose.yaml --profile streaming up -d --wait
  - uv run python data/download_dataset.py nyc-tlc
  - uv run pytest tracks/mlops/modules/16-streaming-realtime-ml/exercises/intermediate/01-kafka-window-consumer -q
---

## Mục tiêu

Đặt logic cửa sổ của bài Basic 01 lên một topic Kafka thật. Test phát lại chuyến taxi NYC thật (tháng 3/2019, ba zone, hai giờ) vào
một topic tạm, cố tình làm lệch thứ tự, chèn sự kiện đến trễ hơn nửa giờ và gửi lại 30 bản trùng. Consumer của bạn phải ra đúng
`trips` và `avg_fare` của từng zone trong từng cửa sổ 15 phút theo **thời điểm đón khách**, không theo lúc đọc được message.

## Đề bài

Mỗi message trên topic (một partition, key là `zone_id`) là JSON:

```json
{"event_id": "trip-000123", "zone_id": 161, "pickup_at": "2019-03-05T08:07:12Z", "fare": 9.5}
```

Viết `consume_windows(bootstrap, topic, *, window_s=900, lateness_s=180, idle_ms=3000)` trong `starter/consumer.py`:

- Đọc topic **từ đầu** bằng `kafka.KafkaConsumer` (thư viện `kafka-python-ng`, đã có trong môi trường), dừng khi `idle_ms` không có
  message mới (`consumer_timeout_ms`), rồi đóng consumer. Một lần `poll` rỗng chưa chắc là hết dữ liệu (consumer có thể còn đang join group): tính idle theo thời gian kể từ message cuối.
- Event time là `pickup_at` (UTC). Cửa sổ tumbling `[start, start + window_s)` với `start = ts - ts % window_s` (`ts` là giây epoch).
- Quy tắc như Basic 01, theo thứ tự đọc: `event_id` đã gặp thì đếm `duplicates`; sự kiện có `window_end <= watermark` (watermark
  trước sự kiện đó) thì đếm `late` và bỏ; còn lại cộng vào cửa sổ; rồi `watermark = max(watermark, ts - lateness_s)`, và đóng mọi
  cửa sổ có `window_end <= watermark`. Hết message thì đóng mọi cửa sổ còn mở.
- Trả dict `{"windows": [...], "late": int, "duplicates": int, "consumed": int}` (`consumed` là số message đã đọc, kể cả bản trùng).
  Mỗi dòng trong `windows` có đúng năm khoá `zone_id`, `window_start`, `window_end` (giây epoch, int), `trips`, `avg_fare`
  (trung bình `fare` của các chuyến được nhận). Dòng xuất theo thứ tự cửa sổ đóng; cửa sổ đóng cùng lúc thì theo
  `(window_end, zone_id)`. Vì watermark chỉ tăng, cả list `windows` (kể cả phần `flush`) khi đó tăng dần theo
  `(window_end, zone_id)`: test kiểm điều này trên mọi ca.

Test có ba ca trên topic thật tạo bằng `mlopskit.kafka_topic()` (xoá sau khi chạy): một luồng 8 sự kiện viết tay có đáp án
cố định, một luồng 4 sự kiện trong đó một lần đóng nhiều cửa sổ có `window_end` khác nhau, và luồng chuyến thật so với bản tham
chiếu tính lại trong test trên đúng thứ tự đã gửi. Kafka (profile `streaming`) chưa bật hoặc chưa tải dữ liệu thì test skip kèm
lệnh cần chạy.

## Tiêu chí đạt

- Test pass.
- Bạn giải thích được vì sao test dùng một partition, và điều gì đổi khi topic có nhiều partition (watermark theo từng partition,
  lấy nhỏ nhất; partition rảnh giữ watermark đứng yên).
- Bạn nói được vì sao consumer này tắt auto commit, và nếu chạy thật thì commit offset ở đâu so với lúc ghi feature (để không mất
  hay đếm lại sự kiện khi consumer chết giữa chừng).

## Gợi ý

### Gợi ý 1

Tách phần gộp cửa sổ thành một lớp thuần (như `WindowAggregator` của Basic 01) và để `consume_windows` chỉ lo Kafka: tạo consumer,
lặp message, gọi `add`, cuối cùng `flush`. Lớp thuần thì test được không cần broker.

### Gợi ý 2

`KafkaConsumer(topic, bootstrap_servers=..., group_id=<tên mới mỗi lần>, auto_offset_reset="earliest", enable_auto_commit=False,
consumer_timeout_ms=idle_ms, value_deserializer=lambda b: json.loads(b))`. `datetime.fromisoformat("...Z")` đọc được đuôi `Z` từ
Python 3.11.
