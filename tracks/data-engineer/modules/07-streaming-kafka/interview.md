# Câu hỏi phỏng vấn: Streaming với Kafka

## Message queue và event stream (log) khác nhau thế nào? Khi nào chọn cái nào?

Message queue (RabbitMQ, SQS) coi message là một việc cần làm: một consumer nhận, ack, broker xoá.
Không replay được, nhiều consumer trên một queue là "competing consumers".

Event stream (Kafka, Kinesis) là một log append-only được giữ theo retention dù đã đọc hay chưa.
Mỗi consumer group tự giữ offset, nhiều group đọc độc lập, có thể replay bằng cách reset offset,
thứ tự được đảm bảo trong một partition.

Chọn queue cho task queue (gửi email, resize ảnh), routing phức tạp, ack từng message. Chọn stream
cho pipeline dữ liệu, CDC, nhiều hệ cùng tiêu thụ một nguồn, cần tính lại lịch sử.

## Giải thích topic, partition, offset. Vì sao partition quan trọng?

Topic là tên một luồng event. Topic chia thành partition, mỗi partition là một log có thứ tự trên
một broker leader. Offset là vị trí tăng dần của record trong partition.

Partition là đơn vị song song (một group có tối đa bằng số partition consumer làm việc) và đơn vị
thứ tự (Kafka chỉ đảm bảo thứ tự trong partition). Nó cũng là đơn vị replication và phân tán tải
giữa broker. Chọn số partition quá ít thì không scale được, quá nhiều thì tốn tài nguyên và tăng
thời gian failover.

## Làm sao đảm bảo các event của cùng một đơn hàng được xử lý đúng thứ tự?

Dùng `order_id` làm key. Default partitioner băm key (`murmur2(key) % N`) nên mọi event cùng key vào
cùng partition, và một partition chỉ do một consumer trong group đọc tuần tự.

Thêm các điều kiện: bật idempotent producer (hoặc `max.in.flight.requests.per.connection=1` với
client cũ) để retry không đảo thứ tự; không tăng số partition khi đang chạy vì ánh xạ key đổi;
consumer không xử lý song song các record cùng key trong một partition.

## Replication, ISR và `min.insync.replicas` hoạt động thế nào?

Mỗi partition có `replication.factor` bản trên các broker khác nhau, một leader và các follower kéo
dữ liệu. ISR là các replica bắt kịp leader. Với `acks=all`, leader chỉ ack khi mọi replica trong ISR
đã ghi. `min.insync.replicas=2` nghĩa là nếu ISR còn ít hơn 2, producer `acks=all` nhận lỗi thay vì
ghi vào chỉ một bản.

Cấu hình phổ biến RF=3, min ISR=2, acks=all: chịu được mất một broker mà không mất dữ liệu và vẫn
ghi được. Leader mới chỉ bầu từ ISR (`unclean.leader.election.enable=false`).

## So sánh `acks=0`, `acks=1`, `acks=all`.

| acks | Chờ | Rủi ro |
| --- | --- | --- |
| 0 | Không chờ | Mất khi broker lỗi hoặc mạng lỗi |
| 1 | Leader ghi | Mất nếu leader chết trước khi follower chép |
| all | Mọi replica trong ISR | Không mất nếu ISR ≥ min.insync.replicas |

Đánh đổi là độ trễ và throughput. Với dữ liệu nghiệp vụ (đơn hàng, thanh toán) luôn dùng `acks=all`.
`acks=0` chỉ hợp cho metric/log có thể mất.

## Idempotent producer giải quyết vấn đề gì? Nó có đủ cho exactly-once không?

Khi ack bị mất, producer retry và broker ghi trùng. Idempotent producer gắn producer id và sequence
number theo partition, broker bỏ bản có sequence đã thấy, đồng thời giữ thứ tự khi có nhiều request
in-flight.

Không đủ cho exactly-once end-to-end: nó chỉ chống trùng trong một phiên producer, một partition.
Producer restart (PID mới) gửi lại dữ liệu thì vẫn trùng; và nó không bao gồm phía consumer. Cần
Kafka transactions (consume-transform-produce) hoặc sink idempotent.

## Consumer group và rebalance là gì? Những gì gây rebalance và cách giảm tác động?

Các consumer cùng `group.id` chia nhau partition, mỗi partition thuộc một consumer. Rebalance là quá
trình chia lại khi consumer vào/ra, consumer bị coi là chết (mất heartbeat quá `session.timeout.ms`
hoặc không poll trong `max.poll.interval.ms`), hoặc topic đổi số partition.

Giảm tác động: dùng `CooperativeStickyAssignor` (incremental rebalance), static membership
(`group.instance.id`) cho rolling deploy, giữ thời gian xử lý mỗi poll nhỏ (`max.poll.records`),
commit offset trong callback `on_partitions_revoked` để không xử lý lại nhiều.

## Giải thích at-most-once, at-least-once, exactly-once. Bạn mặc định chọn gì?

- At-most-once: commit offset trước rồi xử lý; crash thì mất.
- At-least-once: xử lý xong mới commit; crash giữa chừng thì xử lý lại, gây trùng.
- Exactly-once: mỗi event ảnh hưởng kết quả đúng một lần. Trong Kafka → Kafka dùng transactions
  (`transactional.id`, `send_offsets_to_transaction`, consumer `read_committed`). Ra hệ ngoài thì
  lưu offset cùng transaction với dữ liệu, hoặc sink idempotent.

Mặc định chọn at-least-once + sink idempotent (upsert theo `event_id` hoặc khoá nghiệp vụ). Đơn
giản, nhanh, và cho kết quả "effectively exactly-once".

## Consumer lag là gì, đo thế nào, lag tăng thì xử lý ra sao?

Lag của partition = log-end-offset − committed offset của group. Đo bằng
`kafka-consumer-groups.sh --describe`, Burrow, Kafka exporter cho Prometheus. Nên theo dõi cả lag
theo thời gian (event cũ nhất chưa xử lý bao nhiêu giây) vì số record không nói lên độ trễ.

Lag tăng: kiểm tra consumer có lỗi/đang rebalance liên tục không; sink chậm (DB lock, API rate
limit); hot partition (một partition lag cao, các partition khác bình thường, nghĩa là key lệch).
Cách xử lý: thêm consumer (tới số partition), tăng số partition cho dữ liệu mới, batch ghi sink,
tối ưu xử lý, tách công việc nặng sang topic khác.

## Log compaction là gì? Cho ví dụ dùng.

Với `cleanup.policy=compact`, Kafka giữ ít nhất record mới nhất cho mỗi key, xoá các bản cũ hơn trong
các segment đã đóng. Record value `null` là tombstone, sau `delete.retention.ms` key bị xoá hẳn.

Dùng cho dữ liệu dạng "trạng thái hiện tại": bảng khách hàng, giá sản phẩm, changelog của state
store Kafka Streams, `__consumer_offsets`. Consumer mới đọc từ đầu topic compacted là dựng lại được
toàn bộ trạng thái mà không cần đọc lịch sử dài.

## Vì sao cần Schema Registry? Giải thích backward và forward compatibility.

Kafka chỉ lưu bytes; nếu producer đổi schema tuỳ ý, consumer sẽ gãy. Schema Registry lưu các version
schema theo subject, producer gửi schema id kèm dữ liệu, và registry chặn version không tương thích.

- Backward: consumer với schema mới đọc được dữ liệu cũ (thêm field phải có default). Nâng cấp
  consumer trước.
- Forward: consumer với schema cũ đọc được dữ liệu mới. Nâng cấp producer trước.
- Full: cả hai.

Avro/Protobuf hỗ trợ evolution tốt hơn JSON thuần. Không bao giờ đổi kiểu hoặc đổi nghĩa của field
đang dùng; muốn thay đổi lớn thì tạo topic version mới.

## Event time, processing time và watermark là gì? Xử lý event đến trễ thế nào?

Event time là lúc sự kiện xảy ra, processing time là lúc hệ thống xử lý. Tính theo event time mới đúng
nghiệp vụ nhưng phải chờ event trễ. Watermark là ước lượng "đã thấy hết event trước thời điểm W",
thường `W = max_event_time − allowed_lateness`. Window có `end ≤ W` thì đóng và phát kết quả.

Event có event time nhỏ hơn watermark (window đã đóng) là late event. Lựa chọn: bỏ đi (đếm metric),
đẩy vào side output/DLQ để xử lý batch sau, hoặc cập nhật kết quả (phát lại window với output mode
update và sink upsert). Đánh đổi: lateness lớn thì đầy đủ hơn nhưng trễ và tốn state.

## Tumbling, hopping (sliding) và session window khác nhau thế nào?

Tumbling: kích thước cố định, không chồng, mỗi event thuộc đúng một window (GMV mỗi phút). Hopping:
kích thước `size` trượt mỗi `advance` nhỏ hơn size, cửa sổ chồng nhau, một event thuộc nhiều window
(GMV 5 phút gần nhất cập nhật mỗi phút). Session: gom các event cách nhau dưới `gap`, độ dài khác
nhau theo hoạt động (phiên duyệt web). Sliding trong một số framework (Kafka Streams) còn có nghĩa
window xác định theo khoảng cách giữa hai event.

## So sánh Kafka, RabbitMQ và AWS SQS/SNS.

Kafka: log phân tán, giữ dữ liệu, replay, throughput rất cao, thứ tự theo partition, hợp pipeline dữ
liệu, CDC. RabbitMQ: exchange + queue, routing linh hoạt (direct/topic/fanout), ack từng message,
priority, hợp task queue. SQS: queue serverless, standard (at-least-once, không thứ tự) và FIFO
(thứ tự theo message group, dedup 5 phút), visibility timeout, DLQ. SNS: pub/sub serverless, fan-out
tới nhiều SQS/Lambda.

Đang trên AWS và chỉ cần tách service thì SNS + SQS rẻ và không phải vận hành. Cần replay và nhiều
đội tiêu thụ cùng dữ liệu thì Kafka (MSK, Confluent Cloud) hoặc Kinesis.

## Dual write là gì? Outbox pattern giải quyết thế nào?

Dual write: service ghi DB rồi gửi Kafka. Nếu một trong hai bước lỗi, hai hệ lệch nhau (đơn đã lưu
nhưng không có event, hoặc ngược lại). Không có transaction chung giữa DB và Kafka.

Outbox: trong cùng transaction DB, service ghi dữ liệu nghiệp vụ và một dòng vào bảng `outbox`. Một
tiến trình riêng (Debezium đọc WAL/CDC, hoặc poller) đẩy các dòng outbox lên Kafka với at-least-once,
consumer dedup theo `event_id`. Đảm bảo "có dữ liệu thì có event".

## Thiết kế pipeline thời gian thực: order events của Olist vào warehouse, kèm dashboard GMV theo phút theo bang.

Gợi ý câu trả lời theo lớp:

1. Nguồn: service đơn hàng dùng outbox + Debezium, hoặc producer `acks=all`, idempotent, key
   `order_id`, topic `olist.orders.v1` (12 partition, RF 3, retention 7 ngày), schema Avro trong
   Schema Registry, BACKWARD.
2. Xử lý: Flink hoặc Spark Structured Streaming đọc theo event time, watermark 10 phút, tumbling
   window 1 phút group theo `customer_state`, dedup `event_id` trong state có TTL. Late event vào
   topic `olist.orders.late`. Kết quả ghi topic `olist.gmv_per_minute` hoặc thẳng sink.
3. Sink: Kafka Connect S3/Iceberg sink cho lakehouse (raw), và upsert vào bảng serving
   (PostgreSQL/ClickHouse/Pinot) theo khoá `(window_start, state)` để idempotent.
4. Dashboard đọc bảng serving. Job batch hằng đêm tính lại từ raw để sửa sai do late data (hoặc
   Kappa: replay topic).
5. Vận hành: alert consumer lag theo giây, DLQ có dữ liệu, under-replicated partitions; ACL theo
   service; test logic window bằng unit test và test tích hợp với Kafka trong Docker.

Nêu rõ đánh đổi: độ trễ dashboard vs độ đầy đủ (lateness), chi phí vận hành Flink vs dùng dịch vụ
managed, exactly-once bằng sink idempotent thay vì transaction phân tán.

## Crash sau DB commit nhưng trước Kafka commit có làm mất dữ liệu không?

Record có thể được đọc lại. Nếu dữ liệu và checkpoint sink cùng transaction, lần đọc lại nhận ra
record đã xử lý và không ghi trùng. Consumer chỉ commit offset kế tiếp của record đã hoàn tất.
Xem bài CDC sink; giả định ordering/topic generation phải được giữ rõ.

## Có thể replay từ earliest để dựng mọi bảng trong mọi trường hợp không?

Không. Earliest là record sớm nhất còn được giữ, có thể thiếu lịch sử ban đầu.
Dựng bảng mới bằng group mới, kiểm retention và bản nền/snapshot, đối chiếu rồi mới chuyển người đọc.
Không reset consumer đang phục vụ rồi để record cũ ghi đè trạng thái mới.
