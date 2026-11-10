# Postmortem: lộ mật khẩu

## 1. Tóm tắt

Bạn Nam push nhầm tệp có mật khẩu Postgres staging lên GitHub. Nam đã bị nhắc nhở. Team đã xoá commit và đổi mật khẩu, mọi thứ ổn lại
sau khoảng hai tiếng. Không có thiệt hại nào được ghi nhận, production vẫn chạy bình thường trong suốt thời gian đó, staging cũng vậy.

## 2. Tác động

Chỉ staging, production không bị. Lộ khoảng 90 phút.

## 3. Timeline

| Giờ | Sự kiện |
| --- | --- |
| 09:40 | Push |
| 11:05 | Thấy email |
| 10:20 | GitHub gửi cảnh báo |
| 11:15 | Đổi mật khẩu |
| 12:10 | Xoá fork |
| 11:40 | Tạo khoá mới |
| 12:30 | Đọc log Postgres |
| 14:00 | Đóng sự cố |

## 4. Nguyên nhân gốc

- Nam giải mã tệp rồi quên xoá.
- Thiếu pre-commit hook.
- Nam không cẩn thận.

## 5. Xử lý và khôi phục

Đầu tiên dùng git filter-repo xoá commit khỏi lịch sử và force push, sau đó mới xoay mật khẩu Postgres, sops updatekeys với recipient
mới, cập nhật Secret cho ArgoCD.

## 6. Phát hiện

GitHub secret scanning gửi cảnh báo sau 40 phút.

## 7. Điều làm tốt và điều chưa tốt

- Đổi mật khẩu nhanh.

## 8. Action items

| Việc | Người phụ trách | Hạn | Loại |
| --- | --- | --- | --- |
| Cài pre-commit gitleaks | | sớm | phòng ngừa |
| Bật push protection | | sớm | phòng ngừa |
| Xoay khoá định kỳ | | sớm | phòng ngừa |
| Nhắc nhở team | | sớm | khác |
| Viết tài liệu | | sớm | khác |
