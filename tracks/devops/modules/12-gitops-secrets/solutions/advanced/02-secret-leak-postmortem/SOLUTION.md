# Lời giải: postmortem lộ mật khẩu Postgres và khoá age

`POSTMORTEM.md` cạnh tệp này là **một** lời giải qua test; rubric dưới đây mới là thứ chấm nội dung.

## Hướng làm

**Con số.** Cửa sổ lộ tính tới khi secret hết dùng được: mật khẩu Postgres 09:41 tới 11:15 (94 phút), khoá age 09:41 tới 11:52 (131 phút).
Phát hiện có hai mốc: công cụ biết lúc 10:20 (39 phút), con người biết lúc 11:05 (84 phút). Thời gian từ khi biết tới khi chặn xong mật
khẩu: 10 phút.

**Nguyên nhân.** Không phải "kỹ sư bất cẩn". Các điều kiện hệ thống cùng xảy ra: quy trình gỡ lỗi cần bản giải mã và cách dễ nhất là ghi
ra tệp trong repo; README của dự án đặt khoá riêng trong repo; `.gitignore` thiếu; repo GitOps không có pre-commit hook; fork công khai nằm
ngoài push protection; cảnh báo chỉ tới một người; không có mẫu phát hiện cho `AGE-SECRET-KEY-`.

**Thứ tự xử lý.** Coi như đã lộ từ lúc push (bot clone sau 6 phút). Xoay mật khẩu trước vì dùng được ngay; rồi thu hồi khoá age (thêm
recipient mới, `sops updatekeys`, thay khoá trong ArgoCD, gỡ recipient cũ); rồi mới dọn dấu vết. Xoá fork hay `git filter-repo` không thu
hồi được bản đã bị chép, chỉ giảm người thấy về sau. Mọi secret từng mã hoá bằng khoá age cũ (không chỉ mật khẩu DB) đều phải coi là lộ:
liệt kê các tệp `*.enc.yaml` của staging và xoay hết.

**Điều làm tốt.** Tách recipient theo môi trường giới hạn thiệt hại ở staging; allowlist mạng chặn 14 lần thử. Đây là phòng thủ nhiều lớp
đúng nghĩa, đáng giữ và ghi lại.

## Quyết định cần cân nhắc

- **Mức độ sự cố.** SEV2 hay SEV3: dữ liệu giả, nhưng khoá age mở được mọi secret staging và có người đã thử đăng nhập. Nêu lý do chọn.
- **Có báo ra ngoài không.** Không có dữ liệu cá nhân thật nên không thuộc diện báo theo quy định; nếu Postgres có dữ liệu khách thì quy
  trình khác hẳn (pháp chế, thời hạn thông báo).
- **Bỏ fork công khai hay giữ.** Cấm fork công khai của repo private là thay đổi quy trình làm việc của team; có thể thay bằng nhánh trong
  repo công ty.
- **Đổi hẳn cách quản secret.** Dynamic secret của Vault (mật khẩu Postgres sống 1 giờ, mỗi pod một user) làm lần lộ sau gần như vô hại;
  đổi lại là thêm Vault vào đường chạy của app.

## Rubric (10 điểm)

| Điểm | Tiêu chí |
| --- | --- |
| 1 | Tóm tắt đọc riêng vẫn hiểu: lộ gì, bao lâu, chặn thế nào, hậu quả |
| 1 | Tác động có số: cửa sổ lộ riêng cho mật khẩu và khoá, môi trường, dữ liệu, lần thử truy cập, vì sao production không bị |
| 1 | Timeline đủ mốc, đúng thứ tự, có cả mốc của bot và của các lần đăng nhập lỗi |
| 1 | Nguyên nhân là các điều kiện của hệ thống và quy trình, không có câu đổ lỗi cho người; ít nhất bốn điều kiện |
| 1 | Thứ tự xử lý đúng và có lý do: xoay, thu hồi khoá, rồi mới dọn dấu vết; nói rõ xoá lịch sử không thu hồi được |
| 1 | Thu hồi khoá age đúng kỹ thuật: recipient mới, `updatekeys`, thay khoá trong ArgoCD, gỡ recipient cũ, xoay mọi secret khoá cũ mở được |
| 1 | Phát hiện có hai mốc (công cụ, con người) và vì sao không sớm hơn |
| 1 | Điều làm tốt được ghi nhận (phòng thủ nhiều lớp), không chỉ liệt kê cái hỏng |
| 1 | Action item đủ ba loại phòng ngừa, phát hiện, giảm thiểu; mỗi nguyên nhân có ít nhất một item |
| 1 | Mỗi action item cụ thể, kiểm được, có người và hạn thật |

Trừ điểm: tên người làm hỏng trong phần nguyên nhân; "đã xoá fork nên an toàn"; xoá lịch sử trước khi xoay; quên khoá age, chỉ xoay mật
khẩu; action item kiểu "cẩn thận hơn", "nhắc nhở team".

## Đọc thêm

- Google SRE Book, chương "Postmortem Culture: Learning from Failure".
- GitHub Docs, "Removing sensitive data from a repository": chính tài liệu này nói phải xoay secret trước.
- Module 03 (pre-commit hook chặn secret) và module 16 (quy trình postmortem, error budget) của track.
