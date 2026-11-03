# Lời giải: feature repo zone_speed

`features.py` cạnh tệp này.

- **Entity là khoá nối, FeatureView là bảng có thời gian.** `join_keys=["zone_id"]` phải trùng tên cột trong nguồn và trong
  `entity_rows` khi đọc. Feast 0.67 cảnh báo `value_type` của entity sẽ bắt buộc ở bản sau; đặt nó khi nâng phiên bản.
- **`timestamp_field` quyết định point-in-time.** `get_historical_features` chỉ lấy dòng có `event_timestamp` không muộn hơn
  thời điểm hỏi (và trong `ttl`); `materialize` chỉ chép dòng mới nhất của mỗi thực thể.
- **`ttl` hai vai trò.** Offline: giá trị cũ hơn `ttl` so với thời điểm hỏi bị bỏ. Online: lần `materialize-incremental`
  đầu lấy từ `now - ttl`; ttl quá ngắn so với tuổi dữ liệu thì online rỗng. Đặt `ttl` theo chu kỳ cập nhật (thường vài lần).
- **Online bằng offline chỉ sau materialize.** Online store không tự đọc nguồn; đó là lý do cần job materialize có
  lịch và cảnh báo khi trễ.
- **Online thiếu thực thể trả `None`, không phải lỗi.** Bên gọi phải có default (bài 03 của module này).
- **Feast chạy trong container vì `feast[redis]` kéo `pandas` xuống 2.3.3.** Mã của bạn ở repo chỉ khai báo; tính toán feature
  vẫn là pandas ở host (bài 01 và 02 của module).

Lỗi hay gặp: nguồn không có cột timestamp đúng tên; `ttl` mặc định rất ngắn khiến dữ liệu mẫu cũ không materialize; quên rằng
Redis dùng chung giữa các project nên cần tên project riêng và `teardown` khi xong.
