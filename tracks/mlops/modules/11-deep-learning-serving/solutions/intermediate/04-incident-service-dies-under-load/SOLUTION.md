# Lời giải: service ngừng trả lời sau giờ cao điểm

## Nguyên nhân

Có hai lỗi chồng lên nhau.

1. **Batch không có giới hạn trên.** `worker` lấy request đầu, chờ `COLLECT_WINDOW_MS`, rồi `while not queue.empty()` vét **toàn bộ** hàng đợi vào một batch. Lúc tải thường hàng đợi chỉ có vài request nên batch nhỏ và vừa card. Khi push notification kéo hàng chục request tới cùng lúc (và càng nhiều khi một batch đang chạy, request mới dồn lại), batch lên 30–50 ảnh. Bộ nhớ activation tỉ lệ với số ảnh: card 4 GB trừ CUDA context chỉ chứa khoảng 9 ảnh ở cấu hình này, nên lần chạy đó ném `CUDA out of memory`.
2. **Lỗi giết worker mà không ai biết.** `device.run` ném lỗi bên trong task nền `worker`; không có `try/except` nên task kết thúc. Các future của batch đó không bao giờ được trả, request chờ tới 504. Request mới vẫn được đưa vào hàng đợi nhưng không còn ai lấy ra: 504 mãi mãi. `/healthz` chỉ trả hằng số nên vẫn 200; process sống, GPU rảnh, không ai restart.

Gửi tuần tự không tái hiện được vì hàng đợi không bao giờ có quá một request.

## Cách chẩn đoán

1. Tái hiện: 5 request tuần tự (ổn), 48 đồng thời (một phần 504), 1 request sau (504). Triệu chứng "sau lỗi đầu thì chết hẳn" chỉ ra trạng thái hỏng vĩnh viễn, không phải quá tải.
2. Bọc lời gọi model bằng `try/except` và in lỗi: `OutOfMemoryError: CUDA out of memory. Tried to allocate 12250 MiB`.
3. Log kích thước mỗi batch: 1, 1, 2, ... rồi 35. Kích thước batch đi theo độ dài hàng đợi, không có trần.

## Cách sửa

- **Trần batch từ số đo bộ nhớ**: lúc khởi động chạy một ảnh, đo bộ nhớ đỉnh mỗi ảnh (`reset_peak_memory_stats`, `max_memory_allocated`), đọc phần trống bằng `mem_get_info()`, đặt `limit = free * 0.8 // per_image`. Hệ số 0.8 chừa cho phân mảnh và workspace. Batcher lấy tối đa `limit` request mỗi lần (giống bài dynamic batcher); phần còn lại chờ lượt sau.
- **Worker không được chết**: `try/except` quanh lần chạy, lỗi thì `set_exception` cho các future của batch đó (endpoint trả 500 ngay), rồi tiếp tục vòng lặp.

Hard-code một con số (vd. 8) cũng qua được test card 4 GB nhưng gãy ở card 2 GB hoặc khi đổi model/kích thước ảnh. Cách khác hợp lệ: bắt OOM rồi chia đôi batch chạy lại; nhưng mỗi lần OOM trên card thật để lại phân mảnh và tốn thời gian, nên trần batch vẫn là tuyến phòng thủ chính.

## Phòng ngừa

- Metric: histogram kích thước batch, độ dài hàng đợi, số lỗi suy luận theo loại, "thời điểm lần chạy model thành công gần nhất".
- `/readyz` (hoặc `/healthz`) kiểm worker còn sống (`task.done()` là đỏ) và lần chạy thành công gần nhất không quá N giây khi hàng đợi khác rỗng; orchestrator sẽ restart thay vì để pod "sống mà chết".
- Giới hạn độ dài hàng đợi: đầy thì trả 503 ngay (load shedding) thay vì để request chờ tới 504.
- Load test có đợt burst trước khi deploy, không chỉ tải đều.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Test | Pass, kể cả test card 2 GB |
| Hai nguyên nhân | Tách được nguyên nhân gây lỗi (batch không trần) và nguyên nhân không hồi phục (worker chết, health check không thấy) |
| Giám sát | Ít nhất hai metric và một thay đổi health check cụ thể |
