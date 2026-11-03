# Lời giải: thiết kế CI, CT, CD cho ETA

Bài Advanced không có đáp án duy nhất. `DESIGN.md` cạnh tệp này là một bản mẫu đã chạy qua test; chấm theo lập luận.

## Các quyết định cốt lõi

- **Tách theo thứ thay đổi, không theo công cụ.** Code (CI) rẻ và chặn merge; dữ liệu và tham số (CT) đắt hơn nên có mẫu nhỏ
  trên PR và bản đầy đủ theo lịch. Đổi alias là CD, có người duyệt. Gộp thành một workflow lớn làm mọi PR trả giá GPU.
- **Chỗ nối là phần dễ chết nhất.** Mỗi lớp xanh riêng không chứng minh gì về thứ được giao qua lại. Bản mẫu dùng `digest` và
  `git sha` làm định danh, kiểm ở cả hai đầu, và đối chiếu `model_id` sau deploy. Một bản "deploy cái mới nhất" thiếu vế kiểm.
- **Alias là trigger của deploy.** Đổi model không cần commit; nhưng nó cần dấu vết và duyệt, nên hook gửi phiên bản cụ thể và
  môi trường `production` có reviewer.
- **Trung thực về runner tự host.** Nó giải bài toán GPU và dữ liệu nội bộ nhưng mở ra bề mặt tấn công; nêu cách giới hạn.
- **Chi phí là ràng buộc thiết kế.** Có số (phút, chi phí runner), có chỗ huỷ (`concurrency`) và chỗ không bao giờ huỷ.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Tách workflow theo thứ thay đổi | 20 | Trigger khớp thứ thay đổi; không train đầy đủ trên mọi PR; có lịch cho dữ liệu đổi không kèm commit |
| Chỗ nối hai lớp | 25 | Định danh cụ thể được kiểm ở cả hai đầu; nêu cách xử lý hai lần chạy chồng nhau |
| Cổng và người duyệt | 15 | Cái gì tự động, cái gì cần người; rollback bằng đổi alias; ngoại lệ có hạn |
| Secrets, quyền, OIDC | 15 | Không khoá dài hạn; quyền tối thiểu; fork không có secrets; nêu rủi ro runner tự host |
| Chi phí và vận hành | 15 | Cache, huỷ chạy cũ, timeout, giám sát chính pipeline (lịch không chạy, runner chết) |
| Rõ ràng | 10 | Sơ đồ khớp bảng; mỗi phần ngắn; đọc được bởi người chưa biết repo |
