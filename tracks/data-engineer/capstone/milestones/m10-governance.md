# M10: Data quality, lineage, masking PII

## Mục tiêu

Hoàn thiện nền tảng với lớp governance: kiểm tra chất lượng dữ liệu tự động chặn dữ liệu xấu,
lineage từ nguồn tới dashboard, bảo vệ PII bằng masking/tokenization và phân quyền theo vai trò.

## Việc cần làm

1. **Phân loại dữ liệu**: lập bảng `project/governance/data_catalog.md` cho mọi cột chứa PII hoặc
   gần PII (`customer_unique_id`, `customer_zip_code_prefix`, `geolocation_lat/lng`,
   `review_comment_message`, tên/email nếu bạn thêm), mức nhạy cảm và cách xử lý.
2. **Data quality** – `project/governance/quality.py` dùng `pandera` (hoặc dbt tests + 
   `dbt-expectations`):
   - Schema check cho silver `orders`, `order_items`, `payments`.
   - Rule nghiệp vụ (đối chiếu với bất thường đã thấy trong notebook khám phá: trên bộ thật, 166 đơn giao hãng
     trước lúc mua, 23 đơn khách nhận trước lúc giao hãng; quyết định mức `error` hay `warn` và ghi lý do):
     `order_delivered_customer_date >= order_purchase_timestamp`;
     `payment_value > 0`; tổng payment của một đơn ≈ tổng `price + freight` (sai số 1%);
     `review_score` trong 1..5; freshness: đơn mới nhất không cũ quá 2 ngày so với `logical_date` (Olist thật
     dừng ở 10/2018: chạy với `--date` trong khoảng có dữ liệu, như lệnh ở bước 6).
   - NYC TLC: theo dõi `reject_counts` của M06; tỉ lệ chuyến bị loại vượt ngưỡng bạn chọn (bộ 2019 khoảng 1,4%) thì cảnh báo.
   - Kết quả ghi vào `ops.dq_results`; vi phạm mức `error` làm task `quality_gate` của DAG fail,
     mức `warn` chỉ ghi log. Bản ghi lỗi đưa vào bảng quarantine thay vì bỏ im lặng.
3. **Masking & tokenization**:
   - Tokenize `customer_unique_id` bằng HMAC-SHA256 với khoá trong biến môi trường
     (deterministic → vẫn join được), lưu ở tầng gold.
   - Mã hoá cột `review_comment_message` gốc bằng `cryptography.fernet` ở bảng hạn chế; view cho
     analyst chỉ thấy bản đã che (`***`) hoặc độ dài.
   - Trong Postgres: role `analyst` chỉ đọc view đã mask; dùng Row-Level Security để role
     `seller_portal` chỉ thấy đơn của seller mình (`SET app.seller_id = ...`).
4. **Lineage**: xuất lineage từ `dbt docs` (manifest.json) và vẽ sơ đồ mermaid end-to-end cho cả hai nguồn
   (CSV Olist → raw → dw → mart → dashboard; Parquet NYC TLC → Spark → gold → dashboard) trong
   `project/governance/lineage.md`. Nâng cao: phát
   OpenLineage event từ Airflow vào Marquez.
5. **Quyền xoá dữ liệu (GDPR/LGPD)**: script `project/governance/forget_customer.py --customer-id X`
   xoá/ẩn danh khách trên mọi tầng (Postgres, Mongo, Redis, lake) và ghi audit log.
6. Chạy:

   ```bash
   uv run python tracks/data-engineer/capstone/project/governance/quality.py --date 2018-08-01
   uv run pytest tracks/data-engineer/capstone/project/tests -q
   ```

## Kết quả nộp

- `project/governance/` (catalog, quality, lineage, forget_customer, SQL RLS/role)
- Test cho rule chất lượng và hàm tokenize trong `project/tests/test_governance.py`
- Mục "Governance" trong README: ma trận role × dữ liệu, ví dụ một lần DQ chặn dữ liệu xấu.

## Tiêu chí đạt

- [ ] Chèn cố ý 10 dòng xấu (ngày giao trước ngày mua, `payment_value` âm): DAG dừng ở `quality_gate`, dòng xấu nằm trong quarantine.
- [ ] Role `analyst` không đọc được cột PII gốc (thử `SELECT` nhận permission denied).
- [ ] Token của cùng một khách giống nhau giữa các lần chạy; đổi khoá thì token đổi.
- [ ] RLS: đăng nhập `seller_portal` với một `seller_id` chỉ thấy đơn của seller đó.
- [ ] `forget_customer.py` xoá sạch dấu vết khách trên mọi kho (có test kiểm tra).
- [ ] Sơ đồ lineage bao phủ cả hai nguồn, mỗi nguồn tới ít nhất một card dashboard.
- [ ] Quality gate chạy trên Olist thật: bất thường thật (mốc thời gian vô lý, đơn `delivered` thiếu ngày giao) được
  ghi vào `ops.dq_results`/quarantine đúng mức đã chọn, không làm DAG fail oan.
- [ ] Đủ 5 phần của bài nộp cuối (capstone README, mục Bài nộp cuối): pipeline chạy được, dữ liệu sạch, insight,
  dashboard trên trình duyệt, README portfolio có mục Governance (ma trận role × dữ liệu).
