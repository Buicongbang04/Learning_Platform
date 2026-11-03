# Lời giải: consumer Kafka tính feature cửa sổ 15 phút

`consumer.py` cạnh tệp này là lời giải chạy được.

## Ý chính

- **Tách logic cửa sổ khỏi Kafka.** `ZoneWindows` là lớp thuần (giống `WindowAggregator` của Basic 01, thêm phần parse `pickup_at`);
  `consume_windows` chỉ tạo consumer, lặp message, đóng consumer và `flush`. Lớp thuần test được không cần broker, và đổi engine sau
  này không phải viết lại logic.
- **Event time là `pickup_at`**, không phải `message.timestamp` (lúc broker nhận) hay `time.time()` (lúc đọc). Test phát lại một luồng
  2019 vào topic hôm nay: tính theo thời gian đọc sẽ dồn mọi chuyến vào một hai cửa sổ.
- **Một partition để thứ tự đọc xác định.** Nhiều partition thì mỗi partition có watermark riêng, watermark của toàn job là nhỏ nhất;
  một partition không có dữ liệu giữ watermark đứng yên (Flink có `withIdleness` cho trường hợp này).
- **Không auto commit.** Chạy thật: commit offset **sau** khi feature của các cửa sổ đã đóng được ghi xong (at-least-once), và ghi
  feature idempotent (upsert theo `(zone, window)`) để đọc lại không cộng dồn. Trạng thái cửa sổ đang mở phải checkpoint cùng offset,
  nếu không restart sẽ mất phần đã đếm; đó là lý do dùng engine có state (Flink, Bytewax) thay vì tự viết khi pipeline lớn lên.

## Lỗi hay gặp

- Dùng `group_id` cố định: lần chạy sau bắt đầu ở offset đã commit, đọc 0 message.
- Quên `consumer_timeout_ms`: vòng lặp chờ mãi, test treo tới timeout.
- Quên `flush` cuối luồng: mất các cửa sổ cuối.
- Parse `pickup_at` bằng `strptime` không có múi giờ rồi `timestamp()`: Python coi là giờ địa phương của máy, lệch theo máy chạy.
