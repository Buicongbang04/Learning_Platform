# Lời giải: bộ check cho pipeline

## Ý tưởng

Mỗi check tương ứng một dòng trong đặc tả, và dữ liệu được thiết kế để làm lộ đúng loại bug:

| Check | Loại test | Dữ liệu làm lộ bug | Mutant bị bắt |
| --- | --- | --- | --- |
| `check_clean_drops_null_order_id` | Unit | Một dòng `order_id=None` | `clean_keeps_null_ids` |
| `check_clean_normalizes_status` | Unit | `" shipped "`, `"SHIPPED"` | `clean_status_not_normalized` |
| `check_clean_keeps_latest_duplicate` | Unit | `o2` bản cũ đứng trước bản mới | `clean_keeps_first_seen` |
| `check_revenue_excludes_canceled` | Functional | `o3` canceled với số tiền rất lớn | `revenue_includes_canceled` |
| `check_revenue_sorted_desc` | Functional | SP > RJ nhưng RJ đứng trước theo alphabet | `revenue_sorted_by_state` |
| `check_load_is_idempotent` | Integration | Load hai lần vào SQLite | `load_appends` |
| `check_load_upserts_new_values` | Integration | Lần hai đổi `order_status` | `load_ignores_updates` |

## Bài học

- **Test xanh chưa chắc tốt**: bộ test mà dữ liệu "quá đẹp" (không trùng, không null, đã sắp sẵn)
  vẫn pass với code lỗi. Mutation testing (thư viện `mutmut`, `cosmic-ray`) đo điều này tự động.
- **Integration test** với SQLite in-memory rẻ và nhanh; với SQL đặc thù Postgres (`ON CONFLICT`,
  `jsonb`) nên chạy trên Postgres thật trong container (service container của CI).
- **Idempotency** phải được test bằng cách chạy hai lần, và **upsert** phải được test bằng cách
  đổi dữ liệu ở lần hai; hai tính chất này khác nhau (`INSERT OR IGNORE` idempotent nhưng không cập
  nhật).
- Trong repo thật, đổi `check_*` thành `test_*` trong `tests/` và dùng pytest fixture cho dữ liệu.
