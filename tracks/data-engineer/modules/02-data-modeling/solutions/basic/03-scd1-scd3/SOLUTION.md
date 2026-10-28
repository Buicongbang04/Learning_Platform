# Lời giải: SCD type 1 và type 3

## Ý tưởng chung

Đưa snapshot vào bảng staging rồi xử lý bằng SQL theo tập (set-based). Cách này nhanh hơn nhiều so
với lặp từng dòng trong Python, và giống hệt cách bạn sẽ làm trong warehouse/dbt.

## Type 1

`INSERT ... ON CONFLICT (seller_id) DO UPDATE` (upsert) gộp hai trường hợp "mới" và "đã có" trong
một câu. `excluded` là dòng định chèn. Idempotent tự nhiên: chạy lại chỉ ghi đè cùng giá trị.
Đánh đổi: mất lịch sử. Báo cáo doanh thu theo bang của seller năm ngoái sẽ "chuyển" sang bang mới.
Dùng khi thay đổi là **sửa lỗi** (city viết sai) hoặc khi không ai cần lịch sử.

## Type 3

- `UPDATE ... FROM stg` chỉ chạm seller có bang khác (`IS DISTINCT FROM` để so sánh đúng cả khi
  có NULL). Trong `SET`, mọi vế phải đọc giá trị **trước** khi update, nên
  `previous_state = d.current_state` lấy bang cũ dù cùng câu gán `current_state` mới.
- `INSERT ... WHERE NOT EXISTS` thêm seller mới.
- Vì điều kiện `IS DISTINCT FROM`, chạy lại cùng snapshot không có dòng nào thoả → idempotent,
  `state_changed_on` không bị đẩy sang ngày mới.
- Hai câu được bọc trong một transaction để không bao giờ có trạng thái nửa vời.

Đánh đổi của type 3: chỉ nhớ **một** bước. Seller đổi SP → PR → RJ thì mất SP. Phù hợp khi doanh
nghiệp cần so sánh "cơ cấu cũ vs mới" sau một lần tái tổ chức. Cần lịch sử đầy đủ thì dùng type 2
(bài intermediate tiếp theo).
