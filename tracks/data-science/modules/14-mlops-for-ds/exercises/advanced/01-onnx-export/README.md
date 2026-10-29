---
title: Xuất model review xấu sang ONNX cho service không viết bằng Python
level: advanced
services: []
files:
  - path: starter/onnx_export.py
    note: 3 hàm TODO
  - path: starter/REPORT.md
    note: Báo cáo cho đội backend
  - path: tests/test_onnx_export.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/14-mlops-for-ds/exercises/advanced/01-onnx-export -q
---

## Mục tiêu

Đội backend của Olist viết dịch vụ đơn hàng bằng Go và muốn gọi model review xấu **trong cùng
tiến trình**, không qua một service Python. Bạn xuất pipeline scikit-learn sang ONNX, chứng minh
output khớp bản gốc, đo độ trễ, và viết hợp đồng đủ rõ để một kỹ sư không biết Python gọi đúng
model.

## Đề bài

1. Trong `starter/onnx_export.py`:
   - `export_onnx(pipeline, numeric, categorical, path) -> Path`: một input ONNX cho mỗi cột, đúng
     tên cột, thứ tự numeric rồi categorical; cột số `float [None, 1]`, cột phân loại
     `string [None, 1]`; output xác suất là ma trận (tắt ZipMap).
   - `onnx_predict_proba(path, df, numeric, categorical) -> np.ndarray`: xác suất lớp 1 bằng
     `onnxruntime`, điền `"missing"` cho cột phân loại thiếu, không sửa `df`.
   - `parity_report(pipeline, path, df, numeric, categorical) -> dict`: ít nhất `n`,
     `max_abs_diff`, `share_within_1e-5`.
2. Áp dụng lên model Olist thật của module (pipeline của bài Intermediate 01, `C = 1.0`, train trên
   đơn trước 2018-01-01, chấm tập test). Đo độ trễ chấm 1 dòng và cả tập test bằng scikit-learn và
   onnxruntime.
3. Viết `starter/REPORT.md` theo khung có sẵn.

Pipeline của module dùng `OneHotEncoder(handle_unknown="ignore")` trực tiếp, cột phân loại đã điền
`"missing"` từ trước. Hãy thử thêm `SimpleImputer(strategy="constant")` cho cột chuỗi rồi xuất, để
thấy converter từ chối, và ghi lại vào báo cáo.

## Tiêu chí đạt

- Tệp ONNX hợp lệ (`onnx.checker`), input đúng tên và thứ tự.
- Logistic regression: sai lệch lớn nhất dưới 1e-5 trên 3 000 dòng, kể cả bang chưa thấy, số
  thiếu, loại thanh toán thiếu, và khi chấm một dòng.
- Random forest: ít nhất 99% dòng lệch không quá 1e-5 (`parity_report`).
- `REPORT.md` không còn TODO, ít nhất 350 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`skl2onnx.to_onnx(pipeline, initial_types=[("price", FloatTensorType([None, 1])), ...,
("customer_state", StringTensorType([None, 1]))], options={"zipmap": False})`. Output thường có
tên `label` và `probabilities`: xem `session.get_outputs()`.

### Gợi ý 2

Input là dict tên cột → mảng 2 chiều: `df[[c]].to_numpy(np.float32)` cho cột số (NaN giữ nguyên,
imputer trong graph xử lý), `df[[c]].astype(object).where(df[[c]].notna(), "missing").astype(str)`
cho cột chuỗi. Với cây quyết định, ONNX so ngưỡng trên `float32`: một giá trị nằm giữa ngưỡng
`float64` và bản làm tròn `float32` của nó sẽ rẽ nhánh khác.
