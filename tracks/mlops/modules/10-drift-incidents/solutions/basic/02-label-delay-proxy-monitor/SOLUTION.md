# Lời giải: proxy khi nhãn về muộn

- **Nhãn đã về** là điều kiện về thời gian: `ts + delay <= now`. Mô phỏng sai chỗ này (dùng nhãn chưa về) là lỗi rò rỉ phổ biến nhất khi dựng lại dashboard từ dữ liệu lịch sử:
  MAE nhìn đẹp hơn thực tế vì được "tương lai" giúp. `None` thay cho `0` hoặc NaN buộc người gọi xử lý trường hợp chưa có nhãn.
- **Baseline cùng thứ.** Chu kỳ tuần làm cho "bình thường" của Chủ nhật khác của thứ Hai; so với hôm qua thì mọi thứ Hai và mọi thứ Bảy đều báo động giả. Bốn tuần gần nhất đủ ngắn để theo
  kịp xu hướng, đủ dài để có độ lệch chuẩn; `ddof=1` vì đây là mẫu nhỏ. Đánh đổi: tuần lễ (Tết, Black Friday) không có tiền lệ nên baseline này vẫn báo; khi đó cần lịch sự kiện hoặc cùng kỳ năm trước.
- **Hai proxy bổ sung nhau.** Phân phối dự đoán bắt model "đổi hành vi" (do dữ liệu hay do phiên bản mới); tỉ lệ fallback bắt hệ thống đang lui về nhánh dự phòng (thiếu feature, timeout) mà
  phân phối dự đoán có thể không lộ. Cả hai đều là *proxy*: không chứng minh chất lượng giảm, chỉ nói "đi xem". Quyết định retrain hay rollback vẫn chờ nhãn (xem bài quyết định).
- **Ngưỡng.** `z_limit=3` và `fallback_limit=0.02` là điểm bắt đầu; chỉnh bằng cách đếm số báo động giả trên 8 tuần dữ liệu bình thường rồi đặt ngân sách (vd. tối đa 1 báo động giả mỗi tuần).
