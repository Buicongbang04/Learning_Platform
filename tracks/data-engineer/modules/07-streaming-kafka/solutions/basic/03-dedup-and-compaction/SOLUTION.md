# Lời giải: Dedup event và mô phỏng log compaction

## Cách làm

- `dedup_events`: một `set` id đã thấy, duyệt một lượt, chỉ append khi id chưa có. Event không id
  luôn append. O(n) thời gian, O(số id) bộ nhớ.
- `count_duplicates`: đếm số lần xuất hiện rồi trừ 1, lọc các id có trùng.
- `compact`: duyệt theo offset, ghi đè dict; tombstone thì `pop`.
- `compacted_offsets`: lưu offset cuối của mỗi key (kể cả tombstone), trả về list đã sắp.

## Vì sao

- **Trùng là chuyện bình thường** với at-least-once: producer retry, consumer xử lý lại sau
  rebalance hoặc crash trước khi commit. Dedup theo `event_id` (do producer sinh, ví dụ UUID) biến
  at-least-once thành "effectively exactly-once" ở phía xử lý.
- **Bộ nhớ dedup không thể lớn mãi**: trong stream thật, `set` này phải có TTL (giữ id trong 1 giờ,
  hoặc tới watermark), lưu trong state store (RocksDB, Redis) chứ không trong RAM của một process.
  Bài advanced 02 sẽ thêm TTL.
- **Compaction** biến topic thành "bảng trạng thái hiện tại": consumer mới đọc từ đầu là dựng lại
  được giá sản phẩm hiện tại mà không phải đọc mọi thay đổi. Tombstone được giữ thêm một thời gian
  (`delete.retention.ms`) để các consumer đang đọc kịp nhận lệnh xoá, sau đó mới biến mất.
- Lưu ý compaction trong Kafka chạy nền trên các segment đã đóng, nên consumer vẫn có thể thấy
  nhiều version của cùng key: compaction đảm bảo **ít nhất** giá trị mới nhất, không đảm bảo **chỉ**
  giá trị mới nhất.
