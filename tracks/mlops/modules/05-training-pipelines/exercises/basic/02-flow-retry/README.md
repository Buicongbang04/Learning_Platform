---
title: Flow Prefect train, evaluate, register với retry cho bước đọc dữ liệu
level: basic
services: []
files:
  - path: starter/pipeline.py
    note: 5 hàm TODO
  - path: tests/test_flow.py
    note: Không sửa
  - path: tests/conftest.py
    note: Dựng Prefect tạm cho test, không sửa
run:
  - uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/basic/02-flow-retry -q
---

## Mục tiêu

Dựng flow Prefect 3 `đọc dữ liệu -> train -> evaluate -> register` và đặt retry đúng chỗ, đúng loại lỗi: lỗi tạm thời thì thử
lại, lỗi vĩnh viễn thì dừng ngay, model dưới ngưỡng thì không đăng ký.

## Đề bài

Không cần Prefect server: `tests/conftest.py` dùng `prefect_test_harness()` (một server tạm, tự dọn). Lần chạy đầu mất khoảng
20 giây để khởi động. MLflow chạy cục bộ trên SQLite (`mlopskit.mlflow_local`), không cần stack.

Trong `starter/pipeline.py` (đã có `split(df, seed)`) cài:

- `read_data(loader)`: **task** Prefect gọi `loader()` lấy DataFrame. Thử lại tối đa **2 lần** (tức 3 lần gọi) khi gặp
  `ConnectionError` hoặc `TimeoutError`; lỗi khác (ví dụ `ValueError`) không được thử lại. Mỗi lần chờ không quá 1 giây
  (`retry_delay_seconds` ≤ 1) để test chạy nhanh.
- `train_model(train_df, seed)`: task, `RandomForestRegressor(n_estimators=20, max_depth=6, random_state=seed, n_jobs=1)`.
- `evaluate_model(model, test_df)`: task trả R2 trên tập kiểm.
- `register_model(model, r2, tracking_uri, model_name, min_r2, seed)`: task. Nếu `r2 < min_r2` trả `None` và không ghi gì vào
  MLflow. Ngược lại log một run (param `seed`, metric `r2`, model, ví dụ đầu vào), đăng ký version mới của `model_name`
  (tạo registered model nếu chưa có) và trả số version (`int`).
- `training_flow(loader, tracking_uri, model_name="taxi-eta", min_r2=0.5, seed=0)`: **flow** nối các bước, trả
  `{"r2": float, "version": int | None}`. `loader` là một đối tượng gọi được, nên flow cần `validate_parameters=False`.

## Tiêu chí đạt

- Loader hỏng 2 lần rồi thành công: flow xong, `loader.calls == 3`, có đúng một version.
- Loader hỏng 3 lần (`ConnectionError`): flow ném `ConnectionError`, `loader.calls == 3`, registry không có gì.
- `TimeoutError` cũng được thử lại; `ValueError` chỉ gọi 1 lần.
- `min_r2` cao hơn R2 đạt được: `version` là `None` và registry trống.
- Version đăng ký liên kết tới run có `seed` và `r2`; chạy lần hai ra version 2; cùng `seed` ra cùng R2.

## Gợi ý

### Gợi ý 1

Prefect 3 cho `@task(retries=..., retry_delay_seconds=..., retry_condition_fn=...)`. `retry_condition_fn(task, task_run, state)`
trả `True` nếu nên thử lại; lấy ngoại lệ đã xảy ra bằng `state.result(raise_on_failure=False)`.

### Gợi ý 2

MLflow 3 lưu model sklearn bằng định dạng `skops` và từ chối kiểu chưa được tin cậy; với random forest kiểu đó là
`sklearn.tree._tree.Tree`. Truyền `skops_trusted_types=["sklearn.tree._tree.Tree"]` vào `mlflow.sklearn.log_model`. Đăng ký bằng `client.create_model_version(name, info.model_uri, run_id, model_id=info.model_id)`.
