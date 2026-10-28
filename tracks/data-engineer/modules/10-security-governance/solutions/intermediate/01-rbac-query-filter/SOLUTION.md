# Lời giải: RBAC, column masking và row-level security

## Cách làm

1. **Deny by default**: `_policy` tra `POLICIES[role][table]`; thiếu ở bất kỳ tầng nào thì `PermissionError`.
   Không có nhánh "nếu không tìm thấy policy thì cho qua".
2. **Whitelist cột**: danh sách cột được phép tính từ `TABLE_COLUMNS` (giữ thứ tự bảng). Mọi identifier
   đưa vào SQL đều đến từ danh sách này, nên chuỗi `price; DROP TABLE ...` bị chặn ngay ở bước kiểm quyền.
   Identifier không thể truyền bằng tham số `?`, vì vậy whitelist là cách đúng để chống injection ở phần này.
3. **Column masking**: cột trong `masked` render `md5("col") AS "col"`. Hash deterministic nên analyst vẫn
   đếm khách unique, join theo email. (Production nên dùng HMAC với key bí mật hoặc masking policy của
   warehouse, vì md5 email có thể bị dò bằng từ điển.)
4. **Row-level security**: row filter của policy được thêm **luôn luôn** và lấy giá trị từ thuộc tính của
   user đã xác thực, không lấy từ input. `where` của người dùng chỉ được AND thêm vào nên không thể nới rộng
   phạm vi (`seller_id = 's_c'` của seller A cho kết quả rỗng).
5. **Chặn lọc theo cột bị che**: nếu cho `WHERE customer_email = 'ana@gmail.com'`, analyst dò được email
   có tồn tại hay không dù kết quả bị hash. Đây là kiểu rò rỉ qua suy luận (inference attack).
6. **Giá trị qua params**: `' OR 1=1 --` chỉ là một chuỗi so sánh, không đổi cấu trúc câu SQL.

## Trong thực tế

| Lớp ở bài này | Tương đương trong warehouse |
| --- | --- |
| `POLICIES` + `allowed_columns` | `GRANT SELECT (cols)`, role hierarchy |
| `masked` | Snowflake masking policy, BigQuery policy tags, Unity Catalog column mask |
| `row_filter` | Postgres RLS `CREATE POLICY`, Snowflake row access policy, BigQuery row-level security |

Đặt policy ở chính warehouse tốt hơn ở tầng ứng dụng, vì mọi client (BI, notebook, reverse ETL) đều bị áp
dụng như nhau. Lớp ứng dụng như bài này hợp với API phục vụ dữ liệu ra ngoài.
