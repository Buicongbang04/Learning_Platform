# Lời giải: Dựng lineage graph từ danh sách câu SQL

## Cách làm

1. **Làm sạch trước khi tìm.** Xoá comment block và comment dòng, thay chuỗi `'...'` bằng `''` (nên
   `read_parquet('s3://...')` không còn đường dẫn), xoá `EXTRACT(... FROM ...)`, `TRIM`, `SUBSTRING` vốn
   có từ khoá `FROM` nhưng không phải bảng.
2. **Target**: một regex neo ở đầu câu cho `CREATE ... TABLE|VIEW ...` và `INSERT INTO`. Không khớp thì
   câu không ghi gì (`SELECT` thuần) và trả `None`.
3. **Sources**: mọi tên sau `FROM`/`JOIN` trong phần còn lại của câu. `\b(?!\s*\()` loại hàm bảng
   (`read_parquet(`); `(` của subquery không khớp `[\w."]` nên tự bị bỏ. Từ đó trừ đi tên CTE và chính
   target (`INSERT INTO t SELECT ... FROM t` không phải cạnh lineage có ích, và tạo self-loop phá topo sort).
4. **Graph** lưu dạng `target -> sources` (hướng ngược), nên `upstream` là DFS thẳng; `downstream` cần đảo
   cạnh thành `source -> targets` trước.
5. **`run_order`**: Kahn chỉ trên các target; nguồn không phải target là dữ liệu raw có sẵn. Dùng `heapq`
   để chọn tên nhỏ nhất khi nhiều bảng cùng sẵn sàng, kết quả deterministic. Còn target chưa được xếp
   nghĩa là có vòng.

## Giới hạn của regex và cách làm production

- Không xử lý `SELECT *` ở mức cột, alias phức tạp, `;` trong chuỗi, dialect đặc biệt (`MERGE`, `COPY`,
  `UNNEST`). Production dùng parser thật: **sqlglot** (`sqlglot.lineage` cho column-level), hoặc lấy lineage
  từ dbt `manifest.json`, OpenLineage integration của Airflow/Spark, hay query history của warehouse.
- Impact analysis: `downstream(graph, "raw.customers")` chính là danh sách bảng có thể chứa PII cần được tag
  và cần xử lý khi có yêu cầu xoá dữ liệu.
