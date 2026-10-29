# M11: Đưa nền tảng lên cloud (tuỳ chọn, free tier)

> **Milestone này là TUỲ CHỌN.** Bạn hoàn thành lộ trình mà không cần nó. Làm trên cloud thật có thể
> phát sinh chi phí: chỉ dùng free tier/credit, đặt budget alert **trước khi** tạo bất kỳ resource
> nào, và dọn sạch ngay sau khi chụp kết quả. Không muốn rủi ro thì làm **phương án local** bằng
> LocalStack/MinIO ở cuối trang, giá trị portfolio gần tương đương.

## Mục tiêu

Chuyển phần lõi của Olist Data Platform (lake bronze/silver/gold, một job biến đổi, warehouse để
truy vấn) từ MinIO + DuckDB local lên **một** cloud, hạ tầng tạo bằng Terraform, quyền theo least
privilege, có ước tính chi phí và chứng minh đã dọn tài nguyên. Kết quả là một mục "Cloud deployment"
trong README portfolio, đúng thứ nhà tuyển dụng hỏi: "bạn đã làm gì trên cloud?".

## Việc cần làm

Nếu chọn GCP, dùng [hướng dẫn từng bước](../../modules/11-cloud/cloud-gcp-lab.md) và mẫu
`setup/cloud-gcp/`: chuẩn bị Parquet local → tạo bucket/dataset/danh tính bằng Terraform → load và
transform BigQuery → đối chiếu KPI → thử quyền BI → dọn tài nguyên. Lab viết cho dữ liệu giả; ở milestone
này chạy bước chuẩn bị với Olist thật: `uv run python setup/cloud-gcp/prepare.py --raw data/raw --out /tmp/olist-gcp`
(96 478 đơn đã giao, Parquet ~3,5 MB). Cloud thật cần tài khoản/billing và chưa được chứng minh miễn phí bằng việc
chạy local.

1. **Chuẩn bị tài khoản an toàn** (làm trước mọi thứ):
   - Bật MFA cho tài khoản root/owner, không tạo access key cho root.
   - Tạo **budget alert 5 USD** (AWS Budgets / Azure Cost Management / GCP Budgets) gửi email ở 50%, 80%, 100%.
   - Chọn **một region** và chỉ làm ở đó. Ghi lại region trong `project/infra/cloud/README.md`.
   - Đăng nhập CLI bằng SSO/`gcloud auth application-default login`/`az login`; không lưu access key trong repo.
2. **Chọn đường đi nhỏ, dễ kiểm soát chi phí** (kiểm điều kiện free tier/credit tại thời điểm làm):

   | Cloud | Lake | Biến đổi | Truy vấn |
   | --- | --- | --- | --- |
   | GCP | Cloud Storage | dbt-bigquery hoặc job Python chạy local ghi lên GCS | BigQuery (Sandbox/always free 1 TiB truy vấn/tháng) |
   | AWS | S3 | Job Python/DuckDB chạy local hoặc Lambda | Athena + Glue Data Catalog |
   | Azure | ADLS Gen2 | Job Python chạy local | Synapse serverless SQL pool |

   Tránh các dịch vụ có **phí cố định theo giờ**: MWAA, Cloud Composer, Redshift provisioned, Synapse
   dedicated pool, EMR/Dataproc cluster, NAT gateway. Airflow vẫn chạy local (M05) và trỏ tới cloud.
3. **Terraform** trong `project/infra/cloud/` (mở rộng M08):
   - Bucket lake với versioning, mã hoá, chặn public access, lifecycle (`bronze/` sang class lạnh
     sau 30 ngày, `tmp/` xoá sau 1 ngày), `force_destroy = true` **chỉ cho môi trường học** để
     `destroy` xoá được bucket còn object.
   - Danh tính cho pipeline: IAM role / service account / managed identity với quyền chỉ đọc
     `bronze/`, ghi `silver/` và `gold/`; một danh tính chỉ đọc `gold/` cho BI.
   - Dataset/database warehouse (BigQuery dataset, Glue database + Athena workgroup có giới hạn byte quét).
   - Tag/label `project=olist`, `env=learn`, `owner=<tên bạn>` cho mọi resource.
4. **Nạp và biến đổi**: dùng **Olist thật** (`data/raw/`, ~120 MB CSV, vài chục MB Parquet: với lượng này chi phí
   lưu trữ và truy vấn trong free tier gần như bằng 0, vẫn kiểm lại giá tại thời điểm làm), ghi
   Parquet theo partition `year=/month=/` vào `bronze/`, chạy biến đổi ra `silver/` và `gold/`
   (code M04/M06 chỉ đổi endpoint và credential), tạo external table hoặc load vào warehouse.
5. **Truy vấn và đo chi phí**: chạy 3 truy vấn KPI (doanh thu theo bang/tháng, tỉ lệ giao trễ theo
   seller, review trung bình theo danh mục). Ghi số byte quét của từng truy vấn (BigQuery dry run /
   Athena query stats), so sánh truy vấn có và không có filter partition.
6. **Ước tính chi phí** trong `project/infra/cloud/COST.md`: chi phí thực tế của buổi làm (xem
   billing sau 24 giờ) và ước tính nếu chạy production với 2 GB dữ liệu mới mỗi ngày (dùng mô hình
   ở bài advanced 01 của module 11).
7. **Dọn tài nguyên**:

   ```bash
   cd tracks/data-engineer/capstone/project/infra/cloud
   terraform destroy
   # Kiểm tra lại không còn gì chạy:
   aws resourcegroupstaggingapi get-resources --tag-filters Key=project,Values=olist   # AWS
   gcloud asset search-all-resources --query="labels.project:olist"                   # GCP
   az resource list --tag project=olist -o table                                     # Azure
   ```

   Xoá thêm những thứ Terraform không quản (bucket log, dataset tạo tay, query result bucket của Athena).

### Phương án local (không cần tài khoản cloud)

1. `docker compose -f setup/docker-compose.yml up -d localstack minio`
2. Chạy cùng mã Terraform với `tflocal` (`uv tool install terraform-local`) hoặc provider có
   `endpoints { s3 = "http://localhost:4566", iam = "http://localhost:4566", sts = "http://localhost:4566" }`.
3. Pipeline ghi lake vào S3 của LocalStack (hoặc MinIO), truy vấn bằng DuckDB `httpfs` trỏ tới endpoint đó.
4. Kiểm tra quyền: dùng credential của danh tính BI ghi vào `silver/` phải bị từ chối (LocalStack
   community có thể không thực thi IAM đầy đủ: khi đó kiểm tra bằng MinIO policy như M08, và ghi chú
   giới hạn trong README).
5. `COST.md` vẫn bắt buộc: ước tính chi phí nếu triển khai thật trên cloud bạn chọn.
6. `terraform destroy` / `docker compose -f setup/docker-compose.yml --profile cloud down -v`.

## Kết quả nộp

- `project/infra/cloud/*.tf`, `project/infra/cloud/README.md` (cloud, region, cách chạy, sơ đồ
  mermaid kiến trúc trên cloud), `project/infra/cloud/COST.md`.
- Ảnh chụp (đã che account id): bucket với cấu trúc `bronze/silver/gold`, kết quả 3 truy vấn KPI,
  budget alert đã tạo, output của `terraform destroy` (hoặc bản tương đương local).
- Một đoạn trong README portfolio: "Đã triển khai lên <cloud>: ..." kèm chi phí thực tế.

## Tiêu chí đạt

- [ ] Budget alert được tạo trước resource đầu tiên; không có access key/secret nào trong repo (`git grep -iE "aws_secret|private_key"` sạch).
- [ ] Toàn bộ hạ tầng tạo bằng Terraform; `terraform plan` lần hai báo "No changes".
- [ ] Bucket không public, có mã hoá, versioning, lifecycle; mọi resource có tag/label `project=olist`.
- [ ] Danh tính pipeline và BI tách riêng, least privilege; thử ghi bằng danh tính BI bị từ chối.
- [ ] 3 truy vấn KPI chạy trên warehouse cloud (hoặc DuckDB trên LocalStack/MinIO), có ghi số byte quét và hiệu quả của partition.
- [ ] `COST.md` có chi phí thực tế (hoặc 0 USD với phương án local) và ước tính production có giả định rõ ràng.
- [ ] Sau khi xong, `terraform destroy` thành công và lệnh liệt kê resource theo tag trả về rỗng; billing ngày hôm sau không còn phát sinh.
