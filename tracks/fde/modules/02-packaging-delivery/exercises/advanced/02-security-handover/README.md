---
title: Hồ sơ trình An ninh thông tin ngân hàng
level: advanced
services: []
files:
  - path: starter/security-pack.md
    note: Khung hồ sơ 6 phần
run: []
---

## Mục tiêu

Ở ngân hàng, bundle không vào được máy chủ nào trước khi An ninh thông tin ký duyệt, và người duyệt **không tin** bạn:
họ muốn tự kiểm được bundle là của bạn, không bị sửa, trong đó có gì, chạy với quyền gì, đụng tới dữ liệu nào. Hồ sơ
tốt rút 5 ngày duyệt xuống còn một lượt; hồ sơ tệ thêm một vòng hỏi đáp mỗi tuần.

## Đề bài

Ngân hàng Hải Đăng (hư cấu, như các bài trước) sắp nhận `quillo-1.1.0` lần đầu: Rocky Linux 8, SELinux enforcing, Podman
rootless, tài khoản dịch vụ `svc-quillo` **không** sudo, không ra internet, tệp vào qua cổng MFT. Người duyệt: chị Mai (An
ninh thông tin). Bundle của bạn:

- `quillo-1.1.0.tar` (1,08 GiB): ba image (`pgvector/pgvector:0.8.6-pg16`, `ghcr.io/ggml-org/llama.cpp:server-b11718`,
  `quillo-api:1.1.0`) ghim digest trong `manifest.json`; model `qwen2.5-0.5b-instruct-q4_k_m.gguf` và
  `nomic-embed-text-v1.5.Q8_0.gguf` (nguồn Hugging Face, ghim revision + sha256 trong `fdekit.MODELS`); `compose.yaml`,
  migration, `REQUIREMENTS.yaml`, `LICENSE` (MIT). Chi tiết: `tracks/fde/product/README.md`.
- API publish cổng `QUILLO_PORT` (mặc định 18080) trên `QUILLO_BIND` (mặc định `127.0.0.1`); dữ liệu tài liệu và vector
  nằm trong volume Postgres; không gọi dịch vụ ngoài nào.
- Bạn có cosign và syft (module này, phần 0 và 3); công ty bạn chưa từng ký bundle cho khách nào.

Viết `starter/security-pack.md` gửi chị Mai. Bài không có test; tự chấm theo rubric, đạt đủ 10 mục, rồi so với bài mẫu
trong `solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| S1 | Tóm tắt đầu hồ sơ không quá 10 dòng: là gì, chạy ở đâu, quyền gì, mạng gì, dữ liệu gì, chị Mai cần làm gì và trước ngày nào |
| S2 | Danh mục thành phần: mỗi image và model có nguồn, phiên bản, digest/sha256, giấy phép; giấy phép đúng với thực tế của từng thành phần |
| S3 | Lệnh kiểm **chị Mai tự chạy được** bằng công cụ của ngân hàng hoặc công cụ có checksum chính thức: `sha256sum -c`, `cosign verify-blob` với khoá công khai, kèm output mong đợi và việc phải làm khi không khớp |
| S4 | Khoá: khoá công khai và fingerprint giao qua kênh khác kênh giao bundle, một lần; ai giữ khoá riêng, xoay và thu hồi thế nào; nói rõ chế độ ký offline (không transparency log) và hệ quả của nó |
| S5 | SBOM: định dạng chuẩn (CycloneDX hoặc SPDX), mỗi image/thành phần một tệp, tạo bằng gì, và cách ngân hàng tự quét lỗ hổng không cần mạng |
| S6 | Lỗ hổng: không hứa "không có CVE"; có chính sách xử lý theo mức độ (thời hạn vá) và cách ghi nhận CVE không ảnh hưởng |
| S7 | Quyền và bề mặt tấn công: rootless, user nào, không sudo, SELinux giữ enforcing, cổng nào nghe trên địa chỉ nào, kết nối ra ngoài: không có |
| S8 | Dữ liệu: nằm ở đâu, ai đọc được, log chứa gì và không chứa gì, không telemetry, xoá dữ liệu khi kết thúc pilot thế nào |
| S9 | Installer làm gì: danh sách thao tác (ghi ở đâu, tạo gì), không tải gì, cách quay lại và cách gỡ hoàn toàn |
| S10 | Mục "Câu hỏi cho An ninh thông tin" có ít nhất 3 câu cần ngân hàng quyết (vd. kênh nhận khoá, công cụ quét, chính sách lưu log), và không có đề nghị nới bảo mật nào |

## Tiêu chí đạt

- `security-pack.md` đạt đủ S1–S10 khi tự chấm từng mục.
- Mọi lệnh trong hồ sơ chạy được đúng như viết với phiên bản công cụ ghi trong module (cosign v3.1.4, syft v1.55.0) và
  không cần mạng ở phía ngân hàng.

## Gợi ý

### Gợi ý 1

Viết từ câu hỏi của người duyệt ngược về: "làm sao tôi biết tệp này là của các anh?", "trong này có gì?", "nó chạy với
quyền gì, nói chuyện với ai?", "dữ liệu của tôi đi đâu?", "có chuyện thì gỡ thế nào?".

### Gợi ý 2

Chế độ ký mặc định của cosign cần internet ở cả lúc ký lẫn lúc kiểm. Thử lệnh của bạn trên một máy không mạng trước khi
gửi.

### Gợi ý 3

Giấy phép của model không nằm trong SBOM của image; tra trên trang model.
