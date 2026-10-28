# Lời giải: Partitioner, consumer group assignment và consumer lag

## Cách làm

- `partition_for`: `zlib.crc32(key) % n` khi có key, `counter % n` khi không có key.
- `assign`: tạo sẵn đủ partition, duyệt event theo thứ tự, append vào partition tương ứng. Do
  append theo thứ tự đọc, mỗi partition tự giữ thứ tự xuất hiện.
- `range_assign`: `divmod` để biết mỗi consumer nhận bao nhiêu, cắt dải liên tiếp.
- `consumer_lag`: `max(end - (committed or 0), 0)`.

## Vì sao

- **Key → partition là hàm tất định**: mọi event của một `order_id` vào cùng partition nên thứ tự
  `created → approved → shipped` được giữ. Không có key thì Kafka rải đều để cân tải, mất thứ tự.
- **Đổi số partition làm đổi kết quả `% n`**: thử `partition_for(b"o1", 3)` và `partition_for(b"o1", 4)`
  để thấy key nhảy sang partition khác. Đó là lý do không nên tăng partition cho topic cần thứ tự.
- **Range assignor** cho thấy số consumer hữu ích tối đa bằng số partition; consumer thứ 4 với 3
  partition ngồi chơi. Kafka còn RoundRobin, Sticky, CooperativeSticky assignor; CooperativeSticky
  giảm số partition phải chuyển khi rebalance.
- **Lag** là metric quan trọng nhất khi vận hành consumer. Partition chưa commit có lag bằng toàn
  bộ log (trong thực tế là end offset trừ log-start offset, ở đây giả sử log bắt đầu từ 0).
- Kafka thật dùng murmur2 chứ không phải crc32; client Python và Java phải dùng cùng hàm băm thì
  cùng key mới ra cùng partition, nên đừng tự viết partitioner riêng nếu nhiều ngôn ngữ cùng ghi.
