# Lời giải: client cho feature server

`client.py` cạnh tệp này.

- **Đọc theo tên cột.** Server trả cột khoá thực thể cùng các feature; thứ tự không phải hợp đồng. Mã dựa vào `results[1]` sẽ vỡ
  âm thầm khi thêm feature vào `FeatureService`.
- **Thiếu có hai biểu hiện.** Feast 0.67 có thể báo `PRESENT` cho giá trị `null` của thực thể chưa từng được materialize, nên
  kiểm `value is None` song song với `status != "PRESENT"` (`NOT_FOUND`, `OUTSIDE_MAX_AGE` khi quá TTL, `NULL_VALUE`).
- **Default tường minh và có sổ.** `defaulted` cho phép dịch vụ ghi metric "tỉ lệ yêu cầu dùng default"; tỉ lệ này tăng đột ngột
  là dấu hiệu materialize chết hay TTL hết, nhiều khi sớm hơn mọi chỉ số chất lượng model.
- **Loại trùng giữ thứ tự** giảm kích thước yêu cầu mà không làm đổi thứ tự trả lời; `int()` chặn việc gửi `"3"` và `3` thành hai thực thể.
- **Client chỉ dùng thư viện chuẩn** để chạy cùng một mã ở host (unit test) và trong container (tích hợp) mà không kéo Feast
  vào môi trường dịch vụ; trong sản xuất, SDK `feast` cũng gọi cùng REST này.

Lỗi hay gặp: `KeyError` vì dùng `defaults` mà bỏ sót feature; giả định mỗi hàng của cột ứng với thứ tự gửi; để `defaults` ngầm
là `0` làm feature "đứng yên" che mất sự cố materialize.
