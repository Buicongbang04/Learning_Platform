# Lời giải: ước tính chi phí ML

Mã trong `cost.py`. Điều bài này muốn bạn thấy:

- **Hoá đơn lệch về phía serve nhàn rỗi.** Trong kịch bản mẫu train GPU cả tháng chỉ 8,48 USD (spot, 24 giờ GPU) còn hai replica CPU treo 730 giờ tốn 335,8 USD, trong đó 285,43 USD là thời gian máy không làm gì. Người mới hay lo giá GPU; hoá đơn thật thường nằm ở thứ chạy mãi.
- **Train trả theo lần, serve trả theo giờ.** Train chấp nhận bị ngắt (spot, giảm 65%) nếu có checkpoint; serve thì không ngắt được tuỳ tiện nên cách giảm là co về 0 hoặc cam kết dài hạn.
- **Hai đòn bẩy cho phần nhàn rỗi, hai đánh đổi.** `scale_to_zero` bỏ gần hết 285 USD nhưng request đầu tiên sau lúc rảnh chịu khởi động nguội (tải model, có thể hàng chục giây) nên chỉ hợp cho tải không yêu cầu độ trễ chặt. `committed` giảm 38% mà vẫn trả cho giờ rảnh và khoá bạn vào một cỡ máy.
- **Làm tròn một lần.** Cộng các số đã làm tròn lệch cent; ngân sách thì không cần cent, nhưng test tiền phải đúng để công thức không lẫn hệ số.
- **Giá trong bài là minh hoạ.** Dùng làm khuôn: số thật lấy từ bảng giá hiện hành, nhớ cộng các khoản bài này bỏ qua (NAT, load balancer, log, cross-AZ), xem phần chi phí ẩn trong README module.

Lỗi hay gặp: nhân `utilization` vào giá trong khi máy vẫn bật (nhầm giữa "máy bận" và "máy tính tiền"); quên `replicas`; áp `spot` cho serve; để `savings` sửa kịch bản gốc làm lần so sánh sau dùng số đã đổi.
