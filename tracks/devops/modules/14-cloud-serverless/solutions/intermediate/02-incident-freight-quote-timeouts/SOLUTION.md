# Lời giải: Lambda báo giá vận chuyển hết giờ

## Nguyên nhân

Handler gọi dịch vụ báo giá **tuần tự**, từng đơn một, không có hạn thời gian cho cả lần invoke. Mỗi lần gọi khoảng 0,4 giây, nên thời gian
một lần invoke tăng tuyến tính theo số record: 1 đơn 0,4 giây, 10 đơn khoảng 4 giây, vượt timeout 3 giây. Trước khuyến mãi batch chỉ có
một hai đơn nên không ai thấy.

Chuỗi hệ quả:

1. Hết giờ thì Lambda không trả gì, event source mapping coi **cả batch** thất bại, mọi message hiện lại sau visibility timeout, kể cả 7
   đơn đã báo giá xong. Lần sau lại hết giờ ở đúng chỗ đó: dịch vụ báo giá bị hỏi lại cùng đơn nhiều lần, số lần invoke tăng gấp bội.
2. Sau `maxReceiveCount` lần nhận, đơn hợp lệ nằm ở cuối batch sang DLQ dù không có gì sai.
3. Một đơn trả `500` làm `shipping.quote` ném lỗi, exception thoát khỏi handler, cả batch thất bại cùng nó.

Timeout không phải nguyên nhân mà là triệu chứng; tăng timeout lên 15 giây chỉ đẩy giới hạn lên batch 35 đơn và vẫn hỏi giá lại khi có lỗi.

## Cách sửa (`handler/app.py`)

- **Gọi song song có giới hạn**: một `ThreadPoolExecutor(max_workers=8)` tạo ở cấp module, đúng hạn mức 8 request đồng thời của hợp đồng
  (thread hợp với I/O; không cần asyncio hay thư viện ngoài). 10 đơn còn khoảng 0,8 giây.
- **Hạn chót theo thời gian còn lại**: chờ các future tối đa `context.get_remaining_time_in_millis()` trừ 500 ms an toàn. Future xong thì
  là thành công; chưa xong thì `cancel()` (future chưa chạy bị huỷ) và record vào `batchItemFailures` để SQS giao lại; handler luôn trả lời
  trước khi Lambda giết nó.
- **Lỗi theo từng record**: exception của một future chỉ đưa record đó vào `batchItemFailures`.
- **Timeout cho từng lần gọi** (`CALL_TIMEOUT = 2` giây) để một request treo không giữ thread mãi.

**Vì sao pool ở cấp module, không tạo mới mỗi lần invoke.** Cách hay gặp là tạo pool trong handler rồi `shutdown(wait=False,
cancel_futures=True)`. Trên Lambda thật, sau khi handler trả lời môi trường bị đóng băng cùng các thread đang gọi dở; lần invoke sau rã đông
chúng, và pool mới mở thêm 8 request nữa: tổng có thể vượt 8 request đồng thời, dịch vụ báo giá trả `429`. Pool dùng chung theo môi trường
thực thi giữ trần 8 cho mọi request của môi trường đó, kể cả request còn sót từ lần trước (chúng chiếm chỗ trong pool thay vì chạy song song
với pool mới). Request sót vẫn có thể hoàn tất sau khi record đã được báo lỗi, nên phía dịch vụ báo giá (hay bước ghi kết quả) nên idempotent
theo `order_id`. Một cách khác là đặt `CALL_TIMEOUT` nhỏ hơn biên an toàn để mọi request kết thúc trước khi handler trả lời.

## Phòng ngừa (cho postmortem)

- Alarm trên metric `Duration` (p99 so với timeout) và `Errors`, `Throttles` của function; alarm khi DLQ có message.
- Đặt `batch_size` và `scaling_config.maximum_concurrency` của event source mapping theo hạn mức của downstream: 8 request đồng thời mỗi
  Lambda nhân số Lambda đồng thời vẫn có thể vượt tổng hạn mức của dịch vụ báo giá.
- Load test với batch đầy (10 record) và downstream chậm trước mỗi đợt khuyến mãi; test hợp đồng dịch vụ phía sau (độ trễ, 429, 500).
- Idempotency phía consumer (bài Intermediate 01) để message giao lại không gây tác dụng phụ hai lần.
