# Lời giải: dbt staging và mart

## Cấu trúc

```
dbt_project.yml                 staging -> view, marts -> table
models/staging/_sources.yml     khai báo source olist (schema raw)
models/staging/stg_*.sql        1-1 với bảng nguồn, làm sạch + ép kiểu + dedup
models/staging/_stg.yml         data test
models/marts/fct_revenue_by_state.sql
```

## Vì sao làm vậy

- **Staging là view**: rẻ, luôn phản ánh raw mới nhất, chỉ đổi tên/ép kiểu/dedup, không có logic
  nghiệp vụ. **Mart là table**: được dashboard đọc nhiều lần, build một lần mỗi lượt chạy.
- **`source()` và `ref()`** thay cho tên bảng: dbt biết lineage, build đúng thứ tự, và tên schema
  thay đổi theo môi trường (dev/prod) mà không phải sửa SQL.
- **Dedup bằng `row_number()`** chứ không `distinct`: dữ liệu thật thường trùng khoá nhưng khác vài
  cột (bản cập nhật), `distinct` không bắt được.
- **Gộp payment về mức đơn trước khi join**: đây là lỗi fan-out kinh điển. `o1` có 2 payment; join
  thẳng rồi `count(*)` sẽ đếm `o1` hai lần. Quy tắc: biết rõ *grain* (mỗi dòng là gì) của từng CTE
  trước khi join.
- **Test `unique` trên `order_id`** chính là thứ bắt được dòng trùng `o4` nếu quên dedup; `dbt build`
  dừng các model phía sau khi test của model phía trước lỗi, nên mart không bao giờ được build từ
  dữ liệu bẩn.

## Kết quả

| customer_state | orders | revenue |
| --- | --- | --- |
| RJ | 1 | 50.0 |
| SP | 2 | 150.0 |

MG không có vì `o5` đang `shipped`; `o3` (SP) bị loại vì `canceled`.
