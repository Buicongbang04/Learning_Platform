# M02: Star schema cho đơn hàng và vận chuyển

## Mục tiêu

Thiết kế và dựng schema `dw` dạng star schema từ schema `raw`, để analyst trả lời nhanh các câu
hỏi doanh thu, giao hàng và review. Áp dụng Slowly Changing Dimension type 2 cho seller.

## Việc cần làm

1. Xác định **grain** của bảng fact chính: một dòng = một item trong một đơn
   (`order_id`, `order_item_id`). Ghi quyết định vào `project/models/dw/DESIGN.md`.
2. Vẽ ERD mermaid trong `DESIGN.md`, tối thiểu:
   - `dw.fact_order_items` (measure: `price`, `freight_value`; FK: `date_key`, `customer_key`,
     `seller_key`, `product_key`; degenerate dimension `order_id`, `order_status`).
   - `dw.fact_deliveries` (grain: một đơn; `estimated_days`, `actual_days`, `is_late`).
   - `dw.dim_date`, `dw.dim_customer`, `dw.dim_product` (kèm tên danh mục tiếng Anh),
     `dw.dim_seller` (SCD2: `valid_from`, `valid_to`, `is_current`).
3. Viết DDL `project/models/dw/01_dw_schema.sql` với surrogate key (`bigint generated always as identity`)
   và index cho các FK hay join.
4. Viết `project/models/dw/02_load_dw.sql` (hoặc script Python) nạp từ `raw` sang `dw`, idempotent
   (`MERGE` của PostgreSQL 15+ hoặc `INSERT ... ON CONFLICT`).
5. SCD2: viết `project/models/dw/03_scd2_seller.sql`. Thử: đổi `seller_city` của 3 seller trong
   `raw.sellers` rồi chạy lại, kiểm tra có dòng lịch sử.
6. Viết 4 truy vấn phân tích trong `project/models/dw/queries.sql` và đo `EXPLAIN ANALYZE` trước/sau
   khi thêm index:
   - Doanh thu theo bang khách hàng theo tháng.
   - Tỉ lệ giao trễ theo seller (top 20, ít nhất 30 đơn).
   - Điểm review trung bình theo danh mục.
   - Giá trị đơn trung bình theo phương thức thanh toán.
7. Chạy:

   ```bash
   docker compose -f setup/docker-compose.yml up -d postgres
   docker compose -f setup/docker-compose.yml exec -T postgres psql -U de -d de < tracks/data-engineer/capstone/project/models/dw/01_dw_schema.sql
   docker compose -f setup/docker-compose.yml exec -T postgres psql -U de -d de < tracks/data-engineer/capstone/project/models/dw/02_load_dw.sql
   docker compose -f setup/docker-compose.yml exec -T postgres psql -U de -d de < tracks/data-engineer/capstone/project/models/dw/queries.sql
   ```

## Kết quả nộp

- `project/models/dw/DESIGN.md` (grain, ERD mermaid, lý do chọn star thay vì snowflake/OBT)
- `01_dw_schema.sql`, `02_load_dw.sql`, `03_scd2_seller.sql`, `queries.sql`
- Bảng so sánh thời gian truy vấn trước/sau index trong `DESIGN.md`.

## Tiêu chí đạt

- [ ] Tổng `price` trong `dw.fact_order_items` bằng tổng `price` trong `raw.order_items`.
- [ ] Không có FK nào trong fact trỏ tới dimension không tồn tại (kiểm bằng `LEFT JOIN ... IS NULL`).
- [ ] `dim_seller` giữ lịch sử: mỗi `seller_id` có đúng một dòng `is_current = true`.
- [ ] Chạy lại script nạp không làm thay đổi số dòng khi dữ liệu nguồn không đổi.
- [ ] Đơn huỷ và đơn thiếu ngày giao được xử lý rõ ràng (không làm sai `is_late`).
- [ ] 4 truy vấn phân tích chạy dưới 1 giây với 50k đơn.
