# Lời giải: chọn công cụ versioning và kiểm dữ liệu

1. **git-holds (b)**: `dvc add` ghi con trỏ `.dvc` (md5, size, path) vào Git; dữ liệu nằm trong `.dvc/cache` và remote. Không có nhánh
   orphan hay Git LFS nào ở đây.
2. **lock-role (a)**: `dvc.yaml` là *khai báo* (cmd, deps, outs); `dvc.lock` là *kết quả* (hash thật của từng dep và out ở lần chạy cuối).
   Commit cả hai thì checkout commit cũ + `dvc checkout` dựng lại đúng dữ liệu. Xoá `dvc.lock` thì mọi stage chạy lại.
3. **tool-lake (a)**: nhiều writer, cần commit nguyên tử và rollback: lakeFS (lớp branch/commit trên object storage) hoặc Delta
   Lake (transaction log trên bảng). DVC quản lý tệp của một repo, không điều phối giao dịch ghi đồng thời.
4. **tool-small (c)**: 3 GB, một đội, gắn train với commit: DVC + remote object storage. lakeFS và Delta vận hành nặng hơn nhiều so với vấn đề.
5. **pandera-ge (d)**: GE mạnh khi cần Data Docs (báo cáo HTML), chạy trên SQL/Spark và cho người ít code. Pandera mạnh khi luật
   nằm trong code Python cạnh hàm biến đổi. Tốc độ không phải lý do chọn.
6. **contract-owner (b)**: lỗi là *thiếu hợp đồng*, không phải thiếu try/except. Contract có version, người sở hữu, và test ở
   CI phía đội data để họ biết mình phá ai trước khi merge.
7. **repro-skip (b)**: DVC so hash `cmd`, `deps`, `params` hiện tại với `dvc.lock`; khớp thì bỏ qua. Lỗi stage làm `dvc repro` dừng, không "bỏ qua".
8. **lineage-multi (a, b)**: tên tệp không xác định nội dung (c sai). Xoá dữ liệu khỏi remote thì commit cũ không dựng lại được dù con trỏ còn (d sai): phải
   giữ retention của remote bằng chính sách, không bằng hy vọng.
