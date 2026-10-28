# Lab GCP: Parquet → Cloud Storage → BigQuery → KPI

Đây là đường đi cụ thể cho [M11](../../capstone/milestones/m11-cloud-deploy.md).
Dùng dữ liệu giả và một project học riêng. Phần chuẩn bị chạy local; các lệnh Terraform/gcloud/bq
phía sau được người học chạy khi đã có tài khoản và chọn làm cloud thật.

## 1. Chuẩn bị local và định nghĩa số liệu

```bash
uv run python data/generate_olist.py --orders 2000 --out /tmp/olist-gcp-source
uv run python setup/cloud-gcp/prepare.py --raw /tmp/olist-gcp-source --out /tmp/olist-gcp
```

Script không gọi cloud. Nó tạo Parquet với grain **một đơn đã giao**, các cột order_id, order_date,
customer_state, item_revenue. Tiền là tổng price, không cộng vận chuyển; ngày là ngày mua theo giá trị
trong nguồn, chưa chuyển timezone. Đó là contract của lab. Baseline CSV nhóm theo ngày/bang dùng đối chiếu.

Luồng này biến đổi lần một local để rút gọn dữ liệu; BigQuery thực hiện bước tổng hợp KPI. Nó chưa phải
pipeline ingest CSV thô hoàn toàn trên cloud. Muốn mở rộng, thay bước local bằng job managed và giữ contract.

## 2. Tài khoản, CLI và danh tính

Cài Google Cloud CLI (có bq) và Terraform >= 1.5. Tạo project **riêng cho lab**, kết nối billing,
đặt budget alert; kiểm hạn mức và giá tại thời điểm làm. Alert không tự chặn chi tiêu.
Mẫu dùng vị trí US cho cả bucket và dataset để tránh sai location.

```bash
gcloud auth login
# Tạo một lần; nếu đã có configuration này thì chỉ cần export bên dưới.
gcloud config configurations create olist-learning --no-activate
export CLOUDSDK_ACTIVE_CONFIG_NAME="olist-learning"
gcloud auth application-default login
export task_project="THAY_BANG_PROJECT_ID_LAB"
export TF_VAR_project_id="$task_project"
export task_raw_bucket="${task_project}-olist-lab-raw"
export task_curated_bucket="${task_project}-olist-lab-curated"
export task_pipeline_sa="olist-lab-pipeline@${task_project}.iam.gserviceaccount.com"
export task_bi_sa="olist-lab-bi@${task_project}.iam.gserviceaccount.com"
```

Thay placeholder trước khi chạy. Các tên bucket phải chưa tồn tại. Người triển khai cần quyền bật API,
tạo resource và gán IAM trong project. Để thử service account bằng CLI, người triển khai còn cần quyền
Service Account Token Creator trên đúng hai account lab; nhờ quản trị viên cấp nếu bạn không có quyền.
Không tạo JSON key để né quyền impersonation. Không dùng danh tính BI/pipeline có quyền kế thừa rộng từ tổ chức.

## 3. Tạo hạ tầng có thể kiểm lại

Chạy từ gốc repo:

```bash
terraform -chdir=setup/cloud-gcp init
terraform -chdir=setup/cloud-gcp fmt -check
terraform -chdir=setup/cloud-gcp validate
terraform -chdir=setup/cloud-gcp plan -out=/tmp/olist-gcp-plan
terraform -chdir=setup/cloud-gcp apply /tmp/olist-gcp-plan
terraform -chdir=setup/cloud-gcp plan
```

Đọc plan trước apply. Hai bucket raw/curated, hai dataset staging/analytics và hai service account do
Terraform quản; bảng sinh từ load/query thuộc inventory dữ liệu. Mẫu dùng force_destroy và xóa nội dung
dataset khi destroy, chỉ áp dụng resource lab. Soft-delete của bucket lab bị tắt để dễ dọn; production
phải chọn retention theo yêu cầu khôi phục. State Terraform có thông tin cấu hình: không commit state.

## 4. Upload bằng người triển khai, load bằng pipeline

Pipeline đọc raw, ghi curated và hai dataset; BI chỉ đọc analytics và tạo query job.

```bash
gcloud storage cp /tmp/olist-gcp/orders.parquet "gs://${task_raw_bucket}/bronze/orders.parquet" --project="$task_project"
gcloud config set auth/impersonate_service_account "$task_pipeline_sa"
bq --project_id="$task_project" --location=US load \
  --replace --source_format=PARQUET \
  "${task_project}:olist_staging.orders" "gs://${task_raw_bucket}/bronze/orders.parquet"
```

Trong bq, `--replace` ghi đè toàn bộ bảng đích; dùng an toàn ở bảng staging lab, không nhầm với
overwrite một partition production. Chạy lại lệnh load phải giữ số dòng/tổng tiền.
Xem [load Parquet từ Cloud Storage](https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-parquet).

## 5. Chạy transform và đối chiếu

SQL dưới chỉ dùng trong project lab. Giới hạn byte quét nhằm tránh truy vấn vượt dự kiến:

```bash
gcloud config set auth/impersonate_service_account "$task_pipeline_sa"
bq --project_id="$task_project" --location=US query \
  --use_legacy_sql=false --maximum_bytes_billed=100000000 \
  'CREATE OR REPLACE TABLE olist_analytics.daily_revenue
   PARTITION BY order_date AS
   SELECT order_date, customer_state, COUNT(*) AS orders, SUM(item_revenue) AS item_revenue
   FROM olist_staging.orders GROUP BY 1,2'
gcloud config set auth/impersonate_service_account "$task_bi_sa"
bq --project_id="$task_project" --location=US --format=csv query \
  --use_legacy_sql=false --maximum_bytes_billed=100000000 --max_rows=10000 \
  'SELECT order_date, customer_state, orders, item_revenue
   FROM olist_analytics.daily_revenue ORDER BY 1,2' > /tmp/olist-gcp/actual_daily_revenue.csv
```

So kết quả theo cặp ngày/bang với expected_daily_revenue.csv, không chỉ nhìn tổng toàn bảng.
Tiền NUMERIC là số chính xác; khi đọc CSV dùng Decimal và chuẩn hóa ngày để tránh khác định dạng.
Lưu job ID, thời gian và bytes processed từ job details. Thử dry run bằng bq query --dry_run trước
truy vấn lớn; [bq CLI reference](https://docs.cloud.google.com/bigquery/docs/reference/bq-cli-reference).

## 6. Quyền, lỗi và xuất kết quả

Dùng BI đọc staging phải thất bại:

```bash
gcloud config set auth/impersonate_service_account "$task_bi_sa"
bq --project_id="$task_project" --location=US query \
  --use_legacy_sql=false 'SELECT * FROM olist_staging.orders LIMIT 1'
```

Nếu lệnh thành công, điều tra quyền kế thừa; không coi phân quyền đã đạt.
Sau đó dùng pipeline xuất analytics ra curated:

```bash
gcloud config set auth/impersonate_service_account "$task_pipeline_sa"
bq --project_id="$task_project" --location=US extract \
  --destination_format=PARQUET "${task_project}:olist_analytics.daily_revenue" \
  "gs://${task_curated_bucket}/gold/daily-*.parquet"
```

Tạo bản Parquet sai schema riêng để thử load lỗi, không ghi đè bản chuẩn. Ghi thông báo lỗi,
kiểm bảng đã xuất bản còn nguyên, sửa dữ liệu rồi chạy lại. Thử BI ghi bảng mới trong analytics:
phải bị từ chối. Không thử DELETE bảng chuẩn để kiểm quyền.

## 7. Inventory và dọn tài nguyên

Nộp sơ đồ, baseline/đối chiếu, job ID, kết quả quyền cho phép/từ chối và COST.md ghi giả định, giá,
chi phí quan sát. Có thể có độ trễ cập nhật billing; kiểm tiếp sau buổi lab.

```bash
gcloud config unset auth/impersonate_service_account
terraform -chdir=setup/cloud-gcp plan -destroy
terraform -chdir=setup/cloud-gcp destroy
gcloud storage buckets list --project="$task_project"
bq --project_id="$task_project" ls
gcloud iam service-accounts list --project="$task_project"
```

Destroy xóa dữ liệu do **mẫu lab này** quản. Giữ inventory để kiểm thêm bảng, object version, tài nguyên
tạo ngoài Terraform; liệt kê rỗng theo label chưa chứng minh toàn project không phát sinh phí.
Không xóa project đang dùng chung. Cuối buổi, `unset CLOUDSDK_ACTIVE_CONFIG_NAME` để trở về configuration trước. Nếu trước lab bạn đã đặt biến này, lưu và khôi phục giá trị cũ thay vì unset. Nếu không chạy cloud thật, nộp bản thiết kế và baseline local,
ghi rõ chưa kiểm chứng cloud/IAM/billing.
