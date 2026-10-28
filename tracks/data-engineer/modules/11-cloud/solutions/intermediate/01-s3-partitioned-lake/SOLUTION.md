# Lời giải: data lake trên S3 bằng boto3

## Cách làm

- **Partition kiểu Hive** (`year=2018/month=01/day=05`): Spark, Athena, Glue, BigQuery external
  table, DuckDB (`hive_partitioning=true`) đều tự nhận cột partition từ đường dẫn, và truy vấn có
  `WHERE year=2018 AND month=1` chỉ đọc đúng thư mục đó (partition pruning). Dùng `f"{dt:%m}"` để
  luôn có 2 chữ số, nhờ đó sắp xếp chuỗi cũng là sắp xếp thời gian.
- **Từ chối `/` trong tên**: một `table="orders/../gold"` có thể ghi đè sang vùng khác.
- **Multipart**: chia `data` theo `part_size`, `PartNumber` bắt đầu từ 1, gom `ETag` để complete.
  Bọc trong `try/except` → `abort_multipart_upload` → `raise`: part đã upload của một multipart chưa
  complete **vẫn bị tính tiền** và không hiện trong `list_objects`. Rule
  `AbortIncompleteMultipartUpload` là lưới an toàn thứ hai cho trường hợp process chết hẳn.
- **Phân trang**: `list_objects_v2` trả tối đa 1000 key mỗi lần. Code chỉ gọi một lần chạy đúng ở
  dev rồi âm thầm thiếu dữ liệu ở prod. Paginator tự xử lý `ContinuationToken`.
- **Lifecycle**: raw ít đọc lại sau khi đã xử lý nên chuyển IA (30 ngày) rồi Glacier (90 ngày);
  `tmp/` (staging của job) tự xoá sau 1 ngày.

## Trong thực tế

- Upload file lớn thường dùng `s3.upload_file(...)` với `boto3.s3.transfer.TransferConfig`
  (`multipart_threshold`, `max_concurrency`): boto3 tự chia part, upload song song và tự abort.
  Viết tay ở đây để hiểu cơ chế (và để trả lời phỏng vấn).
- Tên object nên tránh dồn hết vào một prefix "nóng" khi throughput rất cao; S3 hiện chịu được
  3,500 PUT và 5,500 GET mỗi giây **cho mỗi prefix**.
- Lifecycle `STANDARD_IA` có phí tối thiểu 30 ngày và object tối thiểu tính 128 KB: hàng triệu
  file CSV nhỏ chuyển IA có thể **đắt hơn**. Gộp file nhỏ (compaction) trước.
- Trên Azure: `azure-storage-blob` (`BlobServiceClient`, block blob `stage_block`/`commit_block_list`
  là tương đương multipart), lifecycle management policy với tier Cool/Cold/Archive. Trên GCP:
  `google-cloud-storage` (resumable/composite upload), Object Lifecycle Management với Nearline,
  Coldline, Archive.
