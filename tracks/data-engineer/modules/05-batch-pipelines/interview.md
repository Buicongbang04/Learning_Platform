# Câu hỏi phỏng vấn: Batch Pipelines, Airflow, dbt

## ETL và ELT khác nhau thế nào? Khi nào bạn chọn mỗi cách?

**ETL** transform dữ liệu trước khi nạp vào đích, bằng một engine riêng (Python, Spark). **ELT** nạp
dữ liệu thô vào warehouse trước rồi transform bằng SQL ngay trong warehouse (thường bằng dbt).

Chọn **ELT** khi warehouse là cloud co giãn (BigQuery, Snowflake), đội phân tích giỏi SQL, và muốn
giữ dữ liệu thô để chạy lại transform khi logic đổi. Chọn **ETL** (hoặc một bước T trước khi L) khi
phải lọc/mask PII trước khi dữ liệu vào warehouse, khi transform cần thứ SQL làm không tốt (parse
log phức tạp, ML, gọi API), hoặc khi đích đắt/yếu. Thực tế đa số hệ thống là lai: EL bằng
Airbyte/Fivetran/script, T bằng dbt, cộng một ít xử lý Spark cho dữ liệu lớn hoặc bán cấu trúc.

## Idempotent pipeline là gì? Làm sao để một job nạp dữ liệu theo ngày idempotent?

Idempotent nghĩa là chạy *n* lần với cùng input cho cùng kết quả như chạy một lần. Cần vì pipeline
luôn bị chạy lại: retry tự động, clear task, backfill.

Cách làm:

1. Tham số hoá theo `ds` (logical date), không dùng `now()`.
2. Ghi theo partition bằng **delete-insert trong một transaction** hoặc `INSERT OVERWRITE PARTITION`.
3. Với bảng có khoá: **upsert/MERGE** theo khoá tự nhiên.
4. Ghi ra vị trí tạm rồi swap/rename (atomic).
5. Tránh side effect không idempotent (gửi email, `INSERT` append) hoặc dùng idempotency key.

```sql
BEGIN;
DELETE FROM fct_orders WHERE ds = '2018-01-01';
INSERT INTO fct_orders SELECT ... WHERE order_date = '2018-01-01';
COMMIT;
```

## Full load và incremental load: đánh đổi là gì? Làm incremental với watermark cần chú ý gì?

Full load đơn giản, luôn đúng, bắt được cả delete, nhưng tốn thời gian và tải lên nguồn khi bảng
lớn. Incremental chỉ lấy phần thay đổi: nhanh, rẻ, nhưng phức tạp hơn và có thể sai lặng lẽ.

Với watermark (`updated_at > last_max`):

- Cập nhật watermark **sau** khi load commit (hoặc cùng transaction), không thì mất dữ liệu khi lỗi.
- Lấy watermark từ `max(updated_at)` của dữ liệu đã đọc, không phải từ đồng hồ máy chạy job.
- Dữ liệu đến muộn/lệch đồng hồ: lấy lùi một khoảng (lookback) + upsert để không trùng.
- Không thấy delete: cần soft delete hoặc CDC.
- Cột `updated_at` phải có index ở nguồn và phải được cập nhật trên mọi đường ghi.
- Định kỳ chạy full refresh hoặc reconcile (đếm dòng, checksum theo ngày) để phát hiện lệch.

## CDC là gì? So với query theo `updated_at` thì hơn kém gì?

Change Data Capture đọc transaction log của database (WAL của Postgres, binlog của MySQL) để lấy
mọi thay đổi `INSERT/UPDATE/DELETE` theo đúng thứ tự commit. Công cụ phổ biến: Debezium (ghi vào
Kafka), AWS DMS, Fivetran.

Hơn: bắt được delete, không cần cột `updated_at`, gần như không tải lên bảng nguồn (không query),
độ trễ giây, giữ được mọi phiên bản trung gian. Kém: hạ tầng phức tạp (Kafka, connector, schema
registry), cần quyền replication trên DB, phải xử lý schema change, snapshot ban đầu, và thứ tự/
trùng lặp sự kiện ở phía tiêu thụ. Với nhu cầu báo cáo hằng ngày trên vài bảng, query theo
watermark thường là đủ.

## Giải thích `start_date`, `schedule`, `logical_date`/`ds` và `catchup` trong Airflow.

Airflow chia thời gian thành các **data interval** theo `schedule` bắt đầu từ `start_date`. Một DAG
run xử lý một interval và chỉ được kích hoạt **khi interval đó kết thúc**. Run của interval
`[2018-01-01 00:00, 2018-01-02 00:00)` chạy lúc 2018-01-02 00:00 và có `logical_date`
(`ds`) = `2018-01-01`. Vì vậy `ds` là ngày của dữ liệu, không phải ngày chạy.

`catchup=True`: khi DAG được bật, scheduler tạo run cho mọi interval chưa chạy từ `start_date` tới
hiện tại. Hữu ích để tự backfill, nguy hiểm nếu `start_date` xa và DAG không idempotent hoặc nặng.
Thường đặt `catchup=False` cho DAG mới rồi backfill có chủ đích bằng
`airflow dags backfill -s ... -e ...`, kèm `max_active_runs` để giới hạn song song.

## Operator, Sensor, Hook, XCom trong Airflow là gì? XCom có nên dùng để truyền DataFrame?

- **Operator**: khuôn cho một task (`PythonOperator`, `BashOperator`, `SQLExecuteQueryOperator`,
  `KubernetesPodOperator`...).
- **Sensor**: operator chờ một điều kiện (file, partition, DAG khác). Dùng `mode="reschedule"`
  hoặc deferrable để không giữ worker slot.
- **Hook**: lớp kết nối tới hệ thống ngoài (PostgresHook, S3Hook), dùng bên trong operator/task,
  đọc thông tin đăng nhập từ Connection.
- **XCom**: cơ chế lưu giá trị nhỏ vào metadata DB để task sau đọc.

Không truyền DataFrame qua XCom: XCom nằm trong database metadata (giới hạn kích thước, làm phình
DB, serialize chậm). Ghi dữ liệu ra storage (S3/MinIO, bảng) và truyền **đường dẫn** qua XCom.
Có thể cấu hình custom XCom backend lưu lên S3, nhưng nguyên tắc vẫn là Airflow điều phối, không
chở dữ liệu.

## Liệt kê những lỗi hay gặp khi viết DAG Airflow.

1. Code nặng ở top-level (query DB, gọi API): scheduler parse tệp liên tục, làm chậm cả hệ thống.
2. `start_date=datetime.now()` hoặc `days_ago()`: lịch trôi, run không được tạo.
3. Dùng `datetime.now()` trong task thay vì `ds`: backfill xử lý sai ngày.
4. Task không idempotent (append): retry/backfill nhân đôi dữ liệu.
5. Xử lý dữ liệu nặng trên worker Airflow thay vì đẩy xuống warehouse/Spark.
6. Truyền dữ liệu lớn qua XCom.
7. Sensor `mode="poke"` chờ nhiều giờ chiếm hết worker slot.
8. Quên `catchup=False` với `start_date` xa → hàng nghìn run.
9. Một task làm quá nhiều việc → lỗi phải chạy lại tất cả; hoặc ngược lại chia quá vụn.
10. Không đặt `execution_timeout`, task treo mãi.

## dbt giải quyết vấn đề gì? `ref()` và `source()` để làm gì?

dbt biến các câu `SELECT` thành bảng/view trong warehouse và mang thực hành kỹ thuật phần mềm vào
SQL: version control, module hoá, test, tài liệu, môi trường dev/prod, CI. Nó không extract/load,
chỉ là chữ T của ELT.

`source('olist', 'orders')` trỏ tới bảng thô do bước EL nạp (khai báo trong YAML, có thể gắn
freshness check). `ref('stg_orders')` trỏ tới model khác. Cả hai vừa trả về tên bảng đúng theo
môi trường (schema dev của từng người, schema prod), vừa khai báo phụ thuộc để dbt dựng DAG, build
đúng thứ tự, chọn model theo đồ thị (`-s +fct_orders+`) và vẽ lineage. Hard-code tên bảng làm mất
tất cả những điều đó.

## So sánh các materialization của dbt. Khi nào dùng incremental?

| Materialization | Ưu | Nhược |
| --- | --- | --- |
| view | Không tốn lưu trữ, luôn mới | Query chậm nếu logic nặng, tính lại mỗi lần đọc |
| table | Đọc nhanh | Build lại toàn bộ mỗi lần chạy |
| incremental | Chỉ xử lý dữ liệu mới, rẻ với bảng lớn | Logic phức tạp, có thể lệch so với full refresh, cần `unique_key` và chiến lược cho late data |
| ephemeral | Không tạo object, gọn | Không query trực tiếp được, khó debug |

Dùng incremental khi bảng lớn (event, fact hàng trăm triệu dòng) và build table mất quá nhiều thời
gian/tiền. Cần: `unique_key` để upsert, điều kiện `is_incremental()` có lookback cho dữ liệu đến
muộn, và lịch `--full-refresh` định kỳ hoặc khi đổi logic.

## dbt test có những loại nào? Snapshot dùng làm gì?

- **Generic test** khai báo trong YAML: `unique`, `not_null`, `accepted_values`, `relationships`,
  thêm từ package (dbt_utils, dbt_expectations) hoặc tự viết bằng macro `{% test %}`.
- **Singular test**: tệp `.sql` trong thư mục test, trả về các dòng vi phạm; có dòng là fail.
- **Unit test** (dbt ≥ 1.8): kiểm logic của model với input giả lập trong YAML.
- **Source freshness**: cảnh báo khi dữ liệu nguồn quá cũ.

`dbt build` chạy test ngay sau model tương ứng và bỏ qua các model phía sau khi test lỗi
(severity `error`), nhờ vậy dữ liệu bẩn không lan xuống marts.

**Snapshot** cài đặt SCD Type 2: mỗi lần chạy so sánh dữ liệu nguồn với bản trước (theo
`updated_at` hoặc theo các cột), đóng bản cũ bằng `dbt_valid_to` và chèn bản mới. Dùng để giữ lịch
sử thay đổi của dimension (địa chỉ khách hàng, giá sản phẩm) khi nguồn chỉ lưu trạng thái hiện tại.

## Airflow, Prefect, Dagster, Luigi: bạn chọn công cụ nào cho một đội mới?

Phụ thuộc bối cảnh:

- **Airflow**: chuẩn ngành, hệ sinh thái provider lớn nhất, có bản managed (MWAA, Cloud Composer,
  Astronomer). Hợp khi cần tích hợp nhiều hệ thống, đội có người vận hành, hoặc công ty đã dùng.
- **Prefect**: viết Python thuần, chạy local ngay, luồng động (if/for), dễ cho đội nhỏ thiên về
  Python. Prefect Cloud giảm gánh vận hành.
- **Dagster**: mô hình asset-centric (bảng là trung tâm, lineage và freshness theo asset), tích hợp
  dbt rất tốt, test dễ. Hợp với nền tảng dữ liệu mới xây từ đầu.
- **Luigi**: đơn giản, target-based, nhưng ít phát triển; chỉ gặp trong hệ thống cũ.

Câu trả lời tốt nêu tiêu chí (quy mô, kỹ năng đội, managed hay tự host, tích hợp cần có, chi phí)
chứ không chỉ nêu tên. Kỹ năng cốt lõi (idempotent, tham số hoá theo ngày, retry, tách điều phối
khỏi tính toán) chuyển được giữa mọi công cụ.

## Retry thế nào cho đúng? Khi nào không nên retry?

Retry cho lỗi **tạm thời**: timeout mạng, HTTP 429/503, deadlock, worker bị kill. Dùng exponential
backoff + jitter để không dội vào hệ thống đang quá tải, giới hạn số lần và thời gian
(`execution_timeout`).

Không retry (fail nhanh và cảnh báo) với lỗi logic/dữ liệu: cột không tồn tại, vi phạm constraint,
contract hỏng; retry chỉ tốn thời gian và che lỗi. Và chỉ retry khi task **idempotent**; task có
side effect (gửi email, gọi API thanh toán) cần idempotency key hoặc bảng ghi nhận "đã làm".

## Data contract là gì và bạn sẽ áp dụng nó vào pipeline ra sao?

Data contract là thoả thuận giữa bên sản xuất dữ liệu và bên tiêu thụ: schema, kiểu, ràng buộc
(not null, enum, khoảng giá trị), ngữ nghĩa cột, SLA về độ tươi và quy trình thay đổi (breaking
change phải báo trước, có version).

Áp dụng:

1. Contract là tệp (YAML/JSON Schema) có version, lý tưởng nằm cạnh code của team nguồn và được
   kiểm tra trong CI của họ (shift-left).
2. Ở biên pipeline, validate dữ liệu đến theo contract: lỗi mức file (thiếu cột) → fail ngay; lỗi
   mức dòng → đưa vào quarantine kèm lý do.
3. Đặt ngưỡng lỗi: vượt ngưỡng thì không publish partition (write-audit-publish), giữ bản tốt cũ.
4. Cảnh báo tới đúng owner trong contract.

## Thiết kế: pipeline hằng ngày nạp dữ liệu Olist từ PostgreSQL vào warehouse cho dashboard lúc 7 giờ sáng.

Một câu trả lời có cấu trúc:

1. **Yêu cầu**: dashboard cần dữ liệu tới hết hôm qua lúc 7h; khối lượng (vài triệu dòng/ngày?),
   bảng nào thay đổi (orders cập nhật trạng thái, reviews thêm mới).
2. **Extract**: bảng nhỏ (sellers, products) full load; bảng lớn (orders, order_items) incremental
   theo `updated_at` với lookback, đọc từ read replica để không ảnh hưởng production. Ghi raw dạng
   Parquet theo `ds` lên object storage (MinIO/S3) → có thể chạy lại transform không cần nguồn.
3. **Load**: nạp raw vào warehouse (COPY/external table), idempotent theo `ds`.
4. **Transform**: dbt: staging (làm sạch, dedup), snapshot cho customers/products, marts
   (`fct_orders` incremental, `dim_*`), test unique/not_null/relationships, kiểm số dòng so với nguồn.
5. **Orchestration**: Airflow DAG chạy 2h sáng, sensor chờ replica bắt kịp, TaskGroup nạp song song,
   `dbt build`, quality check, publish; retry 2–3 lần, `execution_timeout`, SLA 6h30, cảnh báo Slack.
6. **Vận hành**: backfill bằng `airflow dags backfill` nhờ idempotent; dashboard hiển thị "dữ liệu
   cập nhật lúc"; theo dõi thời lượng chạy và số dòng mỗi ngày để phát hiện bất thường.
7. **Đánh đổi**: nếu sau này cần gần realtime, chuyển orders sang CDC (Debezium + Kafka) và giữ batch
   cho phần còn lại.

## Pipeline của bạn đã chạy sai logic suốt 3 tháng. Bạn xử lý thế nào?

1. **Chặn lan rộng**: tạm dừng DAG hoặc model bị lỗi, thông báo cho người dùng dashboard/bảng bị ảnh
   hưởng (kèm phạm vi thời gian).
2. **Sửa và kiểm**: sửa logic, thêm test tái hiện được lỗi (để không tái phát), chạy thử trên vài
   ngày trong môi trường dev, so sánh với số liệu đúng.
3. **Backfill**: vì pipeline idempotent theo ngày, chạy lại 3 tháng: `dbt build --full-refresh`
   cho model incremental bị ảnh hưởng, hoặc `airflow dags backfill` với `max_active_runs` hợp lý để
   không quá tải warehouse; nếu có bảng tích luỹ/snapshot phụ thuộc thứ tự thì chạy tuần tự.
   Raw data được giữ nên không cần extract lại từ nguồn.
4. **Downstream**: rebuild các bảng/dashboards/model ML phụ thuộc (dùng lineage `-s fct_x+`).
5. **Hậu kiểm**: viết postmortem: vì sao test không bắt được, thêm kiểm tra (reconciliation với
   nguồn, anomaly detection số liệu), cải thiện review.

Điểm mấu chốt người phỏng vấn muốn nghe: idempotency và giữ raw data là thứ làm việc sửa sai này
khả thi và rẻ.
