# Lời giải: lineage cho run

Cách làm nằm trong `lineage.py` cạnh tệp này. Bốn quyết định đáng nhớ:

- **`git status --porcelain` thay vì `git diff`.** `git diff` bỏ qua tệp chưa được theo dõi; một `train.py` mới chưa add
  vẫn làm kết quả không tái lập được từ commit. Output rỗng nghĩa là sạch, không cần phân tích định dạng.
- **Tag `git_dirty` đi cùng `git_commit`.** Một commit hash mà cây thư mục bẩn là lời nói dối: người đọc tin rằng checkout
  commit đó sẽ tái lập được run. Tag bẩn cho phép cổng promotion (bài 03 trung cấp) từ chối model train từ cây bẩn.
- **`data_version` là hash nội dung từ `dvc.lock`**, không phải tên tệp hay ngày. `dvc.lock` do `dvc repro` ghi, đã nằm
  trong git, nên `git_commit` + `data_version` chốt được cả hai đầu. Output là thư mục thì md5 có đuôi `.dir`, vẫn dùng như
  một chuỗi định danh.
- **`MlflowClient(uri)` thay vì fluent API.** `mlflow.start_run()` dùng tracking URI toàn cục và run "đang hoạt động" của
  tiến trình; trong test hoặc service chạy nhiều luồng, ghi nhầm vào run khác là lỗi khó tìm. Bọc phần ghi trong `try` để
  run chết giữa chừng thành `FAILED`; không thì `RUNNING` treo mãi trong UI và còn bị `search_runs` thấy.

Lỗi hay gặp: đặt filter `tags.data_version = ...` mà không lọc `status`, rồi chọn nhầm run đã chết; hoặc lấy commit bằng
`git rev-parse --short` (7 ký tự) rồi gặp va chạm khi repo lớn.
