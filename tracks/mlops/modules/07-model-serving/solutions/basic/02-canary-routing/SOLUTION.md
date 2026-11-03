# Lời giải: định tuyến canary và A/B bằng hash ổn định

## Cách làm

`bucket` = SHA-256 của `salt:id`, 8 byte đầu chia cho `2**64`, ra số đồng đều trong [0, 1). `route` so với trọng số. `assign_variant` duyệt các nhánh theo thứ tự tên và cộng dồn trọng số.

## Vì sao đúng

- **Cùng id, cùng nhánh** ở mọi tiến trình: SHA-256 không phụ thuộc trạng thái. `hash()` của Python bị salt theo tiến trình (`PYTHONHASHSEED`), nên hai replica sẽ định tuyến cùng một id khác nhau.
- **Đơn điệu**: canary là `bucket < w`, nên nâng `w` chỉ thêm id vào canary. Nếu dùng dãy số ngẫu nhiên có trạng thái hay modulo trên số khác nhau, người dùng sẽ nhảy qua lại khi bạn đổi trọng số.
- **Salt** làm hai thí nghiệm độc lập: không có salt, người trong 10% đầu của thí nghiệm này cũng nằm trong 10% đầu của mọi thí nghiệm khác, và hiệu ứng của chúng lẫn vào nhau.
- **Thứ tự nhánh cố định** làm kết quả không phụ thuộc cách viết dict.

## Đánh đổi

Băm theo `request_id` cho canary vận hành; băm theo `user_id` khi cần nhất quán trải nghiệm hoặc phân tích A/B theo người dùng. Băm theo `user_id` làm người dùng nặng nằm gọn trong một nhánh nên tải không đúng bằng trọng số; kiểm tải thật, không chỉ số id. Trọng số nhỏ cần nhiều id mới thấy tỉ lệ đúng: 1% của 2000 request chỉ có 20 canary, quá ít để kết luận chất lượng.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Ổn định liên tiến trình | Không dùng `hash()`, `random` |
| Tỉ lệ đúng | ±3% trên 2000 request |
| Đơn điệu và độc lập | Tăng trọng số không đảo nhánh; salt khác thì độc lập |
