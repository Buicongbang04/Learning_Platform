# Câu hỏi phỏng vấn: Security & Governance

## Phân biệt authentication và authorization. Cho ví dụ trong data platform.

**Authentication** xác thực danh tính (bạn là ai): đăng nhập SSO vào Snowflake, service account Airflow
dùng key pair, Kerberos trên Hadoop, IAM role gắn vào pod Spark. **Authorization** quyết định quyền sau
khi đã biết danh tính: `GRANT SELECT ON mart.orders TO analyst`, IAM policy cho phép `s3:GetObject` trên
prefix `bronze/`, row-level policy chỉ cho seller thấy dòng của mình.

Hai lớp độc lập: một user xác thực hợp lệ vẫn phải bị từ chối nếu không có quyền (HTTP 403 thay vì 401).
Trong sự cố thực tế, lỗi authorization (cấp quyền thừa, bucket public) phổ biến hơn lỗi authentication.

## RBAC và ABAC khác nhau thế nào? Khi nào chọn ABAC?

RBAC gắn quyền vào role, user nhận role. Dễ hiểu, dễ audit, có sẵn trong mọi database. ABAC quyết định
dựa trên thuộc tính của user (department, region), của resource (tag `pii`, `sensitivity`) và context
(purpose, thời gian).

Chọn ABAC khi số tổ hợp điều kiện làm role bùng nổ: 50 quốc gia × 5 mức nhạy cảm × 4 phòng ban. Với ABAC
ta gắn tag `pii:email` lên cột một lần, viết một policy "chỉ user có `pii_clearance=true` và
`purpose=support` mới thấy plaintext", mọi bảng mới có tag đó tự được bảo vệ. Thường kết hợp: RBAC cho
quyền thô theo schema, tag-based policy (ABAC) cho cột nhạy cảm, RLS cho dòng.

## Least privilege áp dụng cụ thể thế nào cho một pipeline Airflow + warehouse?

- Mỗi nhóm DAG một service account; DAG ingest chỉ được ghi `raw`/`staging`, DAG transform đọc `staging`
  ghi `mart`, không ai có `DROP DATABASE`.
- Credential trong secret backend (Vault, AWS Secrets Manager), không trong biến Airflow plaintext hay Git.
- Analyst đọc `mart` qua role chỉ đọc; quyền đọc `raw` có PII phải xin, có thời hạn (just-in-time).
- Quyền network: warehouse chỉ nhận kết nối từ VPC/IP của worker.
- Review quyền định kỳ, thu hồi quyền không dùng 90 ngày.

## Encryption at rest có bảo vệ được dữ liệu khỏi analyst có quyền SELECT không?

Không. Encryption at rest (SSE-KMS, TDE, disk encryption) bảo vệ lớp lưu trữ vật lý: ổ đĩa bị lấy, snapshot
bị lộ. Engine tự giải mã khi người có quyền truy vấn, nên analyst có `SELECT` vẫn thấy plaintext.

Muốn ngăn analyst đọc cột nhạy cảm cần: không cấp quyền cột (column-level grant), dynamic masking policy,
tokenization, hoặc field-level encryption với key mà role analyst không được dùng. Đây là câu hỏi để kiểm
tra ứng viên có hiểu mô hình mối đe doạ (threat model) hay chỉ thuộc khái niệm.

## Envelope encryption là gì và vì sao các KMS dùng nó?

Dữ liệu được mã hoá bằng data encryption key (DEK) sinh cho từng file/record; DEK được mã hoá bằng key
encryption key (KEK) nằm trong KMS và không bao giờ rời KMS. Ta lưu ciphertext cùng DEK đã mã hoá.

Lý do: (1) KMS giới hạn kích thước và tốc độ gọi, không thể gửi hàng TB qua KMS; mã hoá cục bộ bằng DEK nhanh.
(2) Rotation rẻ: đổi KEK chỉ cần mã hoá lại các DEK, không động vào dữ liệu. (3) Quyền tập trung: ai được
gọi `Decrypt` trên KEK được kiểm soát và log trong KMS. (4) Cho phép crypto-shredding nếu mỗi user/tenant một DEK.

## Tokenization khác encryption và hashing thế nào? Khi nào dùng?

- **Hashing**: một chiều, deterministic. Nhưng PII có không gian nhỏ (số điện thoại, CPF) nên hash thường
  bị brute-force; cần HMAC với secret key.
- **Encryption**: hai chiều với key; ciphertext phụ thuộc thuật toán, có thể không deterministic.
- **Tokenization**: thay giá trị bằng token ngẫu nhiên, ánh xạ lưu ở vault riêng. Token không có quan hệ
  toán học với giá trị gốc, nên lộ token không lộ gì nếu vault an toàn.

Dùng tokenization khi muốn đa số hệ thống (warehouse, BI, ML) không bao giờ chạm dữ liệu thật, chỉ vài
service được detokenize, điển hình là số thẻ theo PCI DSS: thu hẹp phạm vi audit đáng kể.

## Pseudonymization và anonymization khác nhau ra sao dưới GDPR?

Pseudonymized data vẫn là dữ liệu cá nhân vì có thể nối lại với người thật nhờ thông tin bổ sung (key,
bảng mapping). GDPR khuyến khích nó như biện pháp bảo vệ nhưng mọi nghĩa vụ vẫn áp dụng. Anonymized data
không thể xác định lại cá nhân bằng phương tiện hợp lý, nên ra ngoài phạm vi GDPR.

Anonymization thật khó hơn nhiều người nghĩ: hash `customer_id` không có key là pseudonymization yếu;
dữ liệu chi tiết với zip + ngày sinh + giới tính có thể re-identify. Kỹ thuật hỗ trợ: aggregation với
ngưỡng k (k-anonymity), generalization, suppression, differential privacy.

## Bạn sẽ thiết kế hệ thống phát hiện PII tự động cho data lake thế nào?

1. **Inventory**: liệt kê bảng/cột từ catalog.
2. **Sampling**: lấy mẫu N dòng mỗi cột (ưu tiên partition mới), không quét toàn bộ.
3. **Detector nhiều tầng**: tên cột (heuristic), regex + checksum (email, CPF, thẻ có Luhn, số điện thoại),
   NER cho văn bản tự do (Presidio, Macie, Google DLP).
4. **Ngưỡng**: cột được gắn tag nếu tỉ lệ dòng khớp > ngưỡng (vd. 30%); free-text cột có bất kỳ match nào
   thì gắn `contains_pii` và đề xuất redaction.
5. **Ghi tag vào catalog**, kích hoạt masking policy, gửi steward xác nhận (human-in-the-loop).
6. **Chạy định kỳ / khi schema đổi**, đo precision/recall trên tập mẫu đã gán nhãn.

Rủi ro: false positive làm mask nhầm cột phục vụ nghiệp vụ; false negative nguy hiểm hơn, nên ưu tiên recall
cho cột free-text.

## Kể các data quality dimension và cách kiểm tra mỗi loại trong pipeline.

Completeness (not null, số dòng so với hôm trước), uniqueness (khoá chính unique), validity (kiểu, miền giá
trị, regex), consistency (quy tắc chéo cột/bảng như `delivered >= purchase`), accuracy (so với nguồn tham
chiếu), timeliness/freshness (max timestamp so với now), referential integrity (khoá ngoại tồn tại).

Cài đặt: dbt tests (`unique`, `not_null`, `accepted_values`, `relationships`), pandera/Great Expectations
cho DataFrame, Soda/Elementary/Monte Carlo cho monitoring và anomaly detection. Đặt check ở ranh giới:
sau ingest (contract của nguồn), trước publish mart (quality gate), và theo dõi liên tục (observability).

## Khi một quality check fail, pipeline nên làm gì?

Tuỳ mức độ:

- **Blocking** (trùng khoá chính, schema đổi, mất nhiều dòng): dừng, không publish, giữ bản cũ của mart,
  alert owner. Dashboard thấy số cũ tốt hơn số sai.
- **Row-level** (một số dòng sai miền giá trị): quarantine các dòng lỗi vào bảng riêng kèm lý do, publish
  phần sạch, alert nếu tỉ lệ lỗi > ngưỡng.
- **Warning** (outlier, freshness hơi trễ): log, gửi cảnh báo, vẫn publish.

Quan trọng là write-audit-publish: ghi vào bảng tạm/branch, chạy check, rồi mới swap sang bảng thật (Iceberg
branch, Delta, `ALTER TABLE ... RENAME`) để consumer không bao giờ đọc dữ liệu chưa kiểm.

## Data lineage dùng để làm gì? Thu thập lineage bằng cách nào?

Dùng cho impact analysis trước khi đổi schema, root cause khi số sai, và compliance (PII chảy tới đâu, bảng
nào phải xử lý khi có erasure request; tài liệu cho DPIA/AI Act).

Thu thập:

- **Parse SQL** (sqlglot, dbt `manifest.json` có `depends_on`): tốt cho ELT trong warehouse.
- **Runtime integration**: OpenLineage cho Airflow, Spark (listener), dbt, Flink phát `RunEvent` với
  inputs/outputs/facets; backend Marquez, DataHub, OpenMetadata.
- **Query log** của warehouse (Snowflake `ACCESS_HISTORY`, BigQuery `INFORMATION_SCHEMA.JOBS`).

Table-level dễ, column-level khó hơn (cần hiểu biểu thức, `SELECT *`, UDF). Lineage chỉ đáng tin nếu được
sinh tự động, không vẽ tay.

## Thiết kế "right to be forgotten" cho Olist khi dữ liệu nằm ở Postgres, data lake Parquet, warehouse và backup.

1. **Tiếp nhận + xác minh** yêu cầu, ghi request id, kiểm tra nghĩa vụ giữ lại (hoá đơn thuế phải giữ N năm).
2. **Định vị**: dùng catalog (cột có tag `pii`, khoá `customer_unique_id`) + lineage để liệt kê mọi bảng chứa người này.
3. **Xử lý theo loại bảng**:
   - OLTP / dim: xoá hoặc thay PII bằng giá trị anonymized.
   - Fact: không xoá dòng (mất doanh thu lịch sử), thay `customer_id` bằng pseudonym ngẫu nhiên không nối lại được.
   - Data lake Parquet bất biến: dùng table format hỗ trợ `DELETE` (Delta/Iceberg) rồi `VACUUM`/expire snapshot,
     hoặc lưu PII mã hoá theo DEK từng user và **crypto-shred** (xoá DEK).
   - Backup: không thể sửa từng backup; dựa vào crypto-shredding hoặc retention ngắn và re-apply danh sách
     xoá khi restore.
   - Hệ thống downstream (CRM qua reverse ETL, export cho đối tác): gửi lệnh xoá.
4. **Idempotent + audit**: chạy lại không lỗi, log request id, thời gian, bảng và số dòng tác động, không
   ghi PII thô vào log (lưu hash có key của id).
5. **Xác nhận** trong hạn (GDPR: một tháng), có test tự động đảm bảo không còn dòng nào khớp.

## Data catalog mang lại gì? So sánh DataHub, OpenMetadata, Unity Catalog.

Catalog giúp tìm dữ liệu (search), hiểu dữ liệu (mô tả, glossary, owner), tin dữ liệu (quality, freshness,
lineage) và quản trị (tag, policy). Không có catalog, mỗi câu hỏi "bảng này là gì, ai sở hữu" tốn một tin nhắn Slack.

- **DataHub**: open source từ LinkedIn, metadata dạng event qua Kafka, lineage và tag mạnh, nhiều connector.
- **OpenMetadata**: open source, schema metadata chặt, có data quality test và collaboration tích hợp, dễ triển khai.
- **Unity Catalog**: gắn với lakehouse Databricks (đã open source), vừa là catalog vừa là lớp thực thi quyền
  (GRANT, row filter, column mask, ABAC theo tag) và lineage tự động. Mạnh nếu dùng Databricks, kém trung lập hơn.

## Một analyst cần phân tích hành vi mua theo khách hàng nhưng không được thấy PII. Bạn cung cấp dữ liệu thế nào?

Tạo view/bảng trong mart với `customer_key = HMAC(secret, customer_unique_id)`: deterministic nên đếm
khách unique, cohort, join giữa `orders` và `reviews` vẫn đúng; key nằm trong secret manager, analyst không
có. Loại bỏ cột trực tiếp (tên, email, CPF), generalize quasi-identifier (zip 8 số → 5 số, ngày sinh → nhóm tuổi).
Quyền: analyst chỉ có `SELECT` trên view, không trên bảng gốc. Nếu cần chia sẻ ra ngoài, chuyển sang
aggregate có ngưỡng k (ẩn nhóm < 10 khách). Ghi rõ purpose trên dataset và log truy cập.

## EU AI Act ảnh hưởng gì tới công việc của Data Engineer?

Với hệ thống AI high-risk (chấm điểm tín dụng, tuyển dụng…), Art. 10 yêu cầu dataset train/validation/test
có quy trình governance: nguồn gốc, thu thập, làm sạch, đánh giá bias và tính đại diện, được tài liệu hoá; cộng
với logging và tài liệu kỹ thuật. DE cần: version và snapshot dataset (time travel), lineage từ nguồn tới model,
lưu kết quả quality check và thống kê phân phối, datasheet cho dataset, quyền truy cập và retention rõ ràng.
Nói ngắn: mọi thứ module này dạy (quality, lineage, catalog) trở thành bằng chứng pháp lý.

## Bạn phát hiện một file CSV chứa email khách hàng đang nằm trong bucket public. Bạn làm gì?

1. **Contain ngay**: chặn public access (bucket policy, Block Public Access), không xoá vội để còn bằng chứng.
2. **Đánh giá**: file có từ khi nào, access log cho thấy ai đã tải, bao nhiêu bản ghi, loại dữ liệu nào.
3. **Báo cáo** theo quy trình incident: security team, DPO; GDPR yêu cầu báo cơ quan quản lý trong 72 giờ nếu
   có rủi ro cho cá nhân.
4. **Khắc phục gốc**: vì sao job ghi ra bucket public? Thêm guardrail như IaC policy (OPA/Conftest, AWS SCP
   cấm public bucket), PII scan cho bucket, least privilege cho job export.
5. **Postmortem** không đổ lỗi, có action item đo được.

## Data interoperability nghĩa là gì trong một data platform? Bạn đảm bảo nó bằng những gì?

Dữ liệu và metadata trao đổi được giữa hệ thống, engine, team mà không phải viết lại hay convert tay. Các lớp:
**định dạng mở** (Parquet/Avro, Iceberg/Delta) để nhiều engine đọc chung; **schema registry** với luật tương thích
cho stream; **data contract** máy đọc được, kiểm tra trong CI; **metadata/lineage mở** (OpenLineage, Iceberg REST
catalog); **API chuẩn** (JDBC/ODBC, Arrow Flight/ADBC, Delta Sharing, OpenAPI); **chuẩn ngữ nghĩa** (ISO 8601 UTC,
ISO 4217, ISO 3166). Phép thử: đổi engine hoặc thêm consumer mới có buộc phải viết lại pipeline không.

## Công ty Mỹ muốn dùng toàn bộ log chat CSKH để train model và phân tích marketing. ECPA đặt ra vấn đề gì cho DE?

Chat là **nội dung liên lạc điện tử**: Wiretap Act cấm chặn bắt khi đang truyền, Stored Communications Act cấm
provider tuỳ tiện tiết lộ nội dung đã lưu. Dùng cho mục đích mới cần cơ sở rõ: **consent** trong terms of service
(lưu ý bang yêu cầu mọi bên đồng ý) hoặc nằm trong **provider exception** (vận hành dịch vụ), nên pháp chế phải
duyệt mục đích. Về kỹ thuật: tag riêng **content** và **metadata** trong catalog; giới hạn truy cập bảng nội dung
theo purpose (ABAC), log mọi truy cập; ưu tiên pseudonymize và lọc PII trước khi đưa vào tập train; có quy trình
xử lý yêu cầu từ cơ quan pháp luật (warrant cho nội dung, subpoena cho metadata). Đồng thời kiểm tra luật bang
(CCPA/CPRA) và GDPR nếu có người dùng EU.

## Đổi khóa HMAC định danh ảnh hưởng gì tới các bảng?

Token của cùng đối tượng đổi theo khóa. Nếu chỉ đổi ở một bảng, các phép join có thể gãy.
Cần phiên bản khóa, mapping/migration cho bảng liên quan, thời gian chuyển và kiểm chứng, đồng thời
hạn chế quyền truy cập thông tin liên kết định danh cũ/mới.

## Producer đổi BRL sang cents mà schema vẫn hợp lệ thì ai phát hiện?

Contract và kiểm tra nghiệp vụ phải nêu đơn vị; owner/steward cùng producer/consumer phê duyệt thay đổi.
Quality gate nên bắt thay đổi chưa hỗ trợ qua đối chiếu/baseline phù hợp. JSON hợp lệ chỉ chứng minh
cấu trúc, không bảo đảm ý nghĩa dữ liệu còn đúng.
