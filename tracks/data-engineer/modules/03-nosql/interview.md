# Câu hỏi phỏng vấn: NoSQL

## NoSQL là gì? Khi nào bạn chọn NoSQL thay vì PostgreSQL?

NoSQL là nhóm database không lấy bảng quan hệ làm trung tâm: document (MongoDB), wide-column (Cassandra,
Bigtable), key-value (Redis, DynamoDB), graph (Neo4j). Chúng thường đánh đổi JOIN, truy vấn ad-hoc hoặc
transaction đa bản ghi để lấy khả năng scale ngang, độ trễ thấp ổn định, hoặc mô hình dữ liệu tự nhiên hơn.

Tôi chọn NoSQL khi access pattern đã rõ và đơn giản nhưng khối lượng rất lớn (sự kiện vận chuyển hàng tỉ dòng →
Cassandra), khi dữ liệu có cấu trúc thay đổi nhiều (catalog sản phẩm → MongoDB), khi cần độ trễ dưới mili giây
(cache, session → Redis), hoặc khi quan hệ nhiều bước là trọng tâm (gợi ý → Neo4j). Tôi ở lại PostgreSQL khi cần
JOIN ad-hoc, ràng buộc toàn vẹn, transaction nhiều bảng, hoặc khi dữ liệu vẫn vừa một máy. "Không biết chọn gì"
thì mặc định PostgreSQL.

## Giải thích CAP theorem. Cassandra và MongoDB chọn gì?

CAP nói rằng khi có network partition, hệ phân tán phải chọn giữa Consistency (mọi đọc thấy ghi mới nhất, hoặc
lỗi) và Availability (mọi node còn sống đều trả lời). Partition là chuyện chắc chắn xảy ra nên "CA" không có ý
nghĩa với hệ phân tán.

- **Cassandra là AP**: mọi replica nhận ghi, khi mạng đứt hai phía vẫn phục vụ, hoà giải bằng timestamp
  (last-write-wins), hinted handoff, read repair, anti-entropy repair. Nhưng consistency có thể chỉnh theo từng
  truy vấn (`QUORUM`, `ALL`).
- **MongoDB là CP** (mặc định): chỉ primary nhận ghi; primary bị cô lập khỏi đa số sẽ step down, phía thiểu số
  không nhận ghi. Đọc từ secondary thì trở nên eventual.

Lưu ý CAP chỉ mô tả lúc có sự cố; PACELC bổ sung đánh đổi latency/consistency khi bình thường.

## PACELC khác CAP thế nào?

PACELC: *if Partition, choose Availability or Consistency; Else, choose Latency or Consistency*. CAP bỏ qua
trường hợp phổ biến nhất là mạng bình thường. Khi đó, muốn đọc nhất quán vẫn phải đồng bộ replica (chờ ack nhiều
node, đọc từ leader), làm tăng latency. Cassandra/DynamoDB là PA/EL (mặc định ưu tiên latency), MongoDB/HBase là
PC/EC. Câu hỏi thực tế khi đánh giá DB: "nếu tôi đọc ngay sau khi ghi, tôi có chắc thấy dữ liệu không, và giá
bao nhiêu mili giây?"

## Eventual consistency là gì? Cho ví dụ một vấn đề nó gây ra và cách xử lý.

Eventual consistency: nếu ngừng ghi, cuối cùng mọi replica hội tụ về cùng giá trị, nhưng trong lúc đó các lần đọc
có thể thấy giá trị cũ hoặc khác nhau. Ví dụ: khách cập nhật địa chỉ giao hàng, ghi ở replica A, sau đó trang xác
nhận đọc từ replica B và hiện địa chỉ cũ. Cách xử lý:

- Đảm bảo **read-your-writes**: đọc từ primary/leader sau khi ghi, sticky session, hoặc dùng causal session
  (MongoDB).
- Dùng quorum `R + W > N` (Cassandra `QUORUM`/`QUORUM`, hoặc `LOCAL_QUORUM` trong một DC).
- Thiết kế idempotent và có version/timestamp để hoà giải xung đột (last-write-wins, CRDT).
- Trong pipeline dữ liệu: đọc snapshot/CDC thay vì đọc replica đang trễ, và có cơ chế xử lý late data.

## Embedding và referencing trong MongoDB: chọn thế nào?

Nguyên tắc: dữ liệu đọc cùng nhau thì lưu cùng nhau. **Embed** khi quan hệ 1-1 hoặc 1-few, dữ liệu con luôn được
đọc cùng cha và không phình vô hạn: `order.items`, `order.payments`. Lợi ích: một lần đọc, cập nhật nguyên tử trên
một document. **Reference** khi quan hệ 1-many không giới hạn hoặc many-many, khi dữ liệu con được truy vấn độc
lập, hoặc thay đổi thường xuyên và dùng ở nhiều nơi: review tham chiếu `product_id`, product tham chiếu
`seller_id`.

Có các pattern trung gian: **extended reference** (nhúng bản sao vài trường hay dùng như tên seller), **subset**
(nhúng 10 review mới nhất vào product, phần còn lại ở collection `reviews`), **computed** (lưu sẵn `avg_score`).
Rủi ro lớn nhất của embed là unbounded array vượt 16 MB và làm cập nhật chậm.

## Viết aggregation pipeline MongoDB tính doanh thu theo category từ collection orders có items nhúng.

```python
pipeline = [
    {"$match": {"status": "delivered"}},
    {"$unwind": "$items"},
    {"$group": {
        "_id": "$items.category",
        "revenue": {"$sum": "$items.price"},
        "orders": {"$addToSet": "$_id"},
    }},
    {"$project": {"_id": 0, "category": "$_id", "revenue": {"$round": ["$revenue", 2]},
                  "n_orders": {"$size": "$orders"}}},
    {"$sort": {"revenue": -1}},
]
db.orders.aggregate(pipeline)
```

Điểm cần nói: `$match` đặt đầu để dùng index và giảm dữ liệu; `$unwind` bung mảng thành mỗi item một document;
`$addToSet` + `$size` đếm distinct (với dữ liệu lớn nên `$group` hai lần thay vì gom set khổng lồ). Pipeline lớn
có thể cần `allowDiskUse`.

## Quy tắc ESR khi tạo compound index trong MongoDB là gì?

ESR = Equality, Sort, Range. Trường lọc bằng đặt trước, sau đó trường sort, cuối cùng trường lọc theo khoảng. Với
truy vấn `find({product_id: "p1", score: {$gte: 4}}).sort({created_at: -1})`, index tốt là
`{product_id: 1, created_at: -1, score: 1}`. Đặt range trước sort sẽ buộc MongoDB sort trong bộ nhớ
(`SORT` stage, giới hạn 100 MB). Kiểm chứng bằng `explain("executionStats")`: muốn thấy `IXSCAN`, không có
`SORT` riêng, và `totalDocsExamined` gần `nReturned`.

## "Query-first modeling" trong Cassandra nghĩa là gì? Thiết kế bảng cho "lấy 20 đơn mới nhất của một seller".

Cassandra không có JOIN và chỉ cho lọc hiệu quả theo partition key và clustering key, nên ta liệt kê truy vấn trước
rồi thiết kế một bảng cho mỗi truy vấn, chấp nhận trùng lặp dữ liệu.

```sql
CREATE TABLE orders_by_seller_month (
    seller_id text, month text, purchased_at timestamp, order_id text, order_value decimal,
    PRIMARY KEY ((seller_id, month), purchased_at, order_id)
) WITH CLUSTERING ORDER BY (purchased_at DESC, order_id ASC);

SELECT * FROM orders_by_seller_month WHERE seller_id = ? AND month = '2018-08' LIMIT 20;
```

`(seller_id, month)` là composite partition key: bucket theo tháng để seller lớn không tạo partition vô hạn.
`purchased_at DESC` cho phép lấy mới nhất mà không sort. `order_id` trong clustering key giúp hàng là duy nhất khi
hai đơn cùng thời điểm. Nếu tháng hiện tại chưa đủ 20 đơn, ứng dụng đọc thêm bucket tháng trước.

## Partition key và clustering key khác nhau thế nào? Hot partition là gì?

Partition key được hash để quyết định node nào lưu dữ liệu, và mọi hàng cùng partition key nằm cùng nhau. Clustering
key quyết định thứ tự hàng trong partition và cho phép range query/ORDER BY. Truy vấn phải cung cấp đủ partition
key (so sánh bằng).

**Hot partition** là partition nhận lượng đọc/ghi hoặc dữ liệu lớn bất thường, ví dụ partition key là
`order_status` (chỉ vài giá trị) hoặc `seller_id` của một seller khổng lồ. Hậu quả: một vài node quá tải, độ trễ
tăng, partition quá lớn làm compaction/repair chậm. Cách xử lý: chọn key cardinality cao, thêm bucket thời gian
hoặc bucket hash (`seller_id, bucket = hash(order_id) % 8`), và đọc song song các bucket khi cần.

## Tombstone trong Cassandra là gì và vì sao nguy hiểm?

Vì SSTable bất biến, `DELETE`, ghi `null`, hay TTL hết hạn không xoá ngay mà tạo tombstone. Tombstone được giữ ít
nhất `gc_grace_seconds` (mặc định 10 ngày) để các replica đang offline kịp nhận lệnh xoá, nếu không dữ liệu cũ có
thể "sống lại" (zombie). Khi đọc, Cassandra phải quét qua tombstone; quá nhiều sẽ làm query chậm, cảnh báo ở 1.000
và lỗi ở 100.000 tombstone. Tránh bằng cách: không dùng Cassandra làm queue, không ghi null (bỏ cột), dùng TTL kèm
`TimeWindowCompactionStrategy` cho time-series, thiết kế partition sao cho xoá cả partition thay vì từng hàng, và
chạy repair định kỳ trong khoảng `gc_grace_seconds`.

## Mô tả cache-aside với Redis. Làm sao tránh cache stampede và dữ liệu cũ?

Cache-aside: đọc `GET product:{id}`; hit thì trả; miss thì đọc DB, `SET key value EX ttl`, rồi trả. Khi cập nhật:
ghi DB trước, sau đó **xoá** key cache (không ghi đè, để tránh race khi hai request ghi cache theo thứ tự sai).

- **Dữ liệu cũ**: TTL là lưới an toàn cuối; invalidate khi ghi; với yêu cầu chặt hơn có thể dùng CDC từ DB để xoá
  cache, hoặc "delete, sleep, delete" (double delete).
- **Stampede** (key nóng hết hạn, nhiều request cùng đánh DB): dùng lock `SET lock:key 1 NX EX 5` để chỉ một
  request nạp lại, các request khác chờ hoặc trả bản cũ; hoặc làm mới sớm theo xác suất; thêm jitter vào TTL.
- **Penetration** (key không tồn tại): cache giá trị rỗng với TTL ngắn hoặc dùng Bloom filter.

## Thiết kế rate limiter 100 request/phút cho mỗi API key bằng Redis.

Fixed window đơn giản nhất: `key = rl:{api_key}:{epoch_minute}`, `INCR key`, `EXPIRE key 60`, cho phép nếu giá trị
`<= 100`. Dùng `MULTI`/pipeline để hai lệnh đi cùng nhau. Nhược điểm: ở ranh giới phút client có thể gửi 200
request trong 2 giây.

Chính xác hơn là sliding window log bằng sorted set: `ZREMRANGEBYSCORE key 0 now-60s`, `ZCARD key`, nếu `< 100`
thì `ZADD key now request_id` và `EXPIRE key 60`. Để không có race giữa đếm và thêm, gói vào Lua script (`EVAL`) vì
Redis chạy script nguyên tử. Token bucket (hash `tokens`, `ts`) cho phép burst có kiểm soát. Với Redis Cluster, mọi
key của một client nằm cùng slot nhờ hash tag `rl:{api_key}`.

## Redis có bền vững không? So sánh RDB và AOF.

Redis là in-memory nhưng có persistence. **RDB** chụp snapshot theo chu kỳ (fork + ghi file), khởi động nhanh, file
gọn, nhưng mất dữ liệu kể từ snapshot cuối. **AOF** ghi mọi lệnh ghi vào log, `appendfsync everysec` mất tối đa
khoảng 1 giây, file lớn hơn và cần rewrite. Thường bật cả hai. Ngoài ra replication bất đồng bộ nên failover vẫn có
thể mất vài lần ghi. Vì thế Redis phù hợp làm cache, session, counter, không nên là nơi lưu duy nhất của dữ liệu
quan trọng như đơn hàng.

## Khi nào dùng graph database? Viết Cypher tìm sản phẩm thường được mua cùng.

Dùng graph khi truy vấn chính là đi theo quan hệ với độ sâu thay đổi: gợi ý, phát hiện gian lận (vòng chuyển tiền,
tài khoản dùng chung thiết bị), knowledge graph, phụ thuộc hệ thống. Graph DB dùng index-free adjacency nên mỗi
bước đi có chi phí hằng số, còn SQL cần self-JOIN bùng nổ theo độ sâu.

```cypher
MATCH (:Product {id: $pid})<-[:BOUGHT]-(c:Customer)-[:BOUGHT]->(o:Product)
WHERE o.id <> $pid
RETURN o.id AS product, count(DISTINCT c) AS shared_customers
ORDER BY shared_customers DESC
LIMIT 5
```

Không nên dùng graph cho aggregate toàn tập kiểu "doanh thu theo tháng" — việc đó thuộc về warehouse.

## So sánh DynamoDB với Cassandra.

Cả hai lấy cảm hứng từ Dynamo paper: partition key được hash, sort key (clustering key) trong partition, eventual
consistency mặc định, scale ngang. Khác biệt:

| | DynamoDB | Cassandra |
| --- | --- | --- |
| Vận hành | Fully managed, serverless | Tự vận hành (hoặc Astra, Keyspaces) |
| Chi phí | Theo RCU/WCU hoặc on-demand | Theo máy |
| Truy vấn | API GetItem/Query/Scan, PartiQL | CQL |
| Index phụ | GSI (eventual), LSI | SAI, materialized view |
| Mô hình | Single-table design phổ biến | Mỗi truy vấn một bảng |
| Multi-region | Global Tables | Multi-DC native |
| Giới hạn | Item 400 KB, partition 10 GB nếu có LSI | Partition nên dưới ~100 MB |

Chọn DynamoDB khi đang trên AWS và muốn không vận hành; Cassandra khi cần multi-cloud/on-prem, kiểm soát chi phí
ở quy mô lớn.

## Elasticsearch khác MongoDB thế nào? Có nên dùng ES làm database chính?

Elasticsearch là search engine dựa trên Lucene: tạo inverted index cho full-text, tính relevance (BM25), hỗ trợ
fuzzy, facet, aggregation nhanh. MongoDB là database đa dụng với CRUD, transaction, index B-tree, có text search
cơ bản (Atlas Search mạnh hơn). Không nên dùng ES làm system of record: không có transaction đa document, near
real-time (refresh khoảng 1 giây), mapping thay đổi thường cần reindex, từng có lịch sử mất dữ liệu khi
split-brain. Kiến trúc chuẩn: DB chính là nguồn sự thật, đẩy thay đổi sang ES qua CDC (Debezium → Kafka → ES sink)
và có thể reindex lại từ nguồn bất cứ lúc nào.

## Bạn đưa dữ liệu từ MongoDB vào warehouse thế nào? Các vấn đề cần xử lý?

Hai cách: batch export (query theo `updated_at` hoặc `_id` tăng dần, `mongoexport`, Spark connector) hoặc CDC
bằng change streams / Debezium MongoDB connector → Kafka → lake. Vấn đề:

- **Schema drift**: trường mới, kiểu thay đổi (`price` lúc string lúc number). Cần land raw JSON ở bronze, ép kiểu
  có kiểm soát ở silver, và cảnh báo khi xuất hiện trường lạ.
- **Nested data**: mảng `items` phải bung thành bảng con (`order_items`) với khoá cha; object lồng thì flatten.
- **Delete**: batch export không thấy bản ghi đã xoá; CDC hoặc soft delete mới bắt được.
- **Incremental**: cần trường `updated_at` có index hoặc resume token của change stream; xử lý idempotent bằng
  MERGE theo `_id`.
- **Kiểu đặc thù**: `ObjectId`, `Decimal128`, `Date` timezone UTC.

## Thiết kế lưu trữ cho tính năng "theo dõi đơn hàng" của Olist: 50 triệu sự kiện/ngày, khách xem lịch sử đơn, ops xem đơn trễ theo bang.

Hai truy vấn khác nhau nên tách store theo vai trò:

1. **Lịch sử theo đơn** (đọc nhiều, độ trễ thấp): Cassandra bảng
   `order_events_by_order ((order_id), event_time DESC)` với TTL 180 ngày và TWCS. Ghi `LOCAL_QUORUM`, đọc
   `LOCAL_ONE` hoặc `LOCAL_QUORUM` tuỳ yêu cầu. Mỗi đơn chỉ vài chục sự kiện nên partition nhỏ.
2. **Trạng thái hiện tại** cho trang khách: Redis hash `order:{id}` cập nhật mỗi sự kiện, TTL vài ngày.
3. **Đơn trễ theo bang** (phân tích, cập nhật vài phút một lần là đủ): stream sự kiện qua Kafka vào lakehouse/
   warehouse, tính bảng `late_orders_by_state`; nếu cần gần real-time, thêm bảng Cassandra
   `late_orders_by_state_day ((state, day), promised_date, order_id)` do một consumer ghi khi phát hiện trễ.

Nguồn chung là topic Kafka `order-events`; mọi consumer idempotent (khoá là `order_id + event_time + type`).
Cần nêu đánh đổi: dữ liệu trùng lặp ở nhiều store, độ trễ đồng bộ, chi phí vận hành nhiều hệ thống so với giữ
PostgreSQL + partitioning nếu khối lượng nhỏ hơn dự kiến.

## Azure Cosmos DB có năm consistency level. Bạn chọn mức nào cho giỏ hàng và cho bảng xếp hạng sản phẩm? Vì sao?

- **Giỏ hàng**: **Session** (mặc định). Người dùng phải thấy ngay món vừa thêm (read-your-writes) và không thấy
  giỏ "lùi" về trạng thái cũ (monotonic reads), nhưng không cần người khác thấy tức thì. Strong là thừa và làm
  tăng độ trễ ghi khi có nhiều region.
- **Bảng xếp hạng sản phẩm**: **Eventual** hoặc **Consistent prefix**. Chậm vài giây không sao; consistent prefix
  tránh thấy cập nhật sai thứ tự. Rẻ RU nhất.
- Nêu thêm: **Bounded staleness** khi nghiệp vụ cần biết trễ tối đa (vd. tồn kho hiển thị trễ không quá 5 giây);
  **Strong** chỉ khi thật sự cần linearizable (số dư, đặt chỗ duy nhất) và chấp nhận chi phí. Ánh xạ về lý thuyết:
  đây chính là phổ consistency model và đánh đổi EL/EC của PACELC.

## Nguồn dữ liệu là CouchDB (app mobile offline-first). Bạn nạp tăng dần vào lakehouse thế nào?

Dùng **`_changes` feed** với tham số `since=<last_seq>` (lưu checkpoint `last_seq` sau mỗi lần nạp thành công),
`include_docs=true` để lấy document. Ghi vào bronze dạng append (giữ `_id`, `_rev`, `seq`), rồi silver **MERGE theo
`_id`**, lấy revision mới nhất; document có `_deleted: true` thì xoá mềm/xoá ở silver. Lưu ý: replication
master-master nên có thể có **conflict revision** (`conflicts=true` để thấy), cần quy tắc hoà giải hoặc giữ revision
thắng của CouchDB; feed có thể trả lại thay đổi đã thấy nên MERGE phải idempotent; với khối lượng lớn dùng
`feed=continuous` hoặc connector (Kafka Connect) thay vì polling.
