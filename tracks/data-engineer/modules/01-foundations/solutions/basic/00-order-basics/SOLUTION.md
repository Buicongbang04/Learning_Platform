# Lời giải: đơn hàng nhập môn

Đổi chuỗi thành Decimal trước khi tính, tránh sai số float. NaN/Infinity parse được nhưng không phải
giá tiền hợp lệ nên cần is_finite(). Không bắt mọi Exception: lỗi lập trình cần hiện ra để sửa.

Duyệt theo số dòng bắt đầu 1, kiểm dữ liệu rồi mới đánh dấu ID đã thấy. Vì vậy dòng sai có ID o1
không ngăn dòng o1 hợp lệ tới sau. Giữ nguyên input giúp gọi lại và kiểm tra dễ hơn.

LEFT JOIN giữ khách chưa có đơn. Với khách đó, COUNT(o.order_id) là 0, còn COUNT(*) là 1.
COALESCE đổi tổng NULL thành 0; amount_cents được giữ là số nguyên, không đổi đơn vị giữa truy vấn.
