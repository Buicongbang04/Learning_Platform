# Hướng làm và rubric: lineage và versioning

## Hướng làm

**A (đội ML, 3 GB/tháng): DVC + remote S3/MinIO.** Con trỏ `.dvc` và `dvc.lock` nằm trong Git, nên mỗi commit xác định đúng một phiên bản dữ liệu. Loại lakeFS (cần server, Postgres và người trực
cho vấn đề không có) và Delta Lake (kéo theo Spark hoặc delta-rs chỉ để có time travel cho 3 GB). Lineage: khi huấn luyện, log vào run MLflow tag `git_commit`, `data_version` (md5 trong `dvc.lock`
của stage ra dữ liệu huấn luyện) và `dvc_lock_sha`. Retention: remote giữ mọi object được tham chiếu bởi commit trên `main` và các tag release; `dvc gc --workspace --cloud` chỉ chạy với `--rev` các tag đó.
Kịch bản hỏng: xoá nhầm object ở remote khiến `dvc pull` ở commit cũ báo missing cache; phát hiện bằng job đêm `dvc status -c` trên các tag release.

Lệnh "sáu tháng sau": `mlflow` lấy run của version production, đọc `git_commit`; `git checkout <commit>`; `dvc pull`; `dvc repro --dry` phải báo "up to date" (xác nhận dữ liệu và code khớp `dvc.lock`);
`dvc repro` hoặc `python train.py` rồi so metric với run gốc. Nếu `dvc pull` lỗi missing cache thì chính sách retention đã hỏng.

**B (data lake 40 TB, nhiều writer): lakeFS** (hoặc Delta nếu mọi bảng đã là Delta). Cần commit nguyên tử trên nhiều bảng, branch để thử pipeline, rollback cả lake: DVC không điều phối nhiều writer, và Delta chỉ cho giao dịch trên từng bảng, không branch cả lake.
Lineage: job chạy trên branch `etl-<run>`, commit lakeFS có metadata `airflow_run_id`, `git_commit`; model ghi `lakefs_commit_id` của commit dữ liệu nó đọc. Chi phí: lakeFS server, Postgres/KV store, người trực; branch ngắn hạn phải dọn. Retention: garbage collection lakeFS theo chính sách ngày giữ cho từng nhánh; commit gắn tag release thì được bảo vệ.
Hỏng: job ghi dở dang vào branch tách biệt nên `main` không thấy, phát hiện bằng kiểm tra chất lượng trước merge; merge nhầm thì `revert`.

**C (stream, time travel để điều tra): Delta Lake** (transaction log). `VERSION AS OF`/`TIMESTAMP AS OF` đáp ứng "bảng lúc 03:00 hôm qua". Loại DVC (snapshot theo commit, không phải theo dòng thời gian của stream) và lakeFS
(thừa cho một bảng). Lineage: ghi `delta_version` đọc được lúc huấn luyện. Retention: `VACUUM` với `delta.deletedFileRetentionDuration` ≥ cửa sổ điều tra (vd. 30 ngày); vacuum ngắn hơn cửa sổ thì time travel hỏng.
Hỏng: VACUUM quá sớm làm mất phiên bản cũ; cảnh báo khi cửa sổ retention nhỏ hơn cửa sổ điều tra đã cam kết.

## Rubric (tối đa 20 điểm)

| Mục | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Chọn công cụ và loại phương án | 6 | mỗi hệ thống có lý do gắn ràng buộc (số writer, kích thước, kiểu truy vấn) |
| Trường lineage cụ thể | 5 | tên trường, nơi lưu, ghi tự động, đủ để tái lập |
| Retention và GC | 3 | chính sách rõ và nêu hệ quả khi GC quá tay |
| Kịch bản hỏng và phát hiện | 3 | cơ chế phát hiện chủ động, không chờ người dùng báo |
| Chuỗi lệnh sáu tháng sau | 3 | chạy được, có bước kiểm "dữ liệu khớp", biết thất bại ở đâu |

Trừ điểm: chọn công cụ nặng nhất cho mọi hệ thống (−4); lineage dựa vào tên tệp hoặc ngày (−3); bỏ qua chi phí vận hành (−2).
Mức đạt: 14/20.
