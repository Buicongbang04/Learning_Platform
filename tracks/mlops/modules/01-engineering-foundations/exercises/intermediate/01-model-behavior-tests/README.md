---
title: Test hành vi model - thứ tự cột và hướng khoảng cách
level: intermediate
services: []
files:
  - path: starter/behavior.py
    note: 4 TODO
  - path: tests/test_behavior.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/01-engineering-foundations/exercises/intermediate/01-model-behavior-tests -q
---

## Mục tiêu

Viết hai bất biến hành vi cho model ETA (invariance và directional expectation) đủ nhạy để bắt model hỏng nhưng không báo động giả với model tốt.

## Đề bài

Độ chính xác trung bình (MAE) không cho biết model có làm điều ngớ ngẩn không. Hai bất biến cho dịch vụ ETA:

1. **Invariance**: đổi thứ tự cột của input không được đổi dự đoán (service nhận JSON, thứ tự khoá không có nghĩa).
2. **Directional**: tăng `trip_distance` (giữ nguyên mọi thứ khác) thì ETA **không giảm trên trung bình**, và không quá nhiều chuyến bị ngược chiều.

`behavior.py` nhận `predict` (hàm `DataFrame -> ndarray`) chứ không nhận model cụ thể, để dùng cho mọi model. Hoàn thành:

- `column_order_shift(predict, X)`: chênh lệch tuyệt đối lớn nhất giữa dự đoán trên `X` và trên `X` đã đảo thứ tự cột.
- `distance_effect(predict, X, factor, column)`: nhân cột với `factor`, trả `(mean_delta, violation_rate)`.
- `assert_column_order_invariant(predict, X, tol)` và `assert_distance_monotonic(predict, X, factor, max_violation_rate)`: `AssertionError` có số đo trong thông báo.

Không được sửa `X` tại chỗ. Test chạy các hàm của bạn trên một model tốt và hai model hỏng cố ý: một model chọn cột theo vị trí (`to_numpy()`), một model học ngược chiều. Nó cũng kiểm tra rằng ngưỡng `max_violation_rate` hoạt động độc lập với trung bình.

## Tiêu chí đạt

- Model chọn cột theo tên: cả hai kiểm tra pass.
- Model theo vị trí: kiểm tra thứ tự cột fail, kiểm tra khoảng cách pass.
- Model học ngược: kiểm tra khoảng cách fail, kiểm tra thứ tự cột pass.
- Hàm đo không thay đổi `X`, chỉ đổi đúng cột được yêu cầu.
- Thông báo lỗi có con số đo được (để người đọc log CI biết mức độ).
- Một model có trung bình tăng nhưng 1/3 chuyến bị ngược chiều bị bắt bởi `max_violation_rate` mặc định và qua được khi nới ngưỡng.

## Gợi ý

### Gợi ý 1

`X[list(X.columns[::-1])]` tạo bản sao với cột đảo ngược; `X.copy()` trước khi nhân cột.

### Gợi ý 2

Tách hai giá trị đo (`mean_delta`, `violation_rate`) khỏi hai hàm `assert_*` để dùng lại khi vẽ báo cáo.

### Gợi ý 3

Vì sao không đòi mọi chuyến đều không giảm: model dạng cây có thể có vùng phẳng hoặc dao động nhỏ, nên trung bình cộng với ngưỡng tỉ lệ ngược chiều thực tế hơn; ràng buộc đơn điệu cứng nằm ở lúc train (`monotonic_cst`).
