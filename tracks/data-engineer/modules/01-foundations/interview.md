# Câu hỏi phỏng vấn: Nền tảng kỹ thuật

## Generator trong Python là gì, và vì sao Data Engineer cần nó?

Generator là hàm dùng `yield`, trả về một iterator sinh từng phần tử khi được yêu cầu (lazy
evaluation). Nó giữ trạng thái giữa các lần `next()` và không tạo cả danh sách trong bộ nhớ.

Với Data Engineer, dữ liệu thường lớn hơn RAM. Đọc file 50 GB bằng `list(csv.reader(f))` sẽ sập,
còn `for row in csv.reader(f)` hoặc một generator tự viết chỉ giữ một dòng (hoặc một batch) tại một
thời điểm, bộ nhớ O(1). Generator cũng ghép thành pipeline: `read → filter → transform → batch →
write`, mỗi bước là một generator, dữ liệu chảy qua từng phần tử.

Lưu ý: generator chỉ duyệt được một lần; muốn duyệt lại phải tạo mới. Đóng file đúng lúc bằng
`with` bên trong generator.

## Bạn xử lý một file CSV 30 GB trên máy 8 GB RAM như thế nào?

Có vài cách, chọn theo việc cần làm:

1. **Streaming bằng Python thuần** (`csv` + generator) khi logic theo từng dòng: validate, lọc, ghi
   sang DB theo batch.
2. **pandas với `chunksize`**: `for chunk in pd.read_csv(path, chunksize=200_000)`; tổng hợp từng
   chunk rồi gộp kết quả (chỉ được với phép gộp kết hợp được như sum, count, min, max; mean thì
   giữ sum và count).
3. **DuckDB hoặc polars lazy**: `duckdb.sql("SELECT state, SUM(price) FROM 'f.csv' GROUP BY 1")`
   tự stream và spill ra đĩa, thường nhanh nhất. Tiện thể chuyển sang Parquet để lần sau đọc nhanh
   hơn nhiều.
4. Nếu lặp lại thường xuyên hoặc lớn hơn nữa: Spark, hoặc nạp vào warehouse.

Thêm: chỉ đọc cột cần (`usecols`), khai báo `dtype` (category cho cột ít giá trị), nén đầu vào.

## Khác nhau giữa ROW_NUMBER, RANK và DENSE_RANK? Viết query lấy đơn hàng mới nhất của mỗi khách.

Khi có giá trị bằng nhau: `ROW_NUMBER` đánh số liên tục không trùng (thứ tự giữa các dòng bằng
nhau là tuỳ ý trừ khi thêm cột phá hoà), `RANK` cho cùng hạng và nhảy số (1, 1, 3), `DENSE_RANK`
cho cùng hạng không nhảy (1, 1, 2).

```sql
SELECT *
FROM (
    SELECT o.*,
           ROW_NUMBER() OVER (PARTITION BY customer_id
                              ORDER BY order_purchase_timestamp DESC, order_id) AS rn
    FROM orders o
) t
WHERE rn = 1;
```

Dùng `ROW_NUMBER` vì cần đúng một dòng mỗi khách; thêm `order_id` vào `ORDER BY` để kết quả xác
định (deterministic) khi trùng thời gian. Trên DuckDB/Snowflake/BigQuery có thể viết gọn bằng
`QUALIFY rn = 1`.

## Tính running total và moving average 7 ngày. Khác nhau giữa ROWS và RANGE?

```sql
SELECT d, revenue,
       SUM(revenue) OVER (ORDER BY d ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running,
       AVG(revenue) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma7
FROM daily_revenue;
```

`ROWS` đếm theo dòng vật lý; `RANGE` theo giá trị của cột `ORDER BY`, các dòng cùng giá trị (peer)
được tính chung. Frame mặc định khi có `ORDER BY` là `RANGE ... CURRENT ROW`, nên nếu có hai dòng
cùng ngày thì cả hai nhận cùng running total. Một bẫy nữa: `ROWS BETWEEN 6 PRECEDING` chỉ đúng
"7 ngày" khi không thiếu ngày; nếu có ngày trống, LEFT JOIN với date spine trước, hoặc dùng
`RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW`.

## CTE đệ quy hoạt động thế nào? Cho một ví dụ thực tế.

CTE đệ quy gồm phần anchor (chạy một lần, tạo tập dòng ban đầu) `UNION ALL` phần recursive (tham
chiếu chính CTE). Engine lặp: lấy các dòng mới nhất, chạy phần recursive trên chúng, thêm kết quả,
cho tới khi phần recursive không sinh dòng nào.

Ví dụ: cây danh mục sản phẩm (`category_id`, `parent_id`), cần tính đường dẫn đầy đủ và tổng doanh
thu của mỗi danh mục gồm cả danh mục con; hoặc sinh date spine để báo cáo không bỏ sót ngày không có
đơn; hoặc duyệt quan hệ "nhân viên → quản lý".

Rủi ro: dữ liệu có chu trình làm lặp vô hạn; phòng bằng giới hạn độ sâu hoặc lưu mảng các nút đã đi
qua và loại nút lặp (PostgreSQL 14 có mệnh đề `CYCLE`).

## Giải thích `set -euo pipefail` trong Bash.

- `-e`: dừng script khi một lệnh trả mã khác 0 (thay vì chạy tiếp với trạng thái hỏng).
- `-u`: dùng biến chưa định nghĩa là lỗi (tránh `rm -rf "$DIR/"*` với `DIR` rỗng).
- `-o pipefail`: mã thoát của pipeline là mã khác 0 của lệnh cuối cùng thất bại, không chỉ của lệnh
  cuối. Không có nó, `curl ... | gzip > f.gz` vẫn "thành công" dù curl lỗi.

Kèm theo: quote mọi biến, `trap 'cleanup' EXIT` để dọn file tạm, ghi lỗi ra stderr (`>&2`), trả
exit code có ý nghĩa để scheduler phát hiện thất bại. `-e` có ngoại lệ (lệnh trong `if`, `&&`,
`||`), nên kiểm tra lỗi quan trọng một cách tường minh.

## Đếm số đơn theo trạng thái trong một CSV chỉ bằng dòng lệnh.

```bash
tail -n +2 orders.csv | cut -d, -f3 | sort | uniq -c | sort -rn
```

`tail -n +2` bỏ header, `cut` lấy cột 3, `sort | uniq -c` đếm (uniq chỉ gộp dòng liền kề nên phải
sort trước), `sort -rn` xếp giảm dần. Với awk: `awk -F, 'NR>1 {c[$3]++} END {for (k in c) print k, c[k]}'`.
Hạn chế: không xử lý CSV có dấu phẩy trong ngoặc kép; khi đó dùng `csvkit`, `mlr` hoặc
`duckdb -c "SELECT order_status, count(*) FROM 'orders.csv' GROUP BY 1"`.

## Merge và rebase khác nhau thế nào? Team bạn nên dùng gì?

`merge` tạo merge commit nối hai lịch sử, giữ nguyên commit gốc. `rebase` "phát lại" commit của
nhánh lên đỉnh nhánh khác, tạo commit mới (SHA mới), lịch sử thẳng.

Quy tắc thực tế: rebase nhánh cá nhân lên `main` để cập nhật (`git pull --rebase`), không rebase
nhánh đã chia sẻ vì sẽ viết lại lịch sử người khác đang dựa vào. Gộp PR vào `main` bằng squash merge
(mỗi PR một commit, dễ revert) hoặc merge commit. Với team data, GitHub flow/trunk-based (nhánh ngắn,
PR nhỏ, CI chạy test SQL/dbt, `main` luôn deploy được) thường đủ và đơn giản hơn Git flow.

## Lỡ commit mật khẩu database lên GitHub. Bạn làm gì?

1. **Đổi (rotate) mật khẩu ngay**: coi như đã lộ, vì bot quét GitHub trong vài phút, và có thể đã
   có người clone/fork.
2. Kiểm tra log truy cập DB xem có truy cập lạ.
3. Xoá khỏi lịch sử bằng `git filter-repo` hoặc BFG, force push, báo mọi người clone lại. Đây là
   bước phụ, không thay được bước 1.
4. Phòng ngừa: `.env` trong `.gitignore`, secret manager (Vault, AWS Secrets Manager), pre-commit
   hook quét bí mật (gitleaks, detect-secrets), GitHub secret scanning.

## Chuyện gì xảy ra khi bạn gọi `requests.get("https://api.example.com/orders")`?

1. Phân giải DNS `api.example.com` thành IP (cache cục bộ, resolver, theo TTL).
2. Mở kết nối TCP tới IP cổng 443 (bắt tay 3 bước SYN, SYN-ACK, ACK).
3. Bắt tay TLS: thoả thuận thuật toán, server gửi chứng chỉ, client kiểm tra chuỗi CA và tên miền,
   tạo khoá phiên.
4. Gửi HTTP request (method, path, header như `Host`, `Authorization`, `Accept`), qua kênh mã hoá.
5. Server trả status code, header, body. `requests` giải mã, trả `Response`.
6. Kết nối có thể được giữ (keep-alive) để tái dùng nếu dùng `Session`.

Mỗi bước có lỗi riêng: DNS (`NameResolutionError`), TCP (`Connection refused` hoặc timeout), TLS
(lỗi chứng chỉ), HTTP (4xx/5xx). Biết bước nào hỏng giúp debug nhanh. Và luôn đặt `timeout`, vì mặc
định `requests` chờ vô hạn.

## Pipeline gọi API bị lỗi 429 và 503 thất thường. Bạn thiết kế client thế nào?

- **Phân loại lỗi**: retry 429, 5xx, lỗi kết nối, timeout; không retry 400/401/403/404 (lỗi thật).
- **Exponential backoff + jitter**: chờ 1, 2, 4, 8… giây nhân hệ số ngẫu nhiên, có trần; tôn trọng
  header `Retry-After` của 429.
- **Giới hạn số lần retry** rồi fail rõ ràng (exit code ≠ 0) để orchestrator cảnh báo.
- **Rate limit chủ động**: token bucket để không vượt quota.
- **Timeout** cho connect và read.
- **Idempotency**: request ghi (POST) dùng idempotency key để retry không tạo bản ghi trùng; bên nhận
  dữ liệu thì upsert theo khoá.
- **Phân trang theo cursor** và lưu checkpoint (cursor cuối đã xử lý) để chạy lại tiếp từ chỗ dừng.
- **Circuit breaker** nếu dịch vụ sập lâu: ngừng gọi một thời gian thay vì dồn tải.

## TCP và UDP khác nhau thế nào? Hệ dữ liệu nào dùng gì?

TCP hướng kết nối, đảm bảo đến nơi, đúng thứ tự, không trùng, có kiểm soát luồng và tắc nghẽn; đổi
lại có độ trễ bắt tay và overhead. UDP không kết nối, không đảm bảo, nhẹ và nhanh.

Hầu hết hệ dữ liệu dùng TCP: giao thức PostgreSQL, MySQL, Kafka, HTTP/1.1 và HTTP/2, gRPC. UDP dùng
cho DNS (truy vấn nhỏ), metrics kiểu StatsD (mất vài điểm không sao), streaming media, và QUIC/HTTP3
(xây cơ chế tin cậy riêng trên UDP).

## Replication đồng bộ và bất đồng bộ khác nhau thế nào? Replication lag gây ra vấn đề gì?

Đồng bộ: leader chờ follower xác nhận rồi mới báo ghi thành công. Không mất dữ liệu khi leader chết,
nhưng ghi chậm hơn và một follower chết có thể chặn ghi. Bất đồng bộ: leader trả lời ngay, follower
chép sau. Nhanh, nhưng leader chết có thể mất các ghi chưa kịp chép, và follower bị trễ.

Replication lag gây: đọc từ replica không thấy dữ liệu mình vừa ghi (vi phạm read-your-writes), đọc
hai lần từ hai replica khác nhau thấy dữ liệu "lùi về quá khứ". Với Data Engineer, gặp khi extract từ
read replica: dữ liệu có thể trễ vài giây đến vài phút, nên watermark incremental load phải chừa
khoảng an toàn (lookback window). Thực tế thường chọn semi-synchronous: một follower đồng bộ, còn
lại bất đồng bộ.

## Hash partitioning và range partitioning: chọn thế nào? Data skew là gì?

Hash partitioning phân bố đều theo `hash(key)`, tốt cho truy cập theo khoá cụ thể, nhưng truy vấn
khoảng phải quét mọi partition. Range partitioning (theo ngày, theo khoảng id) cho phép bỏ qua
partition không liên quan (partition pruning), hợp với dữ liệu thời gian trong warehouse, nhưng dễ
nóng ở partition mới nhất.

Data skew: một vài key chiếm phần lớn dữ liệu (một seller cực lớn, rất nhiều `NULL`), làm một
partition/task chạy lâu trong khi phần còn lại xong từ sớm. Xử lý: salting key (thêm hậu tố ngẫu
nhiên rồi gộp hai bước), tách key nóng xử lý riêng, broadcast bảng nhỏ khi join, chọn khoá phân chia
có cardinality cao.

## Vì sao `hash(key) % N` không tốt khi thêm máy? Consistent hashing giải quyết thế nào?

Đổi N thành N+1 làm `hash % N` đổi với gần như mọi key, nên gần như toàn bộ dữ liệu phải di chuyển.
Consistent hashing đặt cả nút và key lên một vòng băm (0 đến 2^32), key thuộc nút đầu tiên theo
chiều kim đồng hồ. Thêm một nút chỉ lấy phần key nằm giữa nó và nút liền trước, nên chỉ khoảng
`K/N` key di chuyển. Mỗi nút vật lý có nhiều virtual node để phân bố đều và để nút mạnh nhận nhiều
vnode hơn. Replication: key được chép sang R nút phân biệt tiếp theo trên vòng. Dynamo, Cassandra,
Riak dùng cách này.

## Giải thích quorum R + W > N. Chọn N, R, W thế nào?

N là số bản sao, W là số nút phải xác nhận ghi, R là số nút được hỏi khi đọc. `R + W > N` đảm bảo
tập đọc và tập ghi giao nhau ít nhất một nút, nên đọc gặp ít nhất một bản mới nhất (dùng version
hoặc timestamp để chọn bản mới). N=3, W=2, R=2 là cấu hình cân bằng, chịu được một nút chết cho cả
đọc và ghi. Ưu tiên ghi nhanh: W=1, R=3. Ưu tiên đọc nhanh: W=3, R=1 (nhưng một nút chết là không
ghi được). Quorum không đảm bảo linearizability tuyệt đối (ghi đồng thời, sloppy quorum, lỗi một
phần), nên Cassandra cho chọn consistency level theo từng truy vấn.

## CAP theorem nói gì, và vì sao "chọn 2 trong 3" là cách nói sai lệch?

Khi có network partition (các nút không liên lạc được với nhau), hệ thống phải chọn: từ chối một số
request để giữ dữ liệu nhất quán (CP), hoặc vẫn phục vụ và chấp nhận dữ liệu có thể cũ/xung đột
(AP). "Chọn 2 trong 3" sai lệch vì P không phải lựa chọn: partition mạng sẽ xảy ra, nên lựa chọn
thật chỉ xuất hiện *khi* có partition. Lúc mạng bình thường, hệ thống có thể vừa C vừa A. PACELC bổ
sung đánh đổi lúc bình thường: latency hay consistency. Ví dụ: hệ ngân hàng ưu tiên C; giỏ hàng,
lượt like ưu tiên A.

## Thiết kế job hằng ngày nạp đơn hàng từ API đối tác vào PostgreSQL. Bạn quan tâm những gì?

- **Extract**: phân trang cursor, timeout, retry backoff + jitter, rate limit; lấy incremental theo
  `updated_at >= watermark - lookback` để không sót bản ghi đến trễ; lưu watermark sau khi ghi
  thành công, không phải trước.
- **Raw zone**: lưu response thô (JSON/Parquet theo ngày) vào object storage để replay khi logic
  đổi, không phải gọi lại API.
- **Validate**: schema, kiểu, giá trị bắt buộc; dòng lỗi vào bảng reject kèm lý do, cảnh báo nếu tỉ
  lệ lỗi vượt ngưỡng.
- **Load idempotent**: staging table, rồi `INSERT ... ON CONFLICT (order_id) DO UPDATE` trong một
  transaction; chạy lại cùng ngày không nhân đôi.
- **Vận hành**: CLI có tham số ngày (để backfill), logging có cấu trúc, exit code, metric (số dòng,
  thời gian), alert; chạy bằng Airflow với retry và SLA.
- **Bảo mật**: token trong secret manager, không log dữ liệu nhạy cảm.
- **Code**: Git, PR, test với dữ liệu mẫu và mock API, CI.

## Vì sao mã zip và số tiền không nên được đọc như mọi số khác?

Zip là định danh: "01000" khác "1000" ở cách biểu diễn cần giữ, không dùng để cộng/trừ.
Tiền cần độ chính xác theo đơn vị đã thống nhất: dùng Decimal hoặc số nguyên cents; chỉ đổi sang
float khi đã hiểu giới hạn. Kiểm giá hữu hạn để NaN/Infinity không lọt vào phép tổng.

## Một context manager có luôn đóng connection database không?

Không. Phải đọc contract của đối tượng. Với sqlite3, with connection quản commit/rollback nhưng
không tự đóng connection. Có thể dùng contextlib.closing cho vòng đời và with con cho transaction.
Test cả nhánh exception để chắc rollback và tài nguyên được giải phóng.

## Bạn cần đếm số khách unique mỗi ngày, mỗi tuần và mỗi tháng trên 2 tỷ event. Làm thế nào cho rẻ?

`COUNT(DISTINCT customer_id)` chính xác nhưng phải giữ toàn bộ tập khoá trong bộ nhớ (hoặc shuffle cả
tập), và kết quả theo ngày **không cộng được** thành theo tuần vì khách quay lại bị đếm nhiều lần. Muốn
có số tuần/tháng lại phải quét lại dữ liệu thô.

Nếu chấp nhận sai số 1–2%, dùng **HyperLogLog**: mỗi ngày lưu một sketch vài KB (BigQuery
`HLL_COUNT.INIT`, Spark/Databricks `hll_sketch_agg`, Druid/Pinot sketch) trong bảng aggregate. Số tuần
là merge 7 sketch (max từng register), số tháng là merge 30 sketch, không đụng lại event thô. Sai số chuẩn
khoảng 1,04 chia căn số register, nên p = 14 (16.384 register) cho khoảng 0,8%.

Cần ghi rõ trên dashboard rằng số là xấp xỉ, và giữ `COUNT(DISTINCT)` chính xác cho chỗ cần đối soát
(vd. số khách được trả thưởng).

## Vì sao một Data Engineer viết Python vẫn nên đọc được Java/Scala và hiểu JVM?

Spark, Kafka, Flink, Trino đều chạy trên JVM. PySpark chỉ là lớp gọi sang driver JVM qua Py4J, nên lỗi
production thường là stack trace Java: `OutOfMemoryError: Java heap space`, `GC overhead limit exceeded`,
`ClassNotFoundException` vì thiếu JAR connector hoặc lệch phiên bản Scala (`_2.12` vs `_2.13`). Đọc được
dòng `Caused by:` cuối và hiểu heap/GC giúp sửa đúng chỗ: tăng `spark.executor.memory` hay
`memoryOverhead`, giảm kích thước partition, bỏ Python UDF.

Ngoài ra, connector Kafka Connect, UDF cho Trino/Hive và job Flink độ trễ thấp thường viết bằng Java;
tài liệu nâng cao của Spark viết bằng Scala. Go thì gặp ở tầng hạ tầng (Kubernetes, Terraform,
Prometheus exporter). Không cần thành thạo hết, nhưng đọc được là đủ để tự debug.
