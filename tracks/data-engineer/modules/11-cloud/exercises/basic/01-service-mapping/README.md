---
title: Bảng dịch vụ tương đương AWS, Azure, GCP
level: basic
services: []
files:
  - path: starter/cloud_map.py
    note: 4 TODO
  - path: tests/test_service_mapping.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/11-cloud/exercises/basic/01-service-mapping -q
---

## Mục tiêu

Thuộc lòng "từ điển" dịch vụ data giữa ba cloud lớn và biết tra ngược: nghe một tên dịch vụ lạ
trong JD là biết nó thuộc nhóm nào và tương đương với gì trên cloud bạn đã quen.

## Đề bài

Trong `starter/cloud_map.py`, `CATALOG` là bảng `nhóm -> {cloud: tên chuẩn}` cho 6 nhóm
`compute`, `object_storage`, `managed_sql`, `etl`, `warehouse`, `streaming` và 3 cloud `aws`,
`azure`, `gcp`. `ALIASES` ánh xạ cách gọi khác (chữ thường) về tên chuẩn.

1. **TODO 1**: điền các ô còn thiếu trong `CATALOG` (đang là `"TODO"`). Tên chuẩn dùng đúng như
   bảng trong README của module: `EC2`, `Virtual Machines`, `Compute Engine`, `S3`, `Blob Storage`,
   `Cloud Storage`, `RDS`, `SQL Database`, `Cloud SQL`, `Glue`, `Data Factory`, `Dataflow`,
   `Redshift`, `Synapse Analytics`, `BigQuery`, `Kinesis`, `Event Hubs`, `Pub/Sub`.
2. **TODO 2** `lookup(name) -> tuple[str, str]`: trả `(nhóm, cloud)` của một tên dịch vụ. Không
   phân biệt hoa thường, bỏ khoảng trắng hai đầu, chấp nhận alias trong `ALIASES` và chấp nhận tiền
   tố hãng `amazon `, `aws `, `azure `, `google cloud `, `google `, `gcp ` (vd. `"Amazon S3"`,
   `"Azure Blob Storage"`, `"Google Cloud Storage"`). Tên không biết thì `raise ValueError`.
3. **TODO 3** `equivalent(name, target) -> str`: tên chuẩn của dịch vụ tương đương trên cloud
   `target` (`aws`/`azure`/`gcp`, không phân biệt hoa thường). `target` sai thì `ValueError`.
   Hỏi tương đương trên chính cloud của nó thì trả lại tên chuẩn của nó.
4. **TODO 4** `comparison_table(categories=None) -> str`: bảng Markdown, dòng đầu
   `| Category | AWS | Azure | GCP |`, dòng thứ hai `| --- | --- | --- | --- |`, mỗi nhóm một dòng
   theo thứ tự trong `categories` (mặc định thứ tự của `CATALOG`). Kết thúc bằng `\n`.

## Tiêu chí đạt

- `CATALOG` đủ 6 nhóm x 3 cloud, không còn `"TODO"`, không trùng tên giữa các ô.
- `lookup("Amazon S3") == ("object_storage", "aws")`, `lookup("gcs") == ("object_storage", "gcp")`.
- `equivalent("BigQuery", "aws") == "Redshift"`, `equivalent("Kinesis Data Streams", "gcp") == "Pub/Sub"`.
- Tên lạ hoặc cloud lạ ném `ValueError`.
- `comparison_table()` có header, dòng phân cách và 6 dòng dữ liệu đúng thứ tự.

## Gợi ý

### Gợi ý 1

Viết một hàm nội bộ `_canonical(name)`: chuẩn hoá chữ thường, thử alias, rồi thử bỏ lần lượt các
tiền tố hãng. Sau đó dò `CATALOG` để so khớp với tên chuẩn viết thường.

### Gợi ý 2

Xử lý tiền tố dài trước (`google cloud ` trước `google `), nếu không `"google cloud storage"` sẽ
thành `"cloud storage"` chỉ nhờ may mắn, còn `"google cloud sql"` vẫn đúng. Dựng sẵn một dict
ngược `tên chuẩn viết thường -> (nhóm, cloud)` cho gọn.
