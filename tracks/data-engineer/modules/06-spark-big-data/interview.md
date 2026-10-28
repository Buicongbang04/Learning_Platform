# Câu hỏi phỏng vấn: Spark & Big Data

## Khi nào bạn chọn Spark, khi nào chọn pandas/DuckDB?

Dựa vào kích thước dữ liệu, hạ tầng sẵn có và nhu cầu song song:

- Dữ liệu vừa RAM/đĩa một máy (tới vài trăm GB với DuckDB/Polars): dùng công cụ single-node. Ít chi phí
  vận hành, khởi động nhanh, debug dễ. Spark trên dữ liệu nhỏ thường **chậm hơn** do overhead JVM,
  lập lịch, shuffle.
- Dữ liệu vượt khả năng một máy, cần hàng trăm core, hoặc tổ chức đã có lakehouse trên Databricks/EMR
  với Delta/Iceberg: dùng Spark.
- Cần chịu lỗi trên job chạy hàng giờ: Spark tự chạy lại task hỏng nhờ lineage.

Câu trả lời tốt nêu được đánh đổi chi phí vận hành, không mặc định "big data = Spark".

## Giải thích HDFS: block, replication, NameNode, DataNode.

HDFS cắt file thành block lớn (128 MB), mỗi block replicate 3 bản trên DataNode khác nhau (rack-aware:
thường 1 bản cùng rack, 2 bản ở rack khác). NameNode giữ metadata trong RAM: cây thư mục, danh sách
block của file, vị trí block. Client hỏi NameNode vị trí rồi đọc/ghi trực tiếp với DataNode.

Điểm yếu: NameNode là single point of failure (giải quyết bằng HA với standby + JournalNode) và
small files problem (hàng triệu file nhỏ làm đầy RAM NameNode và sinh quá nhiều task). Block lớn giúp
đọc tuần tự nhanh và giảm metadata.

## Mô tả các pha của MapReduce. Combiner dùng để làm gì?

Map đọc từng split đầu vào, sinh cặp (key, value). Shuffle & sort gom tất cả value cùng key về cùng
một reducer (hash partition), sắp xếp theo key, dữ liệu trung gian ghi đĩa. Reduce gộp danh sách value
của mỗi key thành kết quả.

Combiner là "reduce cục bộ" chạy trên output của từng mapper trước khi shuffle, giảm dữ liệu qua mạng.
Chỉ dùng được khi phép gộp có tính giao hoán và kết hợp (sum, count, max), không dùng trực tiếp cho
average (phải mang theo cặp sum, count).

## Vì sao Spark nhanh hơn Hadoop MapReduce?

- Giữ dữ liệu trung gian trong bộ nhớ thay vì ghi HDFS giữa mỗi bước; job nhiều bước chạy trong một
  DAG, narrow transformation được pipeline trong cùng task.
- Tối ưu toàn bộ plan nhờ lazy evaluation (Catalyst), codegen (Tungsten).
- Executor sống suốt ứng dụng, không khởi động JVM cho mỗi task như MapReduce.
- Cache được dữ liệu dùng lại, rất có lợi cho thuật toán lặp.

Lưu ý: shuffle của Spark vẫn ghi đĩa; "in-memory" không có nghĩa là không bao giờ chạm đĩa.

## YARN gồm những thành phần nào? So sánh Capacity và Fair scheduler.

ResourceManager (một cho cluster, cấp container), NodeManager (mỗi máy, chạy container), ApplicationMaster
(một cho mỗi ứng dụng, xin tài nguyên và theo dõi task). Với Spark ở cluster mode, driver chạy trong
ApplicationMaster.

Capacity Scheduler chia cluster thành các queue với dung lượng bảo đảm (vd. team BI 30%, ETL 50%), queue
rảnh cho queue khác mượn. Fair Scheduler chia đều tài nguyên theo thời gian cho các job đang chạy, job
nhỏ không bị job lớn chặn. Capacity hợp với nhiều tổ chức cần cam kết; Fair hợp với workload tương tác
lẫn batch.

## Driver và executor làm gì? Job, stage, task khác nhau thế nào?

Driver chạy code người dùng, giữ SparkSession, dựng plan, DAGScheduler cắt stage, TaskScheduler gửi
task tới executor, nhận kết quả nhỏ. Executor là JVM trên worker, chạy task (mỗi core một task), lưu
cache và file shuffle.

Mỗi action sinh một job. Job chia thành stage tại ranh giới shuffle. Mỗi stage có số task bằng số
partition của nó. Ví dụ `orders.filter(...).groupBy("state").count().show()`: 1 job, 2 stage (trước và
sau Exchange), stage 1 có số task = số partition đầu vào, stage 2 = số shuffle partition (sau AQE).

## Lazy evaluation là gì, lợi ích và cạm bẫy?

Transformation chỉ dựng plan, action mới chạy. Lợi ích: Catalyst thấy toàn bộ plan để pushdown filter,
prune cột, gộp operator; tránh tính phần không cần.

Cạm bẫy: lỗi (vd. sai kiểu, file thiếu) chỉ lộ ra khi action chạy, xa chỗ viết code; mỗi action chạy
lại toàn bộ lineage nếu không cache, nên `df.count()` rồi `df.write` là tính hai lần; đo thời gian một
transformation không có ý nghĩa.

## RDD, DataFrame, Dataset khác nhau thế nào? Vì sao trong PySpark nên dùng DataFrame?

RDD là tập object phân tán với API hàm, Spark không hiểu bên trong lambda nên không tối ưu được. DataFrame
có schema, biểu thức cột được Catalyst tối ưu và Tungsten codegen. Dataset là DataFrame có kiểu tĩnh,
chỉ có trong Scala/Java.

Trong PySpark, RDD bắt dữ liệu serialize qua lại giữa JVM và Python worker cho mỗi phép `map`, rất chậm.
DataFrame chỉ gửi plan, việc tính toán nằm hoàn toàn trong JVM. DataFrame API và Spark SQL cho cùng
plan, cùng hiệu năng.

## Narrow và wide transformation? Shuffle tốn kém ở đâu?

Narrow: partition đầu ra chỉ cần một partition đầu vào (filter, select, withColumn), được pipeline,
không trao đổi mạng. Wide: cần dữ liệu từ nhiều partition (groupBy, join, distinct, orderBy,
repartition), gây shuffle.

Shuffle tốn ở: serialize dữ liệu, ghi file shuffle xuống đĩa cục bộ, truyền qua mạng, deserialize,
có thể sort, có thể spill khi thiếu bộ nhớ; thêm nữa shuffle là nơi skew bộc lộ. Giảm shuffle: filter
và chọn cột sớm, broadcast bảng nhỏ, aggregate trước join, tận dụng bucketing.

## So sánh broadcast hash join và sort-merge join. Khi nào broadcast gây hại?

Broadcast hash join gửi nguyên bảng nhỏ tới mọi executor, bảng lớn không phải shuffle. Nhanh nhất khi
một bên nhỏ (mặc định ngưỡng `autoBroadcastJoinThreshold` 10 MB, có thể dùng hint `broadcast()`).
Sort-merge join shuffle cả hai bên theo key, sort rồi merge; ổn định cho hai bảng lớn, spill được.

Broadcast gây hại khi bảng "nhỏ" thực ra lớn (vài GB): driver phải gom bảng (OOM driver), mỗi executor
giữ một bản (OOM executor), thời gian broadcast vượt `spark.sql.broadcastTimeout`. Thống kê sai (bảng
sau filter ước lượng nhỏ nhưng thật lớn) cũng dẫn tới chọn sai; AQE giúp vì nó dùng kích thước thật.

## Data skew là gì? Bạn phát hiện và xử lý ra sao?

Skew là phân bố key lệch, vài key chiếm phần lớn dòng, nên sau shuffle một số task rất lớn. Phát hiện:
Spark UI cho thấy task max lâu hơn median nhiều lần, shuffle read lệch; hoặc đếm
`groupBy(key).count().orderBy(desc)`.

Xử lý theo thứ tự rẻ tới đắt: lọc key rác (NULL, "unknown") và xử lý riêng; broadcast bên nhỏ; bật AQE
skew join; salting: thêm `salt` ngẫu nhiên 0..N-1 vào key bên lớn, nhân bản bên nhỏ N lần, join theo
(key, salt); với aggregation dùng hai tầng (theo key+salt rồi theo key). Salting tăng dữ liệu bên nhỏ
N lần nên chỉ áp cho key nóng nếu có thể.

## repartition và coalesce khác nhau thế nào? partitionBy khi ghi là gì?

`repartition(n, cols)` full shuffle, có thể tăng hoặc giảm, chia đều theo hash/round-robin.
`coalesce(n)` chỉ giảm, gộp partition có sẵn không shuffle, rẻ nhưng có thể không đều và làm giảm song
song của cả stage phía trước (vì nó không tạo ranh giới stage).

`write.partitionBy("year", "month")` là partition **trên đĩa**: tạo thư mục `year=.../month=...` để
truy vấn sau được partition pruning. Thường kết hợp `repartition("year", "month")` trước khi ghi để mỗi
thư mục có ít file.

## Khi nào nên cache? cache và persist khác nhau gì?

Cache khi DataFrame được dùng lại nhiều lần và tính lại tốn kém, ví dụ kết quả join được ghi ra 3 bảng
khác nhau, hoặc dùng trong vòng lặp. `cache()` là `persist()` với storage level mặc định
(MEMORY_AND_DISK cho DataFrame); `persist(level)` cho chọn level (MEMORY_ONLY, DISK_ONLY, `_2`...).

Cache là lazy, chỉ có hiệu lực sau action đầu. Cache thừa chiếm bộ nhớ executor, làm execution spill.
Nhớ `unpersist()`. Với lineage quá dài thì `checkpoint()` (ghi ra storage tin cậy, cắt lineage) chứ
không phải cache.

## AQE làm được gì?

Adaptive Query Execution tối ưu lại plan lúc chạy dựa trên thống kê thật sau mỗi shuffle stage: gộp
các shuffle partition nhỏ (đỡ phải tinh chỉnh `spark.sql.shuffle.partitions`), đổi sort-merge join
sang broadcast khi một bên thực tế nhỏ, tách partition skew trong join. Bật mặc định từ Spark 3.2. Nó
không thay được việc viết job tốt (filter sớm, không UDF, không collect).

## Vì sao Python UDF chậm? Có lựa chọn nào khác?

Python UDF chạy trong tiến trình Python riêng: Spark phải serialize từng batch dòng từ JVM sang Python
và ngược lại (thấy `BatchEvalPython` trong plan), Catalyst coi UDF là hộp đen nên không pushdown hay
codegen qua nó. Thay thế: built-in function trong `pyspark.sql.functions` (gần như mọi logic
when/regexp/date/array/map đều có), biểu thức SQL `F.expr`, Pandas UDF dùng Arrow vector hoá
(`ArrowEvalPython`), hoặc viết UDF bằng Scala/Java nếu thật cần.

## Một job Spark đang chạy chậm hơn hôm qua 3 lần. Bạn điều tra thế nào?

1. So sánh dữ liệu đầu vào: khối lượng có tăng đột biến không, có nhiều file nhỏ mới không.
2. Mở Spark UI: stage nào lâu nhất; trong stage đó task max so với median (skew), spill memory/disk,
   GC time, shuffle read/write.
3. Tab SQL: plan thật sau AQE, join có đổi strategy không (broadcast thành sort-merge do bảng lớn lên),
   filter có được pushdown không.
4. Tài nguyên: executor có bị mất (preemption, OOM), queue YARN có bị tranh chấp.
5. Sửa theo nguyên nhân: salting/AQE cho skew, tăng partition hoặc bộ nhớ cho spill, compaction cho
   small files, broadcast hint, cache phần dùng lại.

## Thiết kế job batch hằng ngày tính GMV theo seller cho Olist trên dữ liệu vài TB.

- **Nguồn**: bảng `orders`, `order_items` dạng Parquet/Delta trên object storage, partition theo ngày.
- **Đọc**: chỉ partition của ngày chạy (và vài ngày trước nếu đơn cập nhật muộn), chọn cột cần,
  schema khai báo.
- **Biến đổi**: filter `delivered`, join `order_items` với `orders` theo `order_id` (cả hai lớn, sort-merge;
  nếu chỉ một ngày orders thì có thể broadcast), join `sellers` bằng broadcast. Kiểm tra skew theo
  `seller_id`, bật AQE.
- **Ghi**: `partitionBy("order_date")`, `partitionOverwriteMode=dynamic` (hoặc `replaceWhere`/`MERGE` với
  Delta) để chạy lại cùng ngày là **idempotent**; `repartition` trước khi ghi để tránh small files.
- **Vận hành**: orchestrate bằng Airflow với tham số ngày (backfill được), data quality check (số dòng,
  tổng GMV so với hôm trước), dynamic allocation, cảnh báo khi job vượt SLA.
- Nêu đánh đổi: nếu dữ liệu một ngày chỉ vài GB, có thể dùng DuckDB/Polars rẻ hơn nhiều.

## Small files problem là gì và xử lý thế nào trong Spark?

Nhiều file nhỏ (KB–vài MB) làm chậm: mỗi file một lần mở, list thư mục chậm trên object storage,
metadata NameNode phình, mỗi file có thể thành một task. Nguyên nhân thường gặp: `partitionBy` theo cột
cardinality cao, streaming ghi micro-batch, 200 shuffle partition × nhiều thư mục.

Xử lý: `repartition` theo cột partition trước khi ghi, `coalesce` khi ghi ít dữ liệu,
`spark.sql.files.maxRecordsPerFile`, chạy job compaction định kỳ (Delta `OPTIMIZE`), chọn cột partition
thô hơn (tháng thay vì giờ).

## Tăng RAM executor có sửa lỗi driver chết khi collect không?

Không xử lý nguyên nhân đó. collect/toPandas đưa dữ liệu về driver; phải hạn chế kết quả lấy về,
ghi phân tán hoặc aggregate trước. Phân biệt log driver và executor, đo partition/shuffle/spill
rồi mới quyết định điều chỉnh tài nguyên ở đâu.

## Job đã tắt thì xem lại Spark UI bằng cách nào?

Bật event log trước khi chạy và lưu ở nơi History Server đọc được. Event log không được bật
thì không thể mặc định dựng lại mọi chi tiết UI sau sự cố. Khi benchmark, lưu cả cấu hình/input và
kết quả đối chiếu; một ảnh thời gian nhanh hơn chưa chứng minh tối ưu đúng.
