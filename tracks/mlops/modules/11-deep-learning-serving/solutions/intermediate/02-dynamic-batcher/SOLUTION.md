# Lời giải: dynamic batcher

## Cách làm

- `submit` tạo `Future`, đưa `(item, future)` vào `asyncio.Queue`, chờ future. Kết quả gắn với future của chính request nên không thể nhầm, kể cả khi thứ tự đến xáo trộn.
- `_collect` chờ item đầu không giới hạn (không quay vòng khi rảnh), đặt `deadline` tính từ item đầu, rồi lấy thêm bằng `wait_for(queue.get(), remaining)` cho tới khi đủ `max_batch_size` hoặc hết hạn.
- `_loop` xếp chồng item bằng `np.stack`, gọi `infer` qua `asyncio.to_thread` (model C++ chặn, không được chạy trong event loop), rồi `set_result` theo chỉ số. Lỗi thì `set_exception` cho mọi future của batch và `continue`: một ảnh hỏng không được giết vòng lặp, nếu không mọi request sau đó treo mãi.
- Bỏ future đã bị huỷ (client ngắt kết nối) trước khi chạy để không tốn chỗ trong batch.

## Hai núm vặn

| Núm | Tăng lên thì | Giảm xuống thì |
| --- | --- | --- |
| `max_batch_size` | throughput cao hơn tới khi phần cứng bão hoà; latency mỗi batch và **bộ nhớ đỉnh** tăng theo | GPU chạy batch nhỏ, nhiều lần gọi, phí overhead |
| `max_wait_ms` | lúc tải thấp batch to hơn nhưng request lẻ chịu thêm tới `max_wait_ms` | latency thấp, lúc tải thấp gần như batch 1 |

Chỉ có `max_wait_ms`: lúc tải cao batch to tuỳ ý, latency và bộ nhớ mất kiểm soát. Chỉ có `max_batch_size`: lúc tải thấp request lẻ phải chờ đủ người mới chạy, có thể chờ mãi. Giá trị khởi đầu hợp lý: `max_batch_size` ở đầu gối đường cong throughput của bài benchmark (và vừa bộ nhớ), `max_wait_ms` khoảng 5–10% ngân sách p95.

## Kiểm chứng ngoài test

- Ghi `batch_sizes` thành histogram metric: tải thật mà batch trung bình gần 1 thì batching không giúp gì, chỉ cộng thêm `max_wait_ms`.
- Thời gian chờ trong hàng đợi là một phần của latency; đo riêng nó.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Test | Pass |
| Đánh đổi | Nói được ảnh hưởng của `max_wait_ms` lên p50 lúc tải thấp và p95 lúc tải cao |
| Hai giới hạn | Giải thích được vì sao cần cả hai |
