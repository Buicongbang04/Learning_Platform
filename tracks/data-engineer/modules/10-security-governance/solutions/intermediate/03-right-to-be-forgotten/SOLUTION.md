# Lời giải: Right to be forgotten trên DuckDB

## Cách làm

1. **Idempotency theo `request_id`**: kiểm tra `erasure_log` trước tiên. Request đã xử lý thì trả lại kết
   quả cũ, không chạy lại. Job có thể được retry (Airflow, hàng đợi) mà không ghi log trùng hay sinh lại
   pseudonym mới cho đơn hàng.
2. **Lấy `customer_id` trước khi xoá**: `customers` là cầu nối duy nhất từ `customer_unique_id` sang
   `orders`. Thứ tự thao tác: reviews → orders → customers → user_keys.
3. **Giữ dữ liệu tổng hợp**: không xoá `orders` (mất doanh thu lịch sử, sai báo cáo tài chính). Thay
   `customer_id` bằng `anon_<uuid4>` **ngẫu nhiên**: không ai, kể cả người có key, nối ngược được. Mỗi
   `customer_id` cũ một pseudonym để số khách/đơn ở quá khứ không bị gộp sai.
4. **Free text**: `review_comment_message` có thể chứa số điện thoại, tên. Không thể biết chắc nên xoá nội
   dung, giữ `review_score` (không định danh).
5. **Crypto-shredding**: xoá DEK trong `user_keys`. Payload trong `pii_vault` (đại diện cho backup, snapshot,
   file Parquet bất biến) vẫn còn nhưng thành rác. Đây là cách thực tế để "xoá" khỏi backup.
6. **Transaction**: `begin/commit/rollback`; lỗi giữa chừng (ở test: bảng `reviews` biến mất) không để lại
   trạng thái nửa vời, và log không ghi request "đã xong".
7. **Audit log không có PII**: chỉ ghi `subject_hash = HMAC(key, customer_unique_id)`. Khi cần chứng minh
   đã xử lý cho một người, tính lại HMAC từ id họ cung cấp và tra log.

## Ngoài phạm vi bài, cần có ở production

- Xác minh danh tính người yêu cầu và kiểm tra căn cứ giữ lại (hoá đơn thuế, chống gian lận).
- Dùng catalog + lineage để biết **mọi** bảng chứa người này (bản copy ở mart, feature store, export CSV,
  CRM qua reverse ETL, log ứng dụng).
- Data lake: table format hỗ trợ `DELETE` (Delta/Iceberg) rồi `VACUUM`/expire snapshot; nếu không thì
  crypto-shredding.
- SLA (GDPR: một tháng) và báo cáo định kỳ số request đã xử lý.
