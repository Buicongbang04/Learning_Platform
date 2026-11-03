# Lời giải: shadow mode

## Cách làm

`predict` chạy primary trên `rows` gốc, sao sâu `rows` (trước khi primary có thể sửa) giao cho một `ThreadPoolExecutor` chạy `run_shadow`, rồi trả ngay dict của primary. `run_shadow` bọc cả lời gọi shadow và lời gọi `log` bằng `try/except` riêng và dựng bản ghi gồm cả trường hợp lỗi.

Điểm dễ sai:

- **Sao chép**: shadow chạy sau khi hàm trả về, nên nếu dùng chung `rows` hay dict kết quả, shadow có thể sửa thứ người gọi đang dùng. Sao sâu cả `rows` lẫn bản ghi kết quả của primary.
- **Đơn vị của lỗi**: lỗi primary là lỗi thật, ném tiếp và không tạo bản ghi shadow; lỗi shadow là dữ liệu (một dòng log).
- **Log hỏng** không được kéo request xuống: log là phần quan sát, không phải phần phục vụ.
- **Hàng đợi**: pool có 4 thread; nếu shadow chậm hơn nhịp đến, hàng đợi dài ra mãi và ăn bộ nhớ. Hệ thống thật cần giới hạn hàng đợi và bỏ bớt mẫu (sampling hoặc `drop` khi đầy), và đo tỉ lệ bị bỏ.

## Khi nào shadow không đủ

Shadow cho biết model mới chạy được và dự đoán lệch bao nhiêu trên traffic thật. Nó không cho biết người dùng phản ứng ra sao với dự đoán mới (cần canary hoặc A/B), và nó tốn gấp đôi tài nguyên dự đoán.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Response nguyên vẹn | Bằng đúng dict của primary |
| Cô lập | Shadow chậm, lỗi, sửa đầu vào, log hỏng đều không ảnh hưởng request |
| Bản ghi đủ | Có version hai bên, độ lệch lớn nhất, lỗi dạng chuỗi |
