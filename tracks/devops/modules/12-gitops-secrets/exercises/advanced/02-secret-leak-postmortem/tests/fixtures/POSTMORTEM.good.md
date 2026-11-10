# Postmortem: lộ credential Kafka staging của payments-api qua snippet công khai (ví dụ đạt, hệ thống khác)

Trạng thái: đã duyệt ngày 2026-09-18. Blameless: nói về hệ thống và quy trình.

## 1. Tóm tắt

Ngày 2026-09-15, một kỹ sư dán nội dung `values-staging.dec.yaml` (bản đã giải mã bằng `sops decrypt` để gỡ lỗi chart Helm của
payments-api) vào một snippet GitLab để hỏi đồng nghiệp, snippet để chế độ public. Tệp chứa username và mật khẩu SASL của Kafka staging
cùng khoá riêng age của môi trường staging. Credential bị lộ 52 phút trước khi bị thu hồi. Không có truy cập trái phép nào thành công;
production không bị ảnh hưởng vì dùng recipient và credential riêng.

## 2. Tác động

- Môi trường: chỉ staging. Production dùng khoá age và user Kafka riêng, không nằm trong tệp.
- Dữ liệu: topic staging chỉ có dữ liệu giả; không có dữ liệu khách hàng thật.
- Cửa sổ lộ: 52 phút (14:03 tới 14:55, lúc xoay xong mật khẩu SASL); khoá age staging lộ 97 phút tới khi gỡ recipient cũ.
- Thời gian người tham gia xử lý: 3 người, khoảng 4 giờ.

## 3. Timeline

Giờ Việt Nam (UTC+7), ngày 2026-09-15.

| Giờ | Sự kiện |
| --- | --- |
| 13:58 | Kỹ sư chạy `sops decrypt` ra `values-staging.dec.yaml` để xem giá trị chart render |
| 14:03 | Dán nội dung tệp vào snippet GitLab public, gửi link vào kênh chat |
| 14:11 | Đồng nghiệp mở link, nhận ra trong snippet có mật khẩu, báo kênh #incident |
| 14:14 | SRE trực tuyên bố SEV3, xoá snippet |
| 14:20 | Kiểm audit log Kafka: chưa có kết nối lạ |
| 14:55 | Xoay mật khẩu SASL user `payments-staging`, cập nhật tệp SOPS, ArgoCD sync |
| 15:40 | Tạo khoá age staging mới, `sops updatekeys` mọi tệp, thay Secret khoá trên cluster, gỡ recipient cũ |
| 16:30 | Đọc lại audit log Kafka 14:03 tới 15:00: không có đăng nhập ngoài dải IP nội bộ |
| 17:00 | Đóng sự cố, mở postmortem |

## 4. Nguyên nhân gốc

- Quy trình gỡ lỗi chart cần đọc giá trị đã giải mã, và cách dễ nhất là ghi ra tệp `.dec.yaml` trong thư mục làm việc.
- Tệp giải mã chứa cả khoá riêng age vì script gỡ lỗi nội bộ gom `SOPS_AGE_KEY` vào cùng tệp values.
- Không có rào nào giữa tệp giải mã và nơi chia sẻ: snippet không qua pre-commit hook hay push protection như repo.
- Snippet mặc định là public trong cài đặt GitLab của công ty.

## 5. Xử lý và khôi phục

1. Xoá snippet ngay khi thấy, nhưng coi như đã lộ: nội dung public có thể đã bị bot chép.
2. Thu hồi và xoay mật khẩu SASL của user Kafka staging trước tiên, vì đây là thứ dùng được ngay.
3. Cập nhật giá trị mới vào tệp SOPS, để ArgoCD sync, kiểm consumer staging kết nối lại.
4. Tạo khoá age staging mới, thêm recipient mới, chạy `sops updatekeys`, thay Secret khoá trên cluster, rồi gỡ recipient cũ.
5. Không cần xoá lịch sử git vì nội dung không vào repo; nếu đã vào thì git filter-repo chỉ làm sau khi đã xoay, vì xoá lịch sử không
   thu hồi được bản đã bị chép.

## 6. Phát hiện

Phát hiện sau 8 phút nhờ người đọc, không phải công cụ: GitLab secret detection chỉ quét repo, không quét snippet, và không có cảnh
báo nào từ Kafka vì không có đăng nhập lạ. Nếu đồng nghiệp không đọc kỹ, thời gian phát hiện có thể là vài ngày.

## 7. Điều làm tốt và điều chưa tốt

- Tốt: người phát hiện báo ngay vào kênh sự cố thay vì nhắn riêng.
- Tốt: khoá và credential tách theo môi trường nên production không phải xoay.
- Chưa tốt: không có runbook xoay khoá age, mất 45 phút tìm lệnh.
- Chưa tốt: snippet public là mặc định và không ai biết.
- Chưa tốt: script gỡ lỗi gom khoá riêng vào tệp values.

## 8. Action items

| Việc | Người phụ trách | Hạn | Loại |
| --- | --- | --- | --- |
| Đổi mặc định snippet sang private, chặn snippet public cho nhóm engineering | Platform (Hà) | 2026-09-22 | Phòng ngừa |
| Script gỡ lỗi render chart in ra stdout, không ghi tệp `.dec.yaml`, không bao giờ kèm khoá | Team payments (Tùng) | 2026-09-25 | Phòng ngừa |
| Bật gitleaks trong pre-commit và CI, thêm rule cho `AGE-SECRET-KEY-` và `.dec.yaml` | Platform (Hà) | 2026-09-30 | Phòng ngừa |
| Runbook xoay khoá age và credential Kafka, diễn tập mỗi quý | SRE (Minh) | 2026-10-05 | Giảm thiểu |
| Chuyển credential Kafka sang dynamic secret của Vault, TTL 1 giờ, xoay tự động | SRE (Minh) | 2026-11-30 | Giảm thiểu |
| Cảnh báo khi Kafka có đăng nhập từ ngoài dải IP nội bộ | SRE (Lan) | 2026-10-10 | Phát hiện |
