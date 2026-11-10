# Lời giải: Hồ sơ trình An ninh thông tin ngân hàng

## Hướng làm

1. **Viết theo câu hỏi của người duyệt**, không theo cấu trúc sản phẩm: nguồn gốc ⇒ thành phần ⇒ quyền/mạng/dữ liệu ⇒
   installer ⇒ việc của họ.
2. **Thử mọi lệnh trên máy không mạng** trước khi gửi. Với cosign v3, `sign-blob` mặc định đẩy lên Rekor và `verify-blob`
   mặc định đòi bằng chứng tlog; ở ngân hàng phải ký với `--use-signing-config=false --tlog-upload=false` và kiểm với
   `--insecure-ignore-tlog=true`. Lệnh kiểm đã được thử trong sandbox `bwrap --unshare-net`: in `Verified OK`.
3. **Tra giấy phép từng thành phần ở nguồn**: Qwen2.5-0.5B-Instruct (Apache-2.0, trang model trên Hugging Face),
   nomic-embed-text-v1.5 (Apache-2.0), llama.cpp (MIT), pgvector (PostgreSQL License), PostgreSQL (PostgreSQL License),
   quillo (MIT, `tracks/fde/product/LICENSE`).
4. **Không hứa điều không kiểm được**: "không có CVE", "an toàn tuyệt đối". Hứa quy trình và thời hạn.

## Rubric (tự chấm, đạt đủ 10 mục)

| # | Bài mẫu đạt ở đâu |
| --- | --- |
| S1 | "Tóm tắt": 7 dòng, có hạn 18/11/2026 và lý do (hồ sơ CAB 19/11 cho cửa sổ 28/11) |
| S2 | Bảng mục 1: nguồn, phiên bản, digest/sha256, giấy phép từng thành phần |
| S3 | Mục 2: ba lệnh, output mong đợi, "không khớp thì không cài, báo lại" |
| S4 | Mục 2: khoá giao qua email + đọc fingerprint qua điện thoại, ai giữ khoá riêng, xoay/thu hồi, hệ quả của việc tắt tlog |
| S5 | Mục 3: CycloneDX mỗi image + phần Python, `syft` v1.55.0, quét offline bằng công cụ của ngân hàng (vd. grype với DB nhập tay) |
| S6 | Mục 3: bảng thời hạn theo mức độ, ghi nhận "không ảnh hưởng" kèm lý do |
| S7 | Mục 4: `svc-quillo` rootless, không sudo, SELinux enforcing + `:Z`, một cổng trên IP do IT chọn, không kết nối ra |
| S8 | Mục 4: volume Postgres trong home `svc-quillo`, log không chứa nội dung tài liệu/câu hỏi, không telemetry, xoá bằng `podman volume rm` + biên bản |
| S9 | Mục 5: danh sách thao tác, không tải gì, quay lại, gỡ hoàn toàn |
| S10 | Mục 6: 4 câu hỏi; không có đề nghị sudo/tắt SELinux/mở mạng |

Lỗi hay gặp: gửi lệnh `cosign verify-blob` mặc định (cần internet, lỗi ở ngân hàng); ghi "model: MIT" theo giấy phép của
sản phẩm; gửi khoá công khai **cùng** MFT với bundle (kẻ sửa được bundle thì thay được khoá); tóm tắt dài một trang.

## Bài mẫu

````markdown
# Hồ sơ an ninh: quillo 1.1.0 cho Ngân hàng Hải Đăng

Gửi: chị Mai (An ninh thông tin) · Từ: FDE phụ trách pilot · Ngày: thứ Tư 04/11/2026

## Tóm tắt

- quillo là ứng dụng tra cứu tài liệu nội bộ cho Khối Pháp chế, chạy hoàn toàn trên máy chủ của ngân hàng.
- Chạy bằng Podman rootless dưới tài khoản `svc-quillo`, không cần sudo, SELinux giữ enforcing.
- Không kết nối ra ngoài; mở đúng một cổng HTTP (18080) trên địa chỉ nội bộ do IT chọn.
- Dữ liệu tài liệu và chỉ mục nằm trong một volume Postgres trên chính máy đó; không có telemetry.
- Bộ giao: `quillo-1.1.0.tar`, chữ ký `quillo-1.1.0.tar.sigstore.json`, SBOM, hồ sơ này.
- Đề nghị chị kiểm theo mục 2–3 và trả lời mục 6.
- Cần kết quả duyệt **trước thứ Tư 18/11/2026** để kịp hồ sơ CAB thứ Năm 19/11 cho cửa sổ thứ Bảy 28/11.

## 1. Thành phần và giấy phép

| Thành phần | Nguồn và phiên bản | Định danh | Giấy phép |
| --- | --- | --- | --- |
| Postgres + pgvector | `pgvector/pgvector:0.8.6-pg16` (Docker Hub) | `sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b` | PostgreSQL License |
| llama.cpp server (CPU) | `ghcr.io/ggml-org/llama.cpp:server-b11718` | `sha256:4b7be0376002b4450a357a109bab804093ff9251193cc75ed4ce0cb39953ff5c` | MIT |
| quillo-api | Build nội bộ 1.1.0 trên `python:3.12.14-slim-bookworm` | sha256 của `images/quillo-api.tar` trong `manifest.json` | MIT |
| Model chat | Hugging Face `Qwen/Qwen2.5-0.5B-Instruct-GGUF`, rev `9217f5db…`, `qwen2.5-0.5b-instruct-q4_k_m.gguf` | `sha256:74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` | Apache-2.0 |
| Model embedding | Hugging Face `nomic-ai/nomic-embed-text-v1.5-GGUF`, rev `0188c9bf…`, `nomic-embed-text-v1.5.Q8_0.gguf` | `sha256:3e24342164b3d94991ba9692fdc0dd08e3fd7362e0aacc396a9a5c54a544c3b7` | Apache-2.0 |

Thư viện Python trong `quillo-api` và gói hệ điều hành trong từng image có trong SBOM (mục 3), kèm giấy phép từng gói.

## 2. Kiểm tra toàn vẹn và nguồn gốc

Khoá công khai `quillo-release.pub` của chúng tôi đã gửi riêng qua email từ địa chỉ công ty ngày 04/11; fingerprint
(sha256 của tệp khoá) em đọc trực tiếp với chị qua điện thoại: `a7501f99…b0fa` (đủ 64 ký tự trong email). Khoá chỉ
giao một lần; các bản sau dùng lại.

Chị chạy trên máy kiểm tra của ngân hàng, không cần mạng:

```bash
sha256sum quillo-release.pub
sha256sum quillo-1.1.0.tar
cosign verify-blob --key quillo-release.pub --bundle quillo-1.1.0.tar.sigstore.json \
  --insecure-ignore-tlog=true quillo-1.1.0.tar
```

Mong đợi: dòng 1 khớp fingerprint đã đọc qua điện thoại; dòng 2 khớp sha256 trong email giao bản; lệnh 3 in
`Verified OK` (kèm cảnh báo bỏ qua transparency log, xem dưới). cosign tải từ trang phát hành chính thức, bản v3.1.4,
sha256 `424e2c97d0b45fd7a6b608a87f090f35633f4c23ece5f092d48bba11aaf4bbfa`. Bất kỳ dòng nào không khớp: **không cài**,
báo lại em; em gửi lại bản qua kênh khác, không "sửa cho khớp".

Chúng tôi ký ở chế độ offline (không đưa chữ ký lên transparency log công khai, vì máy của ngân hàng không kiểm được log
đó). Hệ quả: an toàn của chữ ký dựa hoàn toàn vào khoá riêng. Khoá riêng chỉ nằm trong máy ký của đội phát hành (2 người,
mật khẩu tách người giữ), xoay mỗi năm. Khi khoá lộ hay xoay, chúng tôi báo chị bằng văn bản, giao khoá mới cùng cách trên,
và chị xoá khoá cũ khỏi danh sách tin cậy.

## 3. SBOM và lỗ hổng

Kèm theo: `sbom/pgvector.cdx.json`, `sbom/llama-cpp-server.cdx.json`, `sbom/quillo-api.cdx.json` (CycloneDX JSON, tạo bằng
`syft scan docker-archive:images/<image>.tar -o cyclonedx-json`, syft v1.55.0). Chị quét bằng công cụ của ngân hàng; nếu
dùng grype: tải DB lỗ hổng ở vùng có mạng, chuyển qua MFT, `grype db import <tệp DB>`, rồi `grype sbom:sbom/quillo-api.cdx.json`.
Kết quả quét của chúng tôi lúc phát hành kèm trong `sbom/scan-1.1.0.txt` để chị đối chiếu.

Bản nào cũng có CVE đã biết trong gói hệ điều hành của image; chúng tôi không hứa "không có CVE" mà cam kết xử lý:

| Mức (CVSS) | Thời hạn giao bản vá (PATCH đầy đủ, ký như trên) |
| --- | --- |
| Nghiêm trọng (≥9,0) và có đường khai thác trong cách quillo chạy | 7 ngày |
| Cao (7,0–8,9) | 30 ngày |
| Trung bình, thấp | Bản MINOR kế tiếp |

CVE nằm trong thành phần không chạy ở cấu hình của ngân hàng (vd. công cụ dòng lệnh không được gọi) được ghi "không ảnh
hưởng" trong `scan-1.1.0.txt` kèm lý do để chị kiểm, không bị lờ đi.

## 4. Quyền, mạng và dữ liệu

- **Quyền**: mọi container chạy bằng Podman rootless dưới `svc-quillo` (không sudo, không thuộc nhóm đặc quyền); container
  không `--privileged`, không mount socket hệ thống. SELinux giữ enforcing; volume gắn nhãn `:Z` để chỉ container của
  quillo đọc được.
- **Mạng**: API nghe cổng 18080 trên địa chỉ IT chỉ định (mặc định `127.0.0.1`); Postgres và llama.cpp chỉ nghe trong
  mạng nội bộ của Podman, không publish ra máy. Không kết nối ra ngoài: không cập nhật tự động, không gọi API bên ngoài,
  model chạy tại chỗ.
- **Dữ liệu**: tài liệu nạp vào và vector lưu trong volume Postgres dưới `/home/svc-quillo/.local/share/containers/`; chỉ
  `svc-quillo` và root đọc được. Log ghi thời điểm, đường dẫn API, mã kết quả, thời gian xử lý; **không** ghi nội dung tài
  liệu, câu hỏi hay câu trả lời. Không telemetry.
- **Kết thúc pilot**: `podman volume rm` các volume của quillo, xoá image và thư mục cài; chúng tôi lập biên bản các lệnh đã
  chạy để chị đối chiếu.

## 5. Installer, quay lại và gỡ cài

Installer (`install.sh`, chạy bằng `svc-quillo`) làm đúng các việc sau và không tải gì từ mạng:

1. Kiểm manifest (đủ tệp, sha256, kích thước) và chỗ trống, trước mọi thay đổi.
2. Giải nén vào `/home/svc-quillo/quillo/releases/1.1.0/`; `podman load` ba image.
3. Ghi cấu hình vào `/home/svc-quillo/.config/quillo/` (chỉ lần đầu) và unit Quadlet vào
   `/home/svc-quillo/.config/containers/systemd/`.
4. Khởi động, chờ `/healthz` báo đúng bản; không đạt thì quay về bản trước và báo lỗi.

Cần IT làm một lần với quyền quản trị: `loginctl enable-linger svc-quillo` (để dịch vụ chạy khi không ai đăng nhập).
Quay lại bản trước: `install.sh` với bundle bản trước (giữ trên máy). Gỡ hoàn toàn: `uninstall.sh` dừng dịch vụ, xoá unit,
image, thư mục cài; xoá dữ liệu là bước riêng cần chị xác nhận.

## 6. Câu hỏi cho An ninh thông tin

1. Kênh nào ngân hàng chấp nhận để nhận khoá công khai và sha256 mỗi bản (email có chữ ký, cổng hỗ trợ, văn bản)?
2. Ngân hàng quét SBOM bằng công cụ nào, và cần chúng tôi xuất định dạng nào (CycloneDX hay SPDX)?
3. Chính sách lưu log ứng dụng: thời hạn, có cần đẩy về hệ thống log tập trung không?
4. Ai được phép chạy installer trong cửa sổ: IT ngân hàng theo runbook, hay FDE dưới giám sát?
````
