# Câu hỏi phỏng vấn: DevOps cho Data

## Container khác virtual machine thế nào? Vì sao pipeline dữ liệu nên chạy trong container?

Virtual machine ảo hoá phần cứng, mỗi VM có kernel và hệ điều hành riêng, nặng (GB) và khởi động
chậm. Container chia sẻ kernel của máy chủ, chỉ cô lập process, filesystem, network bằng namespace
và cgroup của Linux, nên nhẹ (MB) và khởi động trong vài trăm ms.

Với pipeline dữ liệu, container giải quyết bài toán **reproducibility**: phiên bản Python, pandas,
driver Postgres, thư viện hệ thống đều được đóng băng trong image. Cùng image chạy trên laptop, CI,
Kubernetes và cho cùng kết quả. Container cũng là đơn vị chuẩn mà Airflow (`KubernetesPodOperator`,
`DockerOperator`), Kubernetes, AWS Batch/ECS, Cloud Run đều chạy được.

## Giải thích layer cache trong Docker. Sắp xếp Dockerfile thế nào để build nhanh?

Mỗi lệnh `RUN`, `COPY`, `ADD` tạo một layer. Docker cache layer dựa trên lệnh và nội dung tệp được
copy. Khi một layer thay đổi, mọi layer sau nó bị build lại.

Vì vậy đặt thứ ít thay đổi lên trước: base image → cài gói hệ thống → `COPY requirements.txt` →
`pip install` → `COPY src/`. Sửa code chỉ làm build lại layer cuối, không cài lại toàn bộ thư viện.
Nếu `COPY . .` trước `pip install`, mỗi lần sửa một dòng code là cài lại pandas, pyarrow từ đầu.
Kèm theo là `.dockerignore` để `.git`, `data/`, `.venv` không làm thay đổi build context.

## Multi-stage build là gì, lợi ích gì?

Multi-stage build có nhiều `FROM` trong một Dockerfile. Stage đầu (`builder`) có compiler, header,
công cụ build để tạo wheel hoặc binary; stage cuối chỉ `COPY --from=builder` những thứ cần lúc chạy.

Lợi ích: image nhỏ hơn (pull nhanh hơn, khởi động Pod nhanh hơn), ít bề mặt tấn công và ít CVE hơn
vì không có `gcc`, `curl`, trình quản lý gói thừa. Có thể dùng thêm stage `test` để chạy pytest khi
build trong CI.

## Vì sao không nên chạy container bằng root, và không nên đặt secret trong Dockerfile?

Mặc định process trong container chạy với UID 0. Nếu có lỗ hổng (thư viện parse file độc hại,
container escape), kẻ tấn công có root trong container và dễ leo thang ra host. Dùng `USER` không
phải root và trong Kubernetes đặt `securityContext.runAsNonRoot: true`.

Secret trong `ENV` hoặc `COPY .env` nằm vĩnh viễn trong layer của image; ai pull được image (hoặc
xem `docker history`) đều đọc được, kể cả khi layer sau xoá file. Secret phải được inject lúc chạy:
biến môi trường từ Kubernetes Secret, secret manager (AWS Secrets Manager, Vault), hoặc
`--mount=type=secret` của BuildKit khi cần lúc build.

## Kubernetes Deployment, Job và CronJob khác nhau thế nào? Khi nào dùng cái nào trong data?

- **Deployment**: giữ N Pod luôn chạy, Pod chết thì tạo lại, hỗ trợ rolling update. Dùng cho
  service chạy mãi: API, Kafka consumer, Airflow webserver.
- **Job**: chạy Pod tới khi hoàn thành thành công, retry theo `backoffLimit`. Dùng cho tác vụ một
  lần: backfill, migration.
- **CronJob**: tạo Job theo lịch cron. Dùng cho ingest định kỳ khi chưa cần orchestrator đầy đủ.

Khi pipeline có nhiều bước phụ thuộc nhau, retry theo task, backfill theo ngày thì dùng Airflow/
Prefect/Dagster, và để orchestrator tạo Pod trên K8s thay vì xâu chuỗi nhiều CronJob.

## Requests và limits trong Kubernetes là gì? Pod job pandas bị OOMKilled thì xử lý ra sao?

`requests` là lượng CPU/RAM scheduler dùng để chọn node (đảm bảo tối thiểu). `limits` là trần:
vượt CPU limit thì bị throttle, vượt memory limit thì kernel giết process, Pod có trạng thái
`OOMKilled` (exit code 137).

Xử lý: xem `kubectl describe pod` để xác nhận OOM và mức dùng thực tế. Ngắn hạn tăng memory limit.
Dài hạn sửa code: đọc theo chunk (`pd.read_csv(chunksize=...)`), chọn cột cần thiết, dùng kiểu dữ
liệu nhỏ hơn (`category`, `int32`), chuyển sang Polars/DuckDB xử lý out-of-core, hoặc chia nhỏ job
theo partition ngày.

## CI và CD khác nhau thế nào? Một pipeline CI/CD cho repo dữ liệu gồm những bước nào?

CI (Continuous Integration) tự động kiểm tra mỗi thay đổi: lint, unit test, integration test,
build. CD (Continuous Delivery) đưa artifact đã kiểm tra lên các môi trường; Continuous Deployment
là tự động tới production không cần duyệt tay.

Cho repo dữ liệu: (1) lint Python (ruff) và SQL (sqlfluff); (2) unit test transform bằng pytest với
fixture nhỏ; (3) integration test với Postgres service container hoặc DuckDB; (4) với dbt chạy
`dbt build --select state:modified+` trên schema tạm; (5) build image tag bằng commit SHA, push
registry; (6) deploy staging, chạy smoke test; (7) duyệt rồi deploy production. Dùng
`concurrency` để không deploy chồng, `environment` để tách secret và quy tắc duyệt.

## GitOps là gì? ArgoCD khác cách CI chạy `kubectl apply` ở điểm nào?

GitOps coi Git là nguồn sự thật duy nhất cho trạng thái hệ thống. Với ArgoCD, một controller trong
cluster liên tục so sánh manifest trong repo với trạng thái thực, phát hiện **drift** và đồng bộ
lại (mô hình pull).

So với CI `kubectl apply` (push): CI không cần quyền admin vào cluster (an toàn hơn); thay đổi tay
trên cluster bị phát hiện và ghi đè; rollback chỉ là `git revert`; lịch sử deploy chính là lịch sử
commit. Đổi lại cần thêm thành phần vận hành và quy ước tách repo ứng dụng / repo manifest.

## Declarative và imperative IaC khác nhau thế nào? Idempotency trong IaC nghĩa là gì?

Declarative mô tả trạng thái đích ("cần bucket X có versioning"); công cụ (Terraform,
CloudFormation, Kubernetes) tự tính diff giữa trạng thái hiện tại và đích rồi thực hiện. Imperative
mô tả từng bước ("gọi API tạo bucket, rồi bật versioning"); người viết phải tự xử lý trường hợp
đã tồn tại.

Idempotency: áp dụng cùng cấu hình nhiều lần cho cùng kết quả, lần sau không tạo thêm hay thay đổi
gì. `terraform plan` trả "No changes" khi code và hạ tầng khớp. Điều này cho phép chạy IaC trong CI
an toàn và phát hiện drift.

## Terraform state là gì? Vì sao cần remote backend và state locking?

State (`terraform.tfstate`) ánh xạ resource trong code với object thật trên cloud (ID, thuộc tính).
Terraform dựa vào state để tính plan. State có thể chứa giá trị nhạy cảm.

Remote backend (S3, GCS, Terraform Cloud) để cả đội và CI dùng chung một state, có versioning để
khôi phục. Locking (DynamoDB với S3 backend, hoặc lockfile native từ Terraform 1.10) ngăn hai người
`apply` cùng lúc làm hỏng state. Không commit state vào Git. Mỗi môi trường (dev/staging/prod) có
state riêng để lỗi ở dev không ảnh hưởng prod.

## Quản lý nhiều môi trường (dev, staging, prod) bằng Terraform thế nào?

Các cách phổ biến:

| Cách | Mô tả | Đánh đổi |
| --- | --- | --- |
| Thư mục theo môi trường gọi chung module | `envs/staging/main.tf`, `envs/prod/main.tf` cùng gọi `modules/data_lake` | Rõ ràng, state tách hẳn; hơi lặp code gọi module |
| Workspaces | `terraform workspace select prod`, dùng `terraform.workspace` | Ít code; dễ nhầm workspace, chung backend config |
| Biến + tfvars | `-var-file=prod.tfvars` | Đơn giản; phải kỷ luật về backend key |
| Terragrunt | Lớp bọc DRY cho backend và biến | Thêm công cụ |

Dù cách nào: cùng module cho mọi môi trường, khác nhau chỉ ở biến (kích thước, số node, tên), có
`validation` cho biến, gắn tag `environment` cho mọi resource.

## Terraform, OpenTofu, AWS CDK và Pulumi: chọn cái nào?

Terraform/OpenTofu dùng HCL declarative, đa cloud, hệ sinh thái provider lớn nhất; OpenTofu là fork
mã nguồn mở sau khi Terraform chuyển sang giấy phép BSL, tương thích cú pháp. AWS CDK cho viết hạ
tầng bằng Python/TypeScript, sinh CloudFormation, mạnh khi chỉ dùng AWS và đội quen lập trình (dùng
vòng lặp, class, test bằng unit test). Pulumi tương tự CDK nhưng đa cloud.

Với đội data đa cloud hoặc dùng nhiều SaaS (Snowflake, Datadog, GitHub đều có provider Terraform),
Terraform/OpenTofu là lựa chọn an toàn. Đội thuần AWS, nhiều logic sinh resource động có thể chọn CDK.

## Bạn giám sát một pipeline batch nạp đơn hàng mỗi giờ như thế nào?

Theo dõi cả **pipeline** lẫn **dữ liệu**:

- **Freshness**: gauge `last_success_timestamp`; cảnh báo khi `time() - last_success > 2h`.
- **Volume**: số dòng mỗi lần chạy; cảnh báo khi lệch nhiều so với lịch sử cùng giờ (z-score hoặc
  ngưỡng % so với trung bình 7 ngày), đặc biệt khi bằng 0.
- **Duration/latency**: histogram thời gian chạy, cảnh báo p95 tăng.
- **Error rate**: số lần thất bại, số bản ghi bị reject/dead-letter.
- **Data quality**: null, unique, giá trị hợp lệ của `order_status` (Great Expectations, dbt test).

Metric đẩy lên Prometheus Pushgateway hoặc Datadog; exception gửi Sentry; dashboard Grafana; cảnh
báo vào Slack/PagerDuty kèm runbook. Cảnh báo theo triệu chứng, không theo mọi lỗi nhỏ, để tránh
alert fatigue.

## Counter, gauge và histogram trong Prometheus khác nhau thế nào? Cardinality là gì?

Counter chỉ tăng (reset khi process khởi động lại), đọc bằng `rate()`/`increase()`: tổng số dòng đã
xử lý. Gauge lên xuống: consumer lag, timestamp lần thành công cuối, số file đang chờ. Histogram
đếm quan sát vào các bucket, tính được percentile toàn cụm bằng `histogram_quantile(0.95, ...)`:
thời gian chạy job.

Cardinality là số time series khác nhau = tích số giá trị của các label. Đặt label như `order_id`
hay `customer_id` tạo hàng triệu series, làm Prometheus tốn RAM và chậm. Label chỉ nên có tập giá
trị nhỏ, ổn định (`pipeline`, `environment`, `status`).

## Phân biệt unit, integration, end-to-end, smoke và load test cho pipeline dữ liệu.

- **Unit**: một hàm transform với DataFrame nhỏ viết tay. Nhanh, chạy mỗi commit.
- **Integration**: code cùng hệ thống thật (Postgres trong container, SQLite, MinIO): kiểm tra SQL
  đúng dialect, load idempotent, constraint.
- **End-to-end**: chạy cả luồng từ nguồn tới bảng mart/dashboard trên dữ liệu mẫu.
- **Smoke**: kiểm tra nhanh sau deploy rằng hệ thống sống (job khởi động, kết nối DB, có dữ liệu
  hôm nay).
- **Load**: chạy với khối lượng lớn để đo thời gian, RAM, chi phí.

Thêm **functional test** (đúng quy tắc nghiệp vụ) và **data quality test** chạy trên dữ liệu
production mỗi lần nạp. Kim tự tháp: nhiều unit, ít E2E.

## A/B test liên quan gì tới Data Engineer?

A/B test chia người dùng ngẫu nhiên vào nhóm A (bản hiện tại) và B (bản mới) để đo tác động lên
metric (tỉ lệ chuyển đổi). Data Engineer chịu trách nhiệm hạ tầng: ghi log gán nhóm (assignment)
và sự kiện một cách nhất quán, pipeline tính metric theo nhóm, đảm bảo không trùng/mất sự kiện.

Trong phạm vi pipeline, ý tưởng tương tự là **shadow/parallel run**: chạy pipeline cũ và mới song
song trên cùng input, so sánh output (data diff) trước khi chuyển hẳn sang bản mới.

## Thiết kế quy trình đưa một job Spark/pandas từ notebook lên production có CI/CD và giám sát.

1. Tách logic khỏi notebook thành package Python với hàm thuần (`extract`, `transform`, `load`),
   cấu hình qua biến môi trường.
2. Viết unit test cho transform, integration test với DB container; lint bằng ruff.
3. Dockerfile multi-stage, pin version, non-root; lock dependency.
4. Hạ tầng (bucket, DB, IAM role, namespace K8s) bằng Terraform module, state remote, tách môi
   trường.
5. GitHub Actions: PR chạy test; merge vào `main` build image tag SHA, push registry; deploy
   staging (Helm/Kustomize hoặc GitOps với ArgoCD), smoke test; duyệt rồi deploy production.
6. Chạy bằng Airflow `KubernetesPodOperator` hoặc CronJob; job idempotent (ghi theo partition ngày,
   upsert) để retry an toàn.
7. Giám sát freshness, volume, duration, error rate; Sentry cho exception; alert có runbook.
8. Rollback: deploy lại image tag cũ (revert commit trong GitOps).

## Rollback code có tự sửa dữ liệu đã bị phiên bản lỗi ghi sai không?

Không. Nó chỉ đưa cách xử lý về phiên bản trước. Cần xác định partition bị ảnh hưởng, dựng lại hoặc
restore dữ liệu, kiểm tập khóa/tổng tiền và cho downstream cập nhật. Runbook phải mô tả cả code lẫn data.

## Backup thành công đã đủ chứng minh đạt RPO/RTO chưa?

Chưa. Phải thử restore, đo mất bao nhiêu khoảng dữ liệu và mất bao lâu tới lúc người dùng dùng lại.
RPO là mục tiêu lượng dữ liệu có thể mất theo thời gian; RTO là mục tiêu thời gian phục hồi.
Kiểm cả schema, quyền và dependency; file backup tồn tại chưa chứng minh nó đọc được.
