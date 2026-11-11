# Postmortem: lộ mật khẩu Postgres staging và khoá age qua fork công khai

Trạng thái: đã duyệt ngày 2026-10-30. Viết theo tinh thần blameless: nói về hệ thống và quy trình, không về lỗi của một người.

## 1. Tóm tắt

Ngày 2026-10-28, một commit sửa chuỗi kết nối DB được push lên fork cá nhân công khai của repo `olist-gitops` kèm hai tệp không được
phép rời máy: `shop/olist-db.dec.yaml` (Secret Postgres staging đã giải mã bằng `sops decrypt` để gỡ lỗi) và `.keys/keys.txt` (khoá riêng
age của team staging). Hai thứ đó công khai 94 phút cho tới khi mật khẩu Postgres được xoay, khoá age công khai 131 phút cho tới khi
recipient cũ bị gỡ. Có 14 lần đăng nhập Postgres staging thất bại từ hai IP lạ, bị allowlist chặn; không có truy cập thành công, không
có dữ liệu khách hàng nào bị đọc. Production không bị ảnh hưởng vì dùng khoá age và mật khẩu riêng.

## 2. Tác động

- Môi trường: chỉ staging. Production mã hoá cho recipient khác và dùng mật khẩu khác, không có trong commit.
- Dữ liệu: Postgres staging chứa dữ liệu Olist công khai đã ẩn danh; không có dữ liệu khách hàng thật.
- Cửa sổ lộ: mật khẩu Postgres 94 phút (09:41 tới 11:15), khoá age staging 131 phút (09:41 tới 11:52).
- Thử truy cập: 14 lần đăng nhập thất bại từ 2 IP nước ngoài lúc 10:05 tới 10:12, bị allowlist mạng chặn trước khi tới bước xác thực.
- Công sức: 3 người, khoảng 5 giờ; staging đóng băng deploy 1 giờ trong lúc xoay khoá.

## 3. Timeline

Giờ Việt Nam (UTC+7), ngày 2026-10-28.

| Giờ | Sự kiện |
| --- | --- |
| 09:12 | Kỹ sư chạy `sops decrypt shop/olist-db.enc.yaml > shop/olist-db.dec.yaml` để xem chuỗi kết nối lỗi |
| 09:40 | `git add -A` và commit "fix db url": commit gồm cả `olist-db.dec.yaml` và `.keys/keys.txt` |
| 09:41 | Push lên fork cá nhân công khai để mở pull request vào repo công ty |
| 09:47 | Bot quét GitHub công khai clone fork (thấy sau trong traffic log của GitHub) |
| 10:05 | 14 lần đăng nhập Postgres staging thất bại từ 2 IP lạ tới 10:12, allowlist chặn |
| 10:20 | GitHub secret scanning gửi email cảnh báo URI Postgres tới chủ fork |
| 11:05 | Chủ fork đọc email sau cuộc họp, báo kênh #incident |
| 11:08 | SRE trực tuyên bố SEV2, đóng băng deploy staging |
| 11:15 | Xoay mật khẩu Postgres staging |
| 11:27 | Tệp SOPS mã hoá lại với mật khẩu mới, ArgoCD sync, api staging Ready |
| 11:52 | Khoá age staging mới: `sops updatekeys` mọi tệp, thay Secret khoá của ArgoCD, restart repo-server, gỡ recipient cũ |
| 12:10 | Xoá fork, nhờ GitHub Support xoá cache view của commit |
| 12:30 | Đọc log Postgres 09:41 tới 12:00: không có đăng nhập thành công ngoài pod của Olist |
| 14:00 | Đóng sự cố, mở postmortem |

## 4. Nguyên nhân gốc

Không có một nguyên nhân duy nhất; năm điều kiện cùng xảy ra:

- Gỡ lỗi Secret cần đọc giá trị đã giải mã, và cách dễ nhất là `sops decrypt` ra tệp `.dec.yaml` trong chính thư mục repo.
- Khoá riêng age của team nằm trong repo (`.keys/keys.txt`) vì `SOPS_AGE_KEY_FILE` được hướng dẫn trỏ vào thư mục dự án; `.gitignore`
  không có `.keys/` hay `*.dec.yaml`.
- Repo không có pre-commit hook chặn tệp chứa `AGE-SECRET-KEY-` hay Secret chưa mã hoá (hook của module 03 chỉ cài ở repo code).
- Fork cá nhân không được push protection của tổ chức che: push protection bật ở repo công ty, không ở fork.
- Cảnh báo secret scanning chỉ gửi tới chủ fork qua email, không tới kênh của team trực.

## 5. Xử lý và khôi phục

1. Coi mọi thứ trong commit là đã lộ ngay từ 09:41: bot đã clone nên xoá fork không thu hồi được gì.
2. Xoay mật khẩu Postgres staging trước tiên (11:15) vì đây là thứ kẻ tấn công dùng được ngay; kiểm allowlist vẫn đang chặn.
3. Mã hoá lại Secret với mật khẩu mới bằng `seal.sh` theo `.sops.yaml`, commit, để ArgoCD sync và kiểm `/readyz` của api.
4. Thu hồi khoá age cũ: tạo khoá mới, thêm recipient mới vào `.sops.yaml`, `sops updatekeys` mọi tệp `*.enc.yaml`, thay Secret khoá
   riêng của ArgoCD, restart repo-server, rồi gỡ recipient cũ. Mọi giá trị từng mã hoá bằng khoá cũ đều coi là đã lộ và đã xoay.
5. Sau khi đã xoay xong mới dọn dấu vết: xoá fork, nhờ GitHub Support xoá cache. Commit không vào repo công ty nên không cần git
   filter-repo; nếu đã vào thì viết lại lịch sử chỉ là dọn dẹp, không phải biện pháp bảo mật.
6. Đọc log Postgres và audit log của GitHub để chắc không có truy cập thành công.

## 6. Phát hiện

GitHub secret scanning nhận ra URI Postgres sau 39 phút (10:20), nhưng cảnh báo tới email của một người đang họp nên con người chỉ biết
sau 84 phút (11:05). Khoá age không bị cảnh báo vì không có mẫu cho `AGE-SECRET-KEY-`. Không có cảnh báo từ phía Postgres dù có 14 lần
đăng nhập lỗi, vì staging chưa có alert cho đăng nhập thất bại.

## 7. Điều làm tốt và điều chưa tốt

- Tốt: khoá và mật khẩu tách theo môi trường (recipient riêng cho production), nên production không phải xoay gì.
- Tốt: Postgres staging chỉ nhận kết nối từ dải IP của cluster; 14 lần thử đều bị chặn trước khi tới bước xác thực.
- Tốt: người phát hiện báo ngay vào kênh sự cố, kèm link commit.
- Chưa tốt: không có runbook xoay khoá age; mất khoảng 25 phút để thống nhất thứ tự `updatekeys`, thay Secret, restart repo-server.
- Chưa tốt: hướng dẫn dự án đặt khoá riêng trong thư mục repo.
- Chưa tốt: cảnh báo đi tới một người, không tới kênh trực.

## 8. Action items

| Việc | Người phụ trách | Hạn | Loại |
| --- | --- | --- | --- |
| Thêm `.keys/`, `*.dec.yaml` vào `.gitignore`; sửa hướng dẫn: khoá age ở `~/.config/sops/age/keys.txt`, không trong repo | Team Olist (An) | 2026-10-31 | Phòng ngừa |
| Pre-commit hook và job CI chạy gitleaks với rule cho `AGE-SECRET-KEY-`, Secret không có `sops:` và tệp `*.dec.yaml` | Platform (Bình) | 2026-11-07 | Phòng ngừa |
| Bật push protection cho mọi fork của repo tổ chức, cấm fork công khai của repo private | Platform (Bình) | 2026-11-03 | Phòng ngừa |
| Chuyển cảnh báo secret scanning vào kênh #incident và PagerDuty của SRE | SRE (Chi) | 2026-11-05 | Phát hiện |
| Alert khi Postgres staging có hơn 5 lần đăng nhập lỗi trong 5 phút | SRE (Chi) | 2026-11-14 | Phát hiện |
| Runbook xoay khoá age và mật khẩu DB, diễn tập định kỳ mỗi quý trên staging | SRE (Dũng) | 2026-11-21 | Giảm thiểu |
| Chuyển mật khẩu Postgres sang dynamic secret của Vault (TTL 1 giờ) qua External Secrets Operator | Team Olist (An) | 2027-01-15 | Giảm thiểu |
