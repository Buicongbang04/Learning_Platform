---
customer: Phòng pháp chế (staging)
host: VM staging do IT khách quản
surveyed: 2026-11-04
product: quillo 1.0.0
survey: reports/survey-lawfirm-staging.json
preflight: reports/preflight-lawfirm-staging.json
blockers: []
warnings:
  - check: egress
    detail: Máy không ra internet và không có DNS; mọi image, model và công cụ phải đi trong bundle offline.
  - check: compose
    detail: Docker (gói docker.io của Ubuntu) không có compose (plugin hay binary); bundle mang binary compose v5.6.1 đã ghim sha.
  - check: registry
    detail: >-
      Registry nội bộ 10.0.2.101:5000 chạy HTTP nhưng chưa có trong insecure-registries của Docker; cần sửa
      /etc/docker/daemon.json và restart Docker (máy không bật live-restore).
  - check: mem
    detail: >-
      MemTotal 4913 MB với VM 5 GB IT cấp: đủ min 4096 MB của llm-small, không đủ cho model lớn hơn; giữ 5 GB khi
      lên production.
asks:
  - Xác nhận cửa sổ bảo trì để sửa daemon.json và restart Docker trên máy staging.
  - Giữ RAM VM ở 5 GB (bản mặc định 2 GB không đủ chạy quillo).
  - Mở cổng 18080 từ mạng luật sư tới VM (API bind 0.0.0.0 trong VM).
  - Đầu mối nhận sha256 của SHA256SUMS qua điện thoại hoặc ticket khi giao bundle.
---

# Báo cáo khảo sát máy staging

Gửi: IT phòng pháp chế. Người khảo sát: FDE triển khai quillo. Ngày: 2026-11-04.

Khảo sát chạy bằng `survey/site_survey.sh` với user `fde`, không cần root, không đọc dữ liệu nghiệp vụ, không lưu biến
môi trường hay lịch sử shell; URL proxy (nếu có) đã bỏ phần `user:pass@`. Kết quả thô: `reports/survey-lawfirm-staging.json`.
So với yêu cầu của quillo 1.0.0 (`survey/REQUIREMENTS.yaml`): `reports/preflight-lawfirm-staging.json`.

## Tóm tắt

**Cài được, không có blocker.** Bốn điểm cần chuẩn bị: bundle offline (máy không ra internet), mang compose riêng, khai
registry nội bộ cho Docker (cần restart Docker), giữ RAM 5 GB.

## Máy hiện tại so với yêu cầu

| Mục | Máy staging | quillo 1.0.0 cần | Kết luận |
| --- | --- | --- | --- |
| OS | Ubuntu 22.04, kernel 5.15, glibc 2.35 | Ubuntu ≥ 20.04 | Đạt |
| CPU | 2 vCPU | ≥ 2 | Đạt (vừa đủ; llm và embed mỗi thứ 2 luồng) |
| RAM | MemTotal 4913 MB (VM 5 GB) | ≥ 4096 MB | Đạt |
| Đĩa trống `/` | 27,2 GiB | ≥ 10 GiB (+ ~3,3 GB khi cài) | Đạt |
| GPU | không | tuỳ chọn | Chạy CPU với llm-small |
| Runtime | Docker (gói Ubuntu) | Docker ≥ 20.10 | Đạt |
| Compose | không có | cần để chạy 5 dịch vụ | Mang binary riêng trong bundle |
| Mạng ra ngoài | không (không DNS) | không cần nếu có bundle | Bundle offline |
| Registry nội bộ | `10.0.2.101:5000` HTTP, Docker chưa tin | image phải từ registry nội bộ | Sửa `daemon.json` |
| sudo / SELinux | có sudo / không có SELinux | | Đạt |

## Việc cần IT khách

1. Cho phép sửa `/etc/docker/daemon.json` (thêm `10.0.2.101:5000` vào `insecure-registries`) và restart Docker trong cửa
   sổ bảo trì: restart dừng mọi container đang chạy trên máy vì `live-restore` đang tắt. Installer giữ bản cũ ở
   `daemon.json.bak-quillo` và tự trả lại nếu Docker không lên.
2. Giữ VM ở 5 GB RAM; bản 2 GB mặc định bị preflight chặn (`mem` blocker).
3. Mở cổng 18080 từ mạng của luật sư tới VM.
4. Chỉ định người nhận sha256 của `SHA256SUMS` qua kênh riêng khi bundle đi qua cổng chuyển tệp.

## Thay đổi installer sẽ làm trên máy

`/opt/quillo` (bản phát hành, binary compose, dữ liệu inbox thuộc uid 10001), `/etc/quillo/quillo.env` (0600, mật khẩu
sinh tại chỗ), `/etc/docker/daemon.json` (một khoá), image trong registry nội bộ dưới `ggml-org/`, `pgvector/`,
`quillo-api`, log ở `/var/log/quillo-install.log`. Không cài gói hệ thống, không đổi plugin của Docker.
