# Câu hỏi phỏng vấn: Data Warehouse & Lakehouse

## OLTP khác OLAP thế nào? Vì sao không chạy báo cáo thẳng trên database của ứng dụng?

OLTP phục vụ giao dịch: nhiều truy vấn nhỏ, đọc/ghi vài dòng theo khoá, cần độ trễ thấp và tính nhất quán từng giao
dịch. Lưu trữ theo dòng, mô hình chuẩn hoá 3NF. OLAP phục vụ phân tích: ít truy vấn nhưng mỗi truy vấn quét hàng triệu
dòng, chỉ vài cột, nhiều phép tổng hợp. Lưu theo cột, mô hình denormalized (star schema).

Chạy báo cáo nặng trên OLTP có ba vấn đề: (1) tranh tài nguyên với ứng dụng, làm chậm khách hàng đang đặt hàng;
(2) lưu trữ theo dòng nên quét chậm; (3) dữ liệu phân tích cần gộp từ nhiều nguồn, giữ lịch sử, làm sạch, điều mà
database ứng dụng không làm. Cách phổ biến là sao chép (batch hoặc CDC) sang warehouse/lakehouse. Read replica là giải
pháp tạm cho truy vấn nhẹ, nhưng vẫn là lưu trữ dòng và chỉ có một nguồn.

## Vì sao lưu trữ dạng cột lại nhanh cho truy vấn phân tích?

- **Column pruning**: chỉ đọc các cột truy vấn cần. Bảng 50 cột mà truy vấn dùng 3 thì I/O giảm khoảng 15 lần.
- **Nén tốt**: giá trị cùng kiểu, nhiều lặp lại đứng cạnh nhau, áp được dictionary encoding, run-length encoding, delta
  encoding rồi nén tổng quát (zstd, snappy). Tỉ lệ nén 5–10 lần là bình thường, nghĩa là ít byte phải đọc hơn nữa.
- **Thống kê min/max theo khối**: bỏ qua cả khối dữ liệu không thoả điều kiện lọc.
- **Vectorized execution**: xử lý cả lô giá trị cùng kiểu một lúc, tận dụng cache CPU và SIMD.

Đánh đổi: ghi hay cập nhật một dòng lẻ đắt (phải chạm nhiều column chunk), nên kho dạng cột thường ghi theo lô lớn và
không hợp với OLTP.

## Mô tả cấu trúc một tệp Parquet. Predicate pushdown hoạt động thế nào?

Tệp Parquet chia thành các **row group** (lát ngang, thường 128 MB – 1 GB). Trong mỗi row group, dữ liệu mỗi cột là một
**column chunk**, chia tiếp thành **page** (đơn vị encode/nén). Cuối tệp là **footer** chứa schema, vị trí các chunk và
**statistics** (min, max, null_count) của từng column chunk.

Reader đọc footer trước. Với `WHERE price > 1000`, nó so với `max(price)` của từng row group, row group nào có max ≤ 1000
thì bỏ qua không đọc. Kết hợp với column pruning, truy vấn có thể chỉ đọc một phần rất nhỏ của tệp. Pushdown hiệu quả
khi dữ liệu được sắp xếp/cluster theo cột lọc; nếu dữ liệu ngẫu nhiên thì mọi row group đều có min/max trải rộng và
không bỏ qua được gì. Parquet còn hỗ trợ page index và bloom filter cho điều kiện bằng trên cột cardinality cao.

## So sánh cách tiếp cận Kimball và Inmon.

**Inmon (top-down)**: xây enterprise data warehouse chuẩn hoá 3NF cho toàn công ty, là nguồn sự thật duy nhất, rồi sinh
các data mart phòng ban từ đó. Nhất quán, ít dư thừa, nhưng tốn thời gian thiết kế, lâu mới có giá trị.

**Kimball (bottom-up)**: xây trực tiếp các star schema theo quy trình nghiệp vụ, nối với nhau qua conformed dimension
theo bus matrix. Nhanh có giá trị, dễ hiểu với người dùng BI, nhưng cần kỷ luật để không mỗi mart một định nghĩa.

Trong thực tế hiện đại, phổ biến nhất là lai: lớp staging/silver gần với nguồn (hoặc chuẩn hoá vừa phải), lớp mart/gold
theo Kimball. Data Vault là lựa chọn cho lớp lõi khi nguồn thay đổi liên tục và yêu cầu audit cao.

## Grain của bảng fact là gì? Vì sao nó quan trọng?

Grain là định nghĩa chính xác một dòng fact đại diện cho cái gì, vd. "một item trong một đơn hàng" hay "một đơn hàng"
hay "tồn kho của một sản phẩm cuối mỗi ngày". Phải khai báo grain *trước* khi chọn dimension và measure.

Quan trọng vì: (1) quyết định dimension nào gắn được (grain đơn hàng thì không gắn được `product`); (2) quyết định
measure nào cộng được đúng (đặt `freight_value` cấp đơn vào bảng grain item thì cộng sẽ bị nhân bản); (3) đổi grain sau
khi đã có báo cáo là rất đắt. Nguyên tắc Kimball: chọn grain **chi tiết nhất** có thể (atomic), vì tổng hợp lên luôn
được, còn tách xuống thì không. Với Olist, `fact_order_items` ở grain item là lựa chọn tự nhiên.

## Surrogate key là gì, vì sao dùng thay natural key? Unknown member dùng để làm gì?

Surrogate key là khoá nhân tạo (thường số nguyên tăng dần hoặc hash) do warehouse sinh, khác với natural key từ nguồn
(`customer_id`). Lý do dùng:

- Cần cho **SCD Type 2**: một `customer_id` có nhiều phiên bản lịch sử, mỗi phiên bản một surrogate key.
- Tách warehouse khỏi nguồn: nguồn đổi hệ thống, tái dùng mã, gộp nhiều nguồn trùng mã vẫn không ảnh hưởng.
- Join trên số nguyên nhỏ nhanh hơn chuỗi dài.

**Unknown member** là một dòng đặc biệt trong dimension (thường key 0 hoặc -1, giá trị "unknown") để fact có khoá
không tìm thấy trong dimension (dữ liệu bẩn, late-arriving dimension) vẫn được nạp. Nhờ vậy tổng số liệu của mart khớp
nguồn và BI hiện rõ nhóm "unknown" để đi sửa, thay vì `INNER JOIN` âm thầm làm rơi dòng.

## Kiến trúc medallion là gì? Mỗi lớp chịu trách nhiệm gì?

- **Bronze**: dữ liệu thô gần nguyên vẹn từ nguồn, append-only, thêm metadata (thời điểm nạp, tệp/batch nguồn). Mục đích:
  lưu bằng chứng gốc, cho phép replay.
- **Silver**: ép kiểu, làm sạch, chuẩn hoá giá trị, khử trùng lặp (giữ phiên bản mới nhất), nối các nguồn; là "trạng thái
  hiện tại" đáng tin của từng thực thể. Dòng lỗi nên đưa vào quarantine.
- **Gold**: dữ liệu theo nhu cầu nghiệp vụ: star schema, bảng tổng hợp, metric, feature.

Lợi ích: tách trách nhiệm dễ test, sửa logic thì chạy lại từ bronze, phục vụ được nhiều đối tượng (DS dùng silver, BI
dùng gold). Đánh đổi: lưu nhiều bản, thêm độ trễ và chi phí; với dữ liệu nhỏ có thể gộp bớt lớp. Medallion là tên gọi
của Databricks cho kiến trúc layered vốn có từ lâu (staging → core → mart).

## Partitioning khác clustering thế nào? Chọn cột partition ra sao?

**Partitioning** chia bảng thành các phần vật lý tách biệt (thư mục `year=2018/month=3/` hoặc partition của BigQuery) theo
giá trị một cột; truy vấn lọc theo cột đó bỏ qua cả partition (partition pruning). **Clustering** (sort key, Z-order)
sắp xếp dữ liệu *bên trong* partition để min/max của từng tệp/khối hẹp lại, giúp bỏ qua khối theo các cột khác.

Chọn cột partition: hay xuất hiện trong `WHERE`, cardinality thấp–vừa, phân bố đều, mỗi partition đủ lớn (hàng trăm MB+).
Ngày/tháng là lựa chọn phổ biến nhất. Không partition theo cột cardinality cao (`customer_id`) vì sinh vô số tệp nhỏ.
Cột cardinality cao mà hay lọc thì dùng clustering. Iceberg có **hidden partitioning** (partition theo `days(ts)` mà người
dùng chỉ cần lọc `ts`) và cho phép đổi cách partition mà không ghi lại dữ liệu cũ.

## Small files problem là gì? Xử lý thế nào?

Khi bảng gồm rất nhiều tệp nhỏ (KB–vài MB), chi phí liệt kê, mở tệp, đọc footer và request lên object storage lấn át việc
đọc dữ liệu thật; metadata (Hive metastore, Delta log) cũng phình to. Nguyên nhân thường gặp: streaming/micro-batch ghi
liên tục, partition quá mịn, nhiều task Spark mỗi task ghi một tệp vào mỗi partition.

Cách xử lý: **compaction** định kỳ (`OPTIMIZE` của Delta, `rewrite_data_files` của Iceberg, `optimize.compact()` của
delta-rs), partition thô hơn, `repartition`/`coalesce` trước khi ghi, bật optimized write/auto compaction, và `VACUUM`
để dọn tệp cũ. Mục tiêu thường là tệp 128 MB – 1 GB.

## Data lake khác lakehouse ở đâu? Table format (Delta, Iceberg, Hudi) giải quyết vấn đề gì?

Data lake là thư mục tệp trên object storage với schema-on-read: rẻ, mở, linh hoạt nhưng thiếu ACID (job chết giữa chừng
để lại dữ liệu dở dang, hai writer giẫm nhau), không update/delete theo dòng, không enforce schema, liệt kê tệp chậm.

Lakehouse giữ dữ liệu ở định dạng mở trên object storage nhưng thêm **table format**: một lớp metadata có giao dịch
ghi lại bảng gồm những tệp nào ở mỗi version. Từ đó có: ACID và snapshot isolation, `UPDATE/DELETE/MERGE`, schema
enforcement và evolution, time travel, thống kê tập trung để pruning, và nhiều engine (Spark, Trino, DuckDB, Snowflake)
dùng chung một bản dữ liệu thay vì copy lake → warehouse.

## Delta Lake đảm bảo ACID trên S3 như thế nào? Time travel hoạt động ra sao?

Bảng Delta = tệp Parquet bất biến + `_delta_log/` chứa commit đánh số liên tiếp. Ghi: viết tệp Parquet mới trước, sau đó
tạo tệp commit version N+1 liệt kê `add`/`remove`. Commit là nguyên tử nhờ thao tác "put-if-absent": nếu hai writer cùng
tạo version N+1, chỉ một bên thành công; bên kia đọc commit mới, kiểm tra xung đột (có đụng cùng tệp/partition không) rồi
thử lại với N+2 (optimistic concurrency). Reader đọc log tới một version nên luôn thấy snapshot nhất quán. Trên S3 trước
đây không có put-if-absent nên cần locking provider (DynamoDB); nay S3 đã hỗ trợ conditional write.

Time travel: vì `UPDATE/DELETE/MERGE` không sửa tệp cũ mà ghi tệp mới và đánh dấu tệp cũ `remove`, tệp cũ vẫn còn trên
storage. Đọc version cũ là áp log tới version đó. `VACUUM` xoá tệp đã remove quá thời gian retention (mặc định 7 ngày);
sau đó không quay về được nữa. Ứng dụng: audit, tái lập kết quả ML, khôi phục sau khi ghi nhầm.

## So sánh copy-on-write và merge-on-read.

- **Copy-on-write (COW)**: khi cập nhật/xoá vài dòng, ghi lại toàn bộ tệp chứa các dòng đó. Ghi chậm, write amplification
  cao, nhưng đọc nhanh vì tệp luôn "sạch". Hợp với bảng đọc nhiều, cập nhật ít, batch.
- **Merge-on-read (MOR)**: ghi thay đổi ra tệp nhỏ riêng (delta log của Hudi, delete files của Iceberg, deletion vectors
  của Delta); lúc đọc mới gộp. Ghi nhanh, hợp upsert tần suất cao/streaming, nhưng đọc chậm dần nên cần compaction định kỳ.

Chọn theo tỉ lệ đọc/ghi và yêu cầu độ trễ. Hudi nổi tiếng với MOR cho CDC; Delta và Iceberg hiện hỗ trợ cả hai.

## So sánh BigQuery, Snowflake và Redshift. Khi nào chọn cái nào?

Cả ba là warehouse cột, MPP, tách storage và compute ở mức độ khác nhau.

- **BigQuery**: serverless hoàn toàn, không quản lý cụm; tính theo byte quét (on-demand) hoặc slot. Hợp khi đã ở GCP,
  khối lượng truy vấn không đều, muốn vận hành tối thiểu. Phải cẩn thận chi phí `SELECT *`, luôn partition + cluster.
- **Snowflake**: chạy trên cả AWS/GCP/Azure; virtual warehouse co giãn độc lập, auto-suspend; mạnh về data sharing,
  zero-copy clone, time travel. Hợp đa cloud, nhiều nhóm cần cô lập tài nguyên, chia sẻ dữ liệu với đối tác.
- **Redshift**: gắn sâu AWS; bản provisioned cần chọn node, sort key, dist key; có Serverless và Spectrum đọc S3. Hợp khi
  hệ sinh thái AWS, tải ổn định dự đoán được.

Thêm Databricks SQL nếu đã dùng lakehouse Delta và Spark. Tiêu chí chọn thực tế: cloud đang dùng, mô hình chi phí
khớp kiểu tải, kỹ năng đội, nhu cầu định dạng mở (Iceberg/Delta) để tránh lock-in.

## Data mesh là gì? Khi nào không nên áp dụng?

Data mesh là mô hình tổ chức phi tập trung với 4 nguyên tắc: domain ownership (domain nghiệp vụ sở hữu dữ liệu phân tích
của mình), data as a product (có chủ, SLA, tài liệu, chất lượng, dễ tìm), self-serve platform (đội platform cung cấp hạ
tầng chung), federated computational governance (chuẩn chung được tự động hoá). Nó giải quyết cổ chai của đội data
trung tâm ở tổ chức lớn.

Không nên áp dụng khi: công ty nhỏ, đội data vài người; các domain chưa có kỹ sư dữ liệu; chưa có platform chung đủ tốt
(nếu không, mỗi domain tự dựng hạ tầng và thành silo); governance chưa trưởng thành. Khi đó lakehouse tập trung với
quy ước sở hữu rõ ràng hiệu quả hơn. Data mesh là thay đổi tổ chức, không phải sản phẩm để mua.

## Data fabric và data hub khác data mesh thế nào?

Data mesh là cách **tổ chức con người và quyền sở hữu**. Data fabric là cách tiếp cận **công nghệ**: một lớp tích hợp
dựa trên metadata (catalog, lineage, knowledge graph, data virtualization) để truy cập dữ liệu phân tán một cách thống
nhất, thường hạn chế di chuyển dữ liệu. Data hub là **điểm trung chuyển** hub-and-spoke: gom, chuẩn hoá (thường kèm
master data) và phân phối dữ liệu giữa các hệ thống. Ba khái niệm không loại trừ nhau: một tổ chức theo data mesh vẫn
có thể dùng công nghệ fabric cho catalog và lineage.

## Bạn sẽ nạp tăng dần (incremental) bảng đơn hàng vào lakehouse thế nào để idempotent và xử lý dữ liệu đến trễ?

1. **Bronze append-only**, mỗi lần nạp gắn `batch_id`/`_ingested_at`; trước khi nạp kiểm tra batch đã nạp chưa (bảng
   control) để chạy lại không nhân đôi.
2. **Silver bằng MERGE** theo khoá nghiệp vụ. Trước đó **khử trùng trong batch** (giữ bản `updated_at` lớn nhất, vì MERGE
   gặp nhiều dòng source cho một dòng target sẽ lỗi). Điều kiện cập nhật `s.updated_at > t.updated_at` để bản cũ đến sau
   không ghi đè bản mới. Tốt hơn nữa là dùng số thứ tự CDC (LSN, offset) thay vì đồng hồ nguồn.
3. **Gold tính lại theo phạm vi bị ảnh hưởng**: thu tập ngày/partition của các dòng thực sự thay đổi, ghi đè đúng các
   partition đó (overwrite có predicate hoặc MERGE). Cẩn thận: nếu đơn đổi ngày mua thì cả ngày cũ và ngày mới bị ảnh
   hưởng; metric không phân tách theo ngày (rolling, distinct theo tháng) cần phạm vi rộng hơn.
4. Đọc tăng dần từ silver bằng watermark hoặc Change Data Feed. Định kỳ chạy full refresh để đối soát. Mọi bước ghi bằng
   giao dịch của table format nên job chết giữa chừng không để lại trạng thái dở dang.

## Thiết kế nền tảng phân tích cho một sàn thương mại điện tử như Olist.

Bắt đầu từ yêu cầu: nguồn (PostgreSQL đơn hàng, API thanh toán, review), khối lượng (vài trăm nghìn đơn/năm, tăng dần),
người dùng (BI vận hành hằng ngày, DS dự báo giao hàng trễ), độ trễ (T+1 cho báo cáo, gần thời gian thực cho cảnh báo).

Đề xuất:

- **Ingestion**: batch hằng đêm từ PostgreSQL (hoặc CDC qua Debezium/Kafka khi cần độ trễ thấp) vào bronze trên S3/MinIO.
- **Storage**: lakehouse với Delta hoặc Iceberg; bronze → silver → gold; partition theo tháng mua, compaction định kỳ.
- **Transform**: dbt cho SQL (silver, gold), Spark khi dữ liệu vượt sức một máy; orchestration bằng Airflow.
- **Mô hình gold**: Kimball, `fact_order_items` (grain item), `fact_payments`, `fact_reviews`, các dimension conformed
  `dim_customer` (SCD2 cho địa chỉ), `dim_product`, `dim_seller`, `dim_date`.
- **Serving**: DuckDB/Trino trên lakehouse cho phân tích; nếu nhiều người dùng đồng thời thì nạp gold lên
  BigQuery/Snowflake. BI bằng Metabase.
- **Chất lượng và governance**: test số dòng, khoá duy nhất, đối soát doanh thu; catalog, lineage, phân quyền, che PII
  (email, số điện thoại) từ silver.

Nêu đánh đổi: lakehouse rẻ và mở nhưng tự vận hành nhiều hơn; warehouse managed nhanh triển khai nhưng chi phí và
lock-in cao hơn. Với đội nhỏ, bắt đầu đơn giản và để ngỏ đường nâng cấp.
