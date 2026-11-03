# ShipFast: dự đoán thời gian giao hàng (ETA)

Công ty giao hàng nội thành, 4 lập trình viên backend, 2 Data Scientist, 0 người chuyên hạ tầng.
Model ETA hiển thị cho khách ở màn hình theo dõi đơn và cho điều phối viên khi gán đơn cho tài xế.
Khoảng 12 000 request ETA mỗi ngày, cao điểm 8 request/giây vào 11:30-13:00 và 18:00-20:00.

## Hiện trạng (lời kể của các đội)

- **Dữ liệu.** DS xuất bảng `orders` từ Postgres replica thành CSV (khoảng 2,1 GB) chia sẻ qua Google
  Drive. Tên tệp kiểu `orders_final_v3_NEW.csv`. Hai DS đôi khi dùng hai bản khác nhau.
- **Training.** Một notebook, chạy tay trên laptop của chị Mai khoảng mỗi tháng một lần. Không đặt seed.
  Kết quả (MAE phút) chị ghi vào một Google Sheet. Lần train gần nhất cách đây 7 tuần.
- **Phát hành.** Chị Mai lưu `model.pkl` rồi gửi qua Slack; anh Tuấn (backend) tải về và copy vào VM
  chạy Flask bằng `scp`, khởi động lại tiến trình thủ công. Không ai giữ bản pickle cũ có tổ chức.
- **Môi trường.** VM chạy `pip install -r requirements.txt` không ghim phiên bản. Tháng trước
  scikit-learn nâng bản và model không load được trong 40 phút.
- **Kiểm thử.** Không có test nào cho code ML. Backend có CI chạy unit test cho phần API, không chạm model.
- **Monitoring.** Chỉ có health check HTTP 200 của load balancer. Không log dự đoán. Bảng `orders`
  có thời gian giao thực tế nhưng chưa bao giờ được nối với dự đoán.
- **Sự cố gần đây.** Sau đợt khuyến mãi tháng 9, điều phối viên báo ETA "sai khoảng 40%". Mất 3 ngày mới
  xác nhận được, rồi 2 ngày để quay về model cũ vì không tìm thấy pickle cũ; phải train lại.
- **Bảo mật.** Chuỗi kết nối Postgres nằm cứng trong notebook; notebook nằm trong repo Git riêng của DS.
- **Chi phí và nhân lực.** Ngân sách hạ tầng thêm tối đa khoảng 300 USD/tháng. Không ai làm MLOps toàn thời gian.
