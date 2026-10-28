# Lời giải: dbt incremental và snapshot

## Incremental model

- Lần chạy đầu (bảng chưa có) `is_incremental()` là `false` → dbt tạo bảng từ toàn bộ nguồn.
- Lần sau `is_incremental()` là `true` → khối `where` được chèn, dbt build kết quả vào bảng tạm rồi
  áp vào bảng đích theo `incremental_strategy`:

| Strategy | Cách làm | Hỗ trợ (ví dụ) |
| --- | --- | --- |
| `append` | Chỉ `INSERT` | Mọi adapter, cho event log không cập nhật |
| `delete+insert` | Xoá các khoá có trong lô mới rồi chèn | DuckDB, Postgres, Snowflake |
| `merge` | `MERGE INTO ... WHEN MATCHED` | Snowflake, BigQuery, Databricks, DuckDB mới |
| `insert_overwrite` | Ghi đè cả partition | BigQuery, Spark |

Lời giải dùng `delete+insert` với `unique_key='order_id'`: `o1` bị xoá rồi chèn lại bản mới, nên
không trùng.

**`o0` không vào bảng** vì `updated_at` của nó nhỏ hơn `max(updated_at)` đã có. Đây là đặc điểm
(và rủi ro) của incremental dựa trên timestamp: dữ liệu đến muộn bị bỏ sót. Cách chữa:

- Lookback: `where updated_at > (select max(updated_at) - interval 3 day from {{ this }})`, cộng
  `unique_key` để không trùng.
- Định kỳ chạy `dbt build --full-refresh -s fct_orders` (vd. mỗi tuần) để dựng lại toàn bộ.
- Dùng cột "thời điểm nạp" (`_loaded_at` do bước EL ghi) thay vì `updated_at` nghiệp vụ.

## Snapshot (SCD Type 2)

- `strategy='timestamp'`: bản ghi được coi là đổi khi `updated_at` thay đổi. Rẻ và chính xác nếu
  nguồn có `updated_at` đáng tin.
- `strategy='check'` + `check_cols`: so sánh giá trị các cột; dùng khi nguồn không có `updated_at`,
  nhưng tốn hơn và không bắt được thay đổi xảy ra rồi quay lại giữa hai lượt chạy.
- Snapshot nên đọc thẳng từ **source** (dữ liệu thô), không qua nhiều model, để logic thay đổi
  không làm "lịch sử giả".
- Kết quả cho `c1`: bản `sao paulo` có `dbt_valid_to = 2018-01-02`, bản `campinas` có
  `dbt_valid_to = null` (hiện hành). Join fact với dimension theo thời điểm:
  `on f.customer_id = s.customer_id and f.purchased_at >= s.dbt_valid_from and (f.purchased_at < s.dbt_valid_to or s.dbt_valid_to is null)`.

Lưu ý: dbt ≥ 1.9 cho phép khai báo snapshot bằng YAML (`snapshots:` trong tệp `.yml`); khối
`{% snapshot %}` trong `.sql` vẫn chạy được và vẫn gặp nhiều trong dự án thật.
