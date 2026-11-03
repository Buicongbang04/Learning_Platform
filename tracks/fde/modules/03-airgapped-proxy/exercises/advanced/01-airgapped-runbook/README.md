---
title: Runbook cài ở khách air-gapped
level: advanced
services: []
files:
  - path: starter/runbook.md
    note: Khung runbook 7 phần
run: []
---

## Mục tiêu

Ở khách air-gapped, ngày cài không phải ngày làm việc: đó là ngày **thực hiện** một kế hoạch đã được IT và An ninh duyệt
từ trước. Mọi câu hỏi chưa có câu trả lời trước ngày đó sẽ được trả lời bằng thời gian của cửa sổ bảo trì, mà cửa sổ thì
không kéo dài được. Bài này viết runbook mà người khác (kể cả IT khách) đọc và làm theo được, có điểm dừng rõ ràng.

## Đề bài

Công ty luật Minh An (hư cấu) đã chạy thử `quillo` trên staging (bài intermediate 02) và duyệt đưa `quillo-1.1.0` lên
production. Những gì bạn biết:

| Mục | Thông tin |
| --- | --- |
| Máy | `qa-prod-01`, Ubuntu 22.04, 8 CPU, 32 GB RAM, `/srv` 200 GB; Docker `docker.io` 29 của Ubuntu, **không** plugin compose |
| Mạng | Không ra internet, có DNS nội bộ; người dùng truy cập từ mạng văn phòng `10.20.0.0/16` |
| Registry | Harbor `registry.minhan.internal`, **HTTPS** bằng chứng chỉ do "Minh An Root CA" (CA nội bộ) cấp; project `vendors` |
| Chuyển tệp | Cổng MFT của khách: tối đa 2 GB một tệp, quét virus có thể mất tới 24 giờ, tệp đến `/srv/mft-inbox/` (chủ là IT) |
| Quyền | Bạn **không** có sudo; anh Tuấn (quản trị Linux) gõ lệnh sudo theo runbook, chia sẻ màn hình |
| Duyệt | Hội đồng thay đổi (CAB) cần runbook trước 5 ngày làm việc; chị Lan (An ninh) duyệt phần mạng và chứng chỉ |
| Cửa sổ | Thứ Bảy 08:00–11:00; quá 10:30 mà chưa đạt thì phải quay về trạng thái ban đầu |
| Dữ liệu | 2 000 hợp đồng mẫu do khách nạp sau khi bàn giao, không có trên USB |

Bundle: `quillo-1.1.0.tar` (1,08 GiB, cấu trúc như `tracks/fde/product/README.md`), binary compose v5.6.1 ghim sha256, script
cài của bạn. Viết `starter/runbook.md`. Bài không có test; tự chấm theo rubric, đạt đủ 10 mục, rồi so với bài mẫu trong
`solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| R1 | Tóm tắt ≤ 8 dòng: cài gì, ở đâu, khi nào, ai làm gì, điều kiện "xong", điều kiện quay về |
| R2 | Checklist trước ngày cài chia theo người chịu trách nhiệm, mỗi mục có **ai xác nhận** và **hạn**; tối thiểu: kênh chuyển tệp và thời gian quét, registry (địa chỉ, project, tài khoản đẩy image, CA), Docker và compose, chỗ trống và RAM, cổng và địa chỉ nghe, DNS/NTP, sao lưu, người liên hệ trong cửa sổ |
| R3 | Chuyển giao và toàn vẹn: lịch gửi tính ngược từ ngày cài theo thời gian quét; sha256 của danh sách checksum gửi qua kênh khác USB/MFT; khi không khớp thì làm gì; tệp nào có thể bị máy quét chặn nhầm và phương án |
| R4 | Các bước ngày cài theo thứ tự, mỗi bước có lệnh (hoặc trỏ tới script), kết quả mong đợi, thời gian ước tính có cách đo, người làm; kiểm tra luôn đứng trước thay đổi |
| R5 | Ít nhất 3 điểm go/no-go có tiêu chí đo được (không phải "nếu ổn") và mốc giờ |
| R6 | Quay về: theo từng bước, hoàn tác cái gì; quyết định quay về dựa trên mốc giờ của cửa sổ; nói rõ dữ liệu nào bị mất (hoặc không) |
| R7 | Chứng chỉ: Docker tin CA nội bộ để kéo/đẩy với Harbor bằng cách đúng (không `insecure-registries`, không tắt kiểm chứng chỉ), cách kiểm fingerprint CA với chị Lan |
| R8 | Bí mật: sinh tại chỗ, không nằm trên USB hay trong runbook/log, lưu ở đâu với quyền gì, giao token quản trị cho ai bằng cách nào |
| R9 | Bằng chứng bàn giao: những gì thu lại (log, kết quả kiểm, `Id`/`RepoDigests` của image so với bản đã kiểm (manifest/biên bản diễn tập), `/healthz`), không chứa bí mật; ai ký nhận |
| R10 | Mục "Không làm" (vd. không cắm điện thoại phát mạng, không mang laptop cá nhân vào mạng khách, không tắt TLS) và mục "Câu hỏi còn mở" có ít nhất 3 câu khách phải trả lời trước CAB |

## Tiêu chí đạt

- `runbook.md` đạt đủ R1–R10 khi tự chấm từng mục.
- Mọi lệnh trong runbook chạy được trên máy như mô tả (Ubuntu 22.04, không mạng, không công cụ ngoài bundle và gói có sẵn
  của Ubuntu), không lệnh nào cần internet.
- Tổng thời gian các bước ngày cài (theo ước tính của bạn) cộng thời gian quay về vẫn nằm trong cửa sổ 3 giờ.

## Gợi ý

### Gợi ý 1

Viết ngược từ 10:30: nếu phải quay về lúc đó, việc quay về mất bao lâu, cần những gì đã chuẩn bị sẵn? Từ đó suy ra mốc
go/no-go cuối cùng.

### Gợi ý 2

Đi lại từng lệnh của bài intermediate 02 và hỏi: cái gì ở production khác staging (registry HTTPS, CA nội bộ, Harbor cần
đăng nhập, không có sudo trực tiếp)? Mỗi khác biệt là một mục checklist hoặc một câu hỏi.

### Gợi ý 3

Người đọc runbook vào sáng thứ Bảy có thể không phải bạn. Mỗi bước phải nói "đúng thì thấy gì" để anh Tuấn tự biết có
được đi tiếp hay không.
