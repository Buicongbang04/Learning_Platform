# Lời giải: drift mạnh từ hôm qua

**Nguyên nhân.** Pipeline nguồn của cột `duration_value` đổi đơn vị từ giây sang phút vào ngày cuối cùng; không ai thông báo. Giá trị nhỏ đi đúng 60 lần: trung vị khoảng 600 giây (10 phút) thành khoảng 10, các cột khác
không đổi. PSI của `duration_value` vọt lên (vài đơn vị, so với dưới 0.05 của hai cột còn lại), mọi phân phối khác y nguyên. **Đây là drift giả**: thế giới không đổi, cách đo đổi.
MAE trên nhãn không đổi vì model phục vụ đọc feature qua đường khác với đường log của monitoring; nếu cả hai dùng chung nguồn, model sẽ thực sự bị hỏng và đó là sự cố khác (training-serving skew).

**Cách chẩn đoán.**

1. Tái hiện: `drifted_columns` chỉ ra đúng một cột; ba cột còn lại sạch. Drift thật từ thế giới hiếm khi chỉ chạm một cột và để nguyên các cột liên quan (cự ly, giá cước) trong khi thời lượng nhỏ đi 60 lần.
2. Xác định điểm gãy: `change_point_day` cho đúng ngày; thay đổi đột ngột trong một ngày là dấu hiệu của thay đổi hệ thống chứ không phải hành vi người dùng.
3. Đo độ lớn: `level_by_period` cho hai trung vị, tỉ số giữa chúng là 60.0, một số nguyên "tròn". Tỉ số tròn như vậy gần như luôn là hệ số quy đổi.
4. Xác nhận bằng nguồn: hỏi đội sở hữu pipeline nguồn; ở đây thay đổi nằm ở hàm ghi log (đổi đơn vị), không nằm ở model hay dữ liệu thực.

**Cách sửa.**

- Sửa ngay: `adjust_from` với `transform = lambda s: s * 60` đưa các ngày sau mốc về cùng đơn vị với lịch sử; cảnh báo biến mất, không cần retrain hay rollback.
- Sửa tận gốc ở nguồn: giữ một đơn vị thống nhất và ghi hẳn đơn vị vào schema/contract của bảng log (xem bài data contract ở module 03).
- Thêm rào: `range_guard` ở cửa vào pipeline monitoring với khoảng hợp lý của từng cột lấy từ dữ liệu tham chiếu (ở đây quantile 0.1% và 99.9% của 14 ngày đầu): lô lệch được chặn và gọi đúng người, thay vì biến thành một "drift" làm cả đội mất giờ.
- Thêm kiểm tự động so trung vị theo ngày với 7 ngày trước: hệ số tròn (10, 60, 100, 1000) là gợi ý đổi đơn vị.

**Bài học.** Trước khi tin một cảnh báo drift: (1) loại trừ lỗi dữ liệu và pipeline, (2) xem nó chạm bao nhiêu cột và có hợp lý về mặt nghiệp vụ không, (3) so với chất lượng trên nhãn. Phản xạ "drift nên retrain"
sẽ train model trên dữ liệu đã bị làm sai và đặt lên production một model hỏng thật.
