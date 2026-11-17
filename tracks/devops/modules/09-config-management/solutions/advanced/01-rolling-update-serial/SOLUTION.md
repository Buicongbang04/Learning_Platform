# Lời giải: rolling update từng máy, health check và rollback

Lời giải là `rollout.yml`.

## Các quyết định

- **`serial: 1`, `max_fail_percentage: 0`, `order: inventory`.** Mỗi đợt một máy theo thứ tự cố định; một máy lỗi là dừng cả play,
  máy sau không bị đụng. `max_fail_percentage` tính trong từng đợt; với `serial: 1`, 0% nghĩa là dừng ở máy lỗi đầu tiên.
  `any_errors_fatal: true` cũng dừng được, nhưng nó còn cắt ngang các máy **cùng đợt** đang chạy, hợp khi đợt lớn.
- **Kiểm tham số trước khi đụng máy.** `assert` trong `pre_tasks` với `match('^\d+\.\d+\.\d+$')`: thiếu `-e` hay gõ nhầm `1.5` dừng
  ngay ở máy đầu, trước khi rút nó khỏi load balancer.
- **Đọc bản cũ trước khi đổi.** `stat` cho `lnk_source`, ghi bằng `set_fact`: rescue biết trỏ về đâu, kể cả khi bản cũ không phải
  bản "trước đó" trong danh sách release.
- **Khối deploy có `when` so bản cũ và bản đích.** Máy đã ở bản đích không bị rút khỏi LB hay đổi gì: chạy lại sau sự cố chỉ làm phần
  còn thiếu, và lần chạy trên mọi máy đã xong là `changed=0`. Đây là idempotency ở mức quy trình, không chỉ ở mức task.
- **Health check có `until`/`retries`/`delay`, `changed_when: false`.** Ứng dụng thật cần vài giây để lên; một lần thử dễ báo lỗi giả.
  Task chỉ đọc không được làm bẩn recap.
- **`block`/`rescue` kết thúc bằng `fail`.** Máy được rescue thành công không bị tính là lỗi, rollout sẽ đi tiếp sang máy sau với
  cùng bản lỗi. `fail` cuối rescue biến nó thành lỗi để `max_fail_percentage` dừng play. Cờ maintenance được giữ: máy vừa rollback
  không nên nhận traffic tới khi có người xem.

## Ở production

- Cờ maintenance thay bằng thao tác thật: tắt server trong upstream Nginx (module 05) qua API hay template rồi reload, hay
  `amazon.aws.elb_target` để deregister khỏi target group, chạy với `delegate_to: <máy LB>` hay `delegate_to: localhost` (gọi API
  cloud từ máy điều khiển). Lab cấm `delegate_to` vì không có máy LB và để không task nào chạy trên máy bạn.
- Thêm `wait_for` cho connection draining (chờ request đang xử lý xong) trước khi đổi.
- Đợt đầu một máy (canary), sau đó tăng dần: `serial: [1, "25%", "100%"]`.
- Giữ N bản release gần nhất trên máy để rollback không cần tải lại; dọn bản cũ bằng một task riêng.
