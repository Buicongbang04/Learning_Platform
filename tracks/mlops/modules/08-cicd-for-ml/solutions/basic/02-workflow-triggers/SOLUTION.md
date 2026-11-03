# Lời giải: trigger cho workflow huấn luyện

Xem `ct.yml` cạnh tệp này.

- **Path filter là công cụ tiết kiệm, không phải bảo mật.** Đổi `src/` không đụng tới dữ liệu hay tham số nên không cần
  train lại; CI cho code là việc của một workflow khác. Đổi lại, nếu bộ lọc thiếu một đầu vào của model (ví dụ `train.py`
  hay `dvc.lock`), thay đổi đó đi qua mà không ai train lại: liệt kê đầu vào thật của pipeline, đừng đoán.
- **`schedule` bắt trôi dạt.** Dữ liệu đổi mà không có commit (tháng mới về, nguồn cập nhật) thì không trigger push nào kích
  hoạt; lịch hằng tuần là lưới an toàn. Cron tính theo UTC, chạy trên nhánh mặc định, có thể trễ hàng chục phút, và GitHub tắt
  lịch của repo không có hoạt động trong 60 ngày.
- **`workflow_dispatch` là cửa ra khẩn cấp** và là cách chạy lại có tham số. Bắt `reason` để lần chạy tay nào cũng có dấu vết.
- **`permissions` mặc định rộng.** Khai `contents: read` ở cấp workflow rồi nâng riêng từng job khi thật cần; token bị lộ qua
  một bước xấu cũng chỉ đọc được.
- `act -l` chỉ kiểm workflow *được liệt kê* cho sự kiện đó; bản thân `act` không đánh giá `paths:` (đó là việc của máy chủ
  GitHub), nên bài Intermediate 01 mô phỏng bộ lọc trong test.
