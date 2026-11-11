# Ghi chép của bạn trong sự cố ở công ty luật (thứ Hai 2026-11-09)

Tình huống hư cấu, dựng theo hành vi của quillo 1.0.0 (kiểm token OIDC với độ lệch đồng hồ cho phép 60 s) và Keycloak
(access token sống 5 phút). Giờ là giờ Việt Nam (UTC+7) trừ khi ghi khác. Đây là ghi chép thô, có cả thứ **không được**
đưa vào báo cáo gửi khách.

## Chat với IT công ty luật (rút gọn)

- 07:42 — chị Nguyễn Thị Hạnh (pháp chế, hanh.nt@luat-abc.vn) nhắn nhóm IT: "bấm đăng nhập quillo thì quay lại trang
  login, không báo gì".
- 07:55 — thêm 6 người báo giống vậy. IT thử đăng nhập Keycloak vào hệ thống khác (email nội bộ): được.
- 08:05 — IT mở ticket cho bạn, mức "cao". Kèm support bundle.
- 08:20 — gọi video với anh Phạm Văn Tuấn (IT). Anh Tuấn: "cuối tuần em có chuyển con VM quillo sang host mới cho đợt vá
  hypervisor, chắc không liên quan". Anh dán nhầm vào chat dòng `QUILLO_ADMIN_TOKEN=7f3a…` (đã nhắc anh xoá tin nhắn và
  đổi token sau sự cố).
- 08:31 — nhờ anh Tuấn gõ `date -u` trên máy quillo: `Mon Nov  9 01:40:12 UTC 2026`; điện thoại của bạn lúc đó
  01:31 UTC. Máy quillo nhanh ~9 phút.
- 08:34 — `chronyc tracking`: `Reference ID : 00000000 ()`, `Leap status : Not synchronised`. `chronyc sources`: một
  nguồn `10.20.0.11`, trạng thái `?` (không tới được).
- 08:40 — log api trong bundle: từ 07:31 có các dòng
  `{"level": "INFO", "logger": "quillo.auth", "msg": "token OIDC bị từ chối", "reason": "Signature has expired"}`, trước
  07:31 không có dòng nào như vậy kể từ thứ Sáu. Đăng nhập bằng token quản trị vẫn được (không qua OIDC).
- 08:47 — anh Tuấn: NTP `10.20.0.11` đã tắt từ tháng trước khi đổi sang cụm NTP mới `10.20.0.21`, `10.20.0.22`; host
  cũ có giờ đúng nên máy quillo không lệch dù chrony không đồng bộ được. Host mới nhanh 9 phút.
- 08:58 — bạn đề xuất: IT sửa nguồn NTP của máy quillo sang cụm mới rồi cho chrony chỉnh ngay; bạn không đề xuất đổi gì
  trong quillo. Anh Tuấn nói cần anh Minh (trưởng IT) duyệt vì là máy production.
- 09:05 — anh Minh duyệt. 09:07 IT sửa `/etc/chrony/chrony.conf`, chạy `chronyc makestep`.
- 09:10 — `chronyc tracking`: `Leap status : Normal`, lệch < 1 ms. 09:12 chị Hạnh đăng nhập được. 09:20 IT xác nhận 12
  người thử đều được.
- 09:25 — IT hỏi có mất tài liệu không. Bạn kiểm: worker vẫn nạp tài liệu bình thường suốt buổi sáng (không dùng
  OIDC), 23 tài liệu vào `done/` từ 07:00 tới 09:25, không tệp nào trong `failed/`.

## Số liệu khác

- Log Keycloak (IT gửi): 37 người dùng khác nhau đăng nhập thành công **vào Keycloak** cho client `quillo` từ 07:30 tới
  09:12, nhưng không ai vào được quillo.
- VM được chuyển host lúc khoảng 23:00 Chủ nhật 08/11 (IT không chắc giờ chính xác). Sáng thứ Hai 07:30 là lúc nhân viên
  bắt đầu dùng.
- Bạn nghĩ (chưa kiểm): có thể khi chuyển host, hypervisor đặt lại giờ VM theo giờ host.
- Preflight của bạn lúc cài (tháng 9) có kiểm NTP? Không, chỉ kiểm CPU, RAM, đĩa, Docker.
- Sản phẩm: `/healthz` không kiểm đồng hồ; log quillo không gợi ý lệch giờ khi từ chối token.
