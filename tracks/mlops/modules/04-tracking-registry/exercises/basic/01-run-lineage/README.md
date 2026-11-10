---
title: Lineage cho run - git commit, trạng thái cây thư mục và phiên bản dữ liệu
level: basic
services: []
files:
  - path: starter/lineage.py
    note: 4 hàm TODO
  - path: tests/test_lineage.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/basic/01-run-lineage -q
---

## Mục tiêu

Mỗi run trong MLflow phải trả lời được hai câu hỏi sáu tháng sau: "code nào đã train ra nó" và "dữ liệu nào".
Bạn viết phần ghi lineage (git commit, cây thư mục có bẩn không, phiên bản dữ liệu lấy từ `dvc.lock`) và phần
truy ngược: từ một phiên bản dữ liệu tìm lại mọi run đã dùng nó.

## Đề bài

Bài chạy trên MLflow cục bộ (SQLite trong thư mục tạm, không cần bật stack). Trong `starter/lineage.py`:

1. `git_state(repo) -> dict`: `{"commit": <40 ký tự>, "dirty": bool}`. Tệp mới chưa `git add` cũng làm cây thư mục "bẩn".
2. `data_version_from_lock(lock_path, stage) -> str`: md5 của output đầu tiên của stage trong `dvc.lock`
   (cấu trúc `stages.<tên>.outs[0].md5`, như file `dvc.lock` bạn tạo ở module 03). Stage không tồn tại hoặc không có
   `outs` thì `ValueError` nêu tên stage.
3. `log_run(tracking_uri, experiment_id, params, metrics, repo, lock_path, stage) -> str`: một run `FINISHED` có
   params, metrics và ba tag `git_commit`, `git_dirty` (`"true"`/`"false"`), `data_version`. Dùng `MlflowClient`,
   không đổi tracking URI toàn cục. Lỗi giữa chừng khi ghi param/metric thì lỗi vẫn được ném ra và run phải là `FAILED`, không để `RUNNING` treo.
4. `find_runs(tracking_uri, experiment_id, data_version=None, git_commit=None) -> list[str]`: run_id của các run
   `FINISHED` khớp mọi điều kiện đã cho, mới nhất đứng đầu.

## Tiêu chí đạt

- Cây thư mục sạch cho `git_dirty = "false"`, sửa một tệp hay thêm tệp mới cho `"true"`.
- `data_version` đổi khi `dvc.lock` đổi, và `find_runs` tách đúng các run theo phiên bản dữ liệu và theo commit.
- Ghi param hoặc metric lỗi giữa chừng không để lại run `RUNNING`.
- Run `FAILED` không bao giờ xuất hiện trong kết quả `find_runs`.
- Gọi `log_run` với một tracking URI khác không làm đổi `mlflow.get_tracking_uri()` của tiến trình.

## Gợi ý

### Gợi ý 1

`subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True, check=True)`:
output rỗng nghĩa là sạch. `client.create_run(experiment_id, tags={...})` đặt tag ngay lúc tạo run.

### Gợi ý 2

`search_runs(..., filter_string="attributes.status = 'FINISHED' and tags.data_version = 'abc'",
order_by=["attributes.start_time DESC"])`. Ghép điều kiện bằng `and`; chỉ thêm điều kiện nào được truyền vào.
