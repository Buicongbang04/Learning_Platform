---
title: "Olist: tracking thí nghiệm và Model Registry với MLflow"
level: intermediate
services: []
files:
  - path: starter/registry.ipynb
    note: 3 hàm TODO
  - path: tests/test_registry.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/14-mlops-for-ds/exercises/intermediate/01-olist-tracking-registry/starter/registry.ipynb
  - uv run pytest tracks/data-science/modules/14-mlops-for-ds/exercises/intermediate/01-olist-tracking-registry -q
---

## Mục tiêu

Đi trọn đường từ "train trong notebook" tới "model có phiên bản trong registry mà service nạp
được": mỗi lần train là một run có params, metric và model kèm signature; chọn run tốt nhất trên
validation; đăng ký và gắn alias `champion`; nạp lại theo alias.

## Đề bài

Model dự đoán đơn Olist bị review xấu (`review_score <= 2`), chấm **lúc đơn vừa giao xong**: được
dùng số ngày giao thật và số ngày trễ, không được dùng cột nào sinh ra từ review. Notebook có sẵn
`load_olist_table`, `time_split` (train trước 2018-01-01, validation tới trước 2018-04-01, test
tới hết 2018-08-31) và `build_pipeline(C)`. Bạn viết:

1. `train_and_log(train, val, C, tracking_uri, experiment_id) -> str`: fit, ghi param `C` và
   `n_train`, metric `val_auc`, model ở `name="model"` với signature suy từ `train[FEATURES]`
   (cột số dạng float), `input_example`, `pyfunc_predict_fn="predict_proba"`. Trả `run_id`.
2. `register_best(tracking_uri, experiment_id, model_name, metric="val_auc") -> int`: đăng ký model
   của run `FINISHED` tốt nhất, gắn alias `champion`, trả số version.
3. `load_champion(tracking_uri, model_name)`: `mlflow.pyfunc.load_model("models:/<tên>@champion")`.

Chạy các cell `explore`: 4 giá trị C, đăng ký, chấm test **một lần**, xem lỗi khi gửi thiếu cột.
Trả lời ba câu hỏi ở cuối notebook.

## Tiêu chí đạt

- Run có `C`, `n_train`, `val_auc`; nạp lại model của run cho đúng `val_auc` đã ghi.
- Signature có đúng 12 cột `FEATURES` theo thứ tự; model nạp qua pyfunc trả ma trận xác suất 2 cột.
- `register_best` gắn `champion` cho run tốt nhất; khi có run tốt hơn thì tạo version mới và chuyển
  alias, version cũ vẫn còn.
- Model champion từ chối đầu vào thiếu cột.
- Trên Olist thật: 43 362 / 20 468 / 31 994 đơn; `C = 1.0` cho `val_auc` ≈ 0.799.

## Gợi ý

### Gợi ý 1

`mlflow.sklearn.log_model` là fluent API: cần `mlflow.set_tracking_uri(tracking_uri)` và
`with mlflow.start_run(experiment_id=experiment_id):`. MLflow 3 mặc định lưu model scikit-learn bằng
định dạng **skops** (an toàn hơn pickle) và từ chối nạp kiểu dữ liệu chưa khai báo: thêm
`skops_trusted_types=["numpy.dtype"]`.

### Gợi ý 2

Schema enforcement của MLflow **không** tự đổi `int64` sang `float64`: suy signature trên dữ liệu đã
ép float, và suy trên cả tập train để cột có NaN thật (như `approve_hours`) được đánh dấu optional.
Alias: `MlflowClient(uri).set_registered_model_alias(name, "champion", version)`.
