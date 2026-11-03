# Lời giải: rollback bằng alias và reload

## Cách làm

State là **một tuple** `(version, model)`. `/predict` đọc tuple một lần rồi dùng cả hai phần; `reload` nạp model mới vào biến cục bộ, chỉ khi thành công mới gán tuple mới. Như vậy:

- không có khoảnh khắc nào version và model lệch nhau (response không lẫn "version 1, dự đoán của version 2");
- model đang phục vụ không bị đụng cho tới lúc có thay thế sẵn sàng; nạp lỗi thì 409 và giữ nguyên.

Một `Lock` chỉ để hai lần reload đồng thời không nạp hai lần; `/predict` không lấy khoá nên không chờ reload. Nếu alias trỏ vào cùng version, trả `changed=false` và không nạp lại: reload lặp lại phải rẻ và vô hại (idempotent), vì hệ thống tự động có thể gọi nó mỗi phút.

## Quy trình rollback

1. Tìm version tốt gần nhất (registry, lịch sử alias).
2. `client.set_registered_model_alias("taxi-eta", "champion", "<version cũ>")`.
3. `curl -X POST -H "X-Admin-Token: ..." <service>/admin/reload` tới từng replica (hoặc qua một job lặp qua endpoints).
4. Kiểm `model_version` trong response và log; nếu có nhiều replica, kiểm tất cả đã đổi.

## Đánh đổi và lỗi hay gặp

- **Nhiều replica**: reload là thao tác trên từng tiến trình; không gọi tới hết thì một phần traffic vẫn ở bản xấu. Phương án khác: service tra alias định kỳ (poll) và tự reload, đổi lấy việc đổi model không có điểm dừng rõ ràng.
- **Token** chỉ là một lớp; đặt endpoint sau mạng nội bộ hoặc mTLS, không công khai qua ingress.
- Không tra alias mỗi request: mỗi request thêm một lần gọi registry và làm kết quả phụ thuộc vào độ sẵn sàng của nó.
- Kiểm toán: alias nằm ngoài image nên phải giữ lịch sử đổi alias.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Rollback không restart | Đổi alias, reload, `model_version` đổi |
| An toàn khi lỗi | 409, giữ model cũ, vẫn phục vụ |
| Nhất quán dưới tải | Không lỗi, không lẫn version trong lúc reload |
