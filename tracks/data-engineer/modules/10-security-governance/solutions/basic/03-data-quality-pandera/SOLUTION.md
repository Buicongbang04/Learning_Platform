# Lời giải: Quality gate cho bảng orders bằng pandera

## Cách làm

- **Mỗi dimension thành một ràng buộc**: completeness → `nullable=False`; uniqueness → `unique=True`;
  validity → kiểu dữ liệu, `Check.isin`, `Check.gt(0)`; consistency → check mức DataFrame
  `delivered_after_purchase` so sánh hai cột trên cùng dòng.
- **`coerce=True`** cho hai cột thời gian: dữ liệu từ CSV/JSON là chuỗi; ép kiểu trong schema giúp phép so
  sánh ngày đúng và bắt luôn chuỗi ngày hỏng.
- **`lazy=True`** gom mọi lỗi trong một lần chạy thay vì dừng ở lỗi đầu tiên; báo cáo cho data owner đủ
  thông tin để sửa một lần.
- **Quarantine theo index**: `failure_cases["index"]` cho biết dòng nào lỗi. Một dòng có thể vi phạm nhiều
  check (o4 vừa status lạ vừa giá âm), nên dùng `set` để không đếm trùng. Check mức DataFrame được pandera
  trả về một dòng cho mỗi cột của dòng lỗi, vì vậy `failed_checks` đếm `nunique()` index chứ không đếm số dòng của `failures`.
- Khi không có lỗi vẫn trả `failures` rỗng có đủ cột để code phía sau (ghi bảng quarantine) không phải rẽ nhánh.

## Dùng trong pipeline

```python
valid, failures = validate(raw_orders)
failures.to_parquet("quarantine/orders/dt=2018-01-10.parquet")
if len(valid) / len(raw_orders) < 0.95:
    raise RuntimeError("Quá nhiều dòng lỗi, dừng publish")  # stop the line
publish(valid)
```

Lỗi mức bảng như trùng khoá trên toàn bảng hay schema đổi nên là *blocking*; lỗi từng dòng thì quarantine.
Great Expectations làm cùng việc với khái niệm Expectation Suite + Checkpoint + Data Docs; dbt tests làm
trong warehouse sau mỗi model.
