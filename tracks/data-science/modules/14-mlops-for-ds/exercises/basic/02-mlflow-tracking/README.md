---
title: Ghi và tìm lại thí nghiệm bằng MLflow Tracking
level: basic
services: []
files:
  - path: starter/tracking.py
    note: 3 hàm TODO
  - path: tests/test_tracking.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/14-mlops-for-ds/exercises/basic/02-mlflow-tracking -q
---

## Mục tiêu

Dùng MLflow Tracking bằng API tường minh (`MlflowClient`) thay vì "bật autolog và hy vọng": biết
dữ liệu nằm ở đâu (backend store và artifact store), ghi params/metrics/tags đúng cách và tìm lại
run tốt nhất bằng truy vấn thay vì bằng mắt trên UI.

## Đề bài

Trong `starter/tracking.py`, mọi hàm nhận `tracking_uri` (ví dụ `sqlite:////tmp/x/mlflow.db`) và
dùng `MlflowClient(tracking_uri)`, không đổi tracking URI toàn cục:

1. `get_or_create_experiment(tracking_uri, name, artifact_root) -> str`: trả `experiment_id`.
   Tạo mới thì đặt `artifact_location` bên trong `artifact_root`.
2. `log_training_run(tracking_uri, experiment_id, params, metrics, tags=None) -> str`: một run
   gồm params, metrics, tags, kết thúc `FINISHED`. Metric là list thì phần tử thứ i ghi ở step i.
3. `best_run(tracking_uri, experiment_id, metric, higher_is_better=True) -> dict`: run tốt nhất
   trong các run `FINISHED` có ghi metric đó; trả `run_id`, `params`, `value`. Không có thì
   `ValueError`.

Không chạy được bằng file store `./mlruns`: MLflow 3 đã đưa file store vào chế độ bảo trì và báo lỗi
nếu không đặt `MLFLOW_ALLOW_FILE_STORE=true`. Dùng SQLite, như test.

## Tiêu chí đạt

- Gọi `get_or_create_experiment` hai lần trả cùng id; `artifact_location` nằm trong `artifact_root`.
- Params được lưu dạng chuỗi (`C=0.1` thành `"0.1"`), metric list thành các step 0, 1, 2…
- `best_run` chọn đúng theo cả hai chiều (AUC lớn nhất, logloss nhỏ nhất), bỏ qua run `FAILED`
  và run không có metric, báo lỗi khi experiment rỗng.
- Không tệp hay thư mục nào bị tạo trong thư mục làm việc hiện tại.

## Gợi ý

### Gợi ý 1

`client.get_experiment_by_name(name)` trả `None` nếu chưa có. `Path(artifact_root).resolve().as_uri()`
cho một URI `file:///...` tuyệt đối; đường dẫn tương đối sẽ được hiểu theo thư mục đang chạy, đúng
cái bẫy mà test kiểm.

### Gợi ý 2

`client.search_runs([exp_id], filter_string="attributes.status = 'FINISHED' and metrics.val_auc > -1e308",
order_by=["metrics.val_auc DESC"], max_results=1)`. Điều kiện `> -1e308` là cách loại run không
có metric đó. Bọc phần ghi trong `try` và đặt run `FAILED` khi có lỗi, để run dở dang không bị
nhầm là run tốt.
