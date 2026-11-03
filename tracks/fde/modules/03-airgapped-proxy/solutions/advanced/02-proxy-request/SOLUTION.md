# Lời giải: đề nghị mạng và chứng chỉ gửi IT/An ninh bệnh viện

## Hướng làm

1. Tách việc theo máy: `bv-app-01` (vùng bệnh án) **không** xin gì; mọi thứ xin cho `bv-build-01`.
2. Với từng việc, hỏi "có cần mạng ở máy đó không": model và bundle làm ở văn phòng rồi mang vào (offline); chỉ việc dựng
   image connector của team bệnh viện thật sự cần Docker Hub và PyPI tại chỗ.
3. Đo tên miền thật: chạy `docker pull`, `pip install`, tải model qua mitmproxy của lab rồi đọc log (bài mẫu đo ngày
   04/11/2026, xem bảng). Không đoán, không wildcard.
4. Mặc định **soi + tin CA**. Không xin bypass nào: mọi công cụ trong danh sách đều cấu hình CA được (đã chứng minh ở bài
   basic 01 và intermediate 01).
5. Liệt kê chỗ phải tin CA theo cơ chế, cách kiểm, ai làm; thêm cách để An ninh tự kiểm cam kết "không tắt TLS".

Chỗ hay sai: xin `*.docker.io`/`*.docker.com` thay vì tên cụ thể; quên tên miền CDN (blob của Docker Hub, tệp của PyPI và
Hugging Face nằm ở tên miền khác tên bạn gõ); xin bypass cho Docker Hub "vì Docker không chạy sau proxy" (sai: daemon
dùng trust store hệ thống, chỉ cần restart); xin mạng cho máy chủ ứng dụng; đề xuất `ngrok`/reverse SSH để hỗ trợ.

## Rubric (tự chấm, đạt đủ 8 mục)

| # | Bài mẫu đạt ở đâu |
| --- | --- |
| P1 | "Tóm tắt": 5 dòng, xin 5 tên miền cho `bv-build-01`, không bypass, không gì cho vùng bệnh án, cần duyệt trước 18/11 |
| P2 | Mục 1: 7 tên miền đã đo, mỗi dòng đủ cổng, máy nguồn, mục đích, tần suất, dung lượng, thời hạn; hai tên Hugging Face ghi để IT biết nhưng không xin |
| P3 | Cột "Đề nghị" từng dòng: soi + CA cho Docker Hub và PyPI, offline cho Hugging Face, lý do từng dòng; không bypass |
| P4 | Mục 2: 6 chỗ, cơ chế đúng (trust store hệ thống; dockerd đọc lúc khởi động; image có trust store riêng; `requests` dùng `certifi`; pip 25 dùng trust store hệ thống của image hoặc `PIP_CERT`; Node/Java nếu dùng sau), ai làm, lệnh kiểm |
| P5 | Mục 5: cam kết + cách An ninh tự kiểm (grep cấu hình, chạy image tới endpoint chứng chỉ lạ phải lỗi) |
| P6 | Mục 3: luồng offline qua MFT, sha256 của `SHA256SUMS` qua điện thoại, installer kiểm manifest, không cấu hình proxy trên `bv-app-01` |
| P7 | Mục 4: dùng kênh có sẵn của bệnh viện, anh Phong bật theo phiên, ghi lại, không đường hầm tự dựng |
| P8 | Mục 5–6: 4 rủi ro kèm người chấp nhận, ngày đóng tên miền 28/02/2027, 4 câu hỏi |

---

## Bài mẫu

# Đề nghị mạng và chứng chỉ cho quillo: Bệnh viện Đa khoa Sông Hồng

Gửi: chị Hoa (An ninh), anh Phong (Quản trị hệ thống) · Từ: FDE … · Ngày: 04/11/2026

## Tóm tắt

- Xin mở **5 tên miền** qua proxy (vẫn soi TLS) cho **một** máy: `bv-build-01`, từ 23/11/2026 đến 28/02/2027.
- **Không** xin bypass soi TLS nào; CA của bệnh viện sẽ được tin đúng chỗ (mục 2), không tắt kiểm chứng chỉ ở đâu.
- **Không** xin mạng cho `bv-app-01` hay máy nào trong vùng bệnh án: quillo cài và nâng cấp offline qua MFT (mục 3).
- Model AI tải ở văn phòng, mang vào trong bundle; Hugging Face không cần mở.
- Cần An ninh duyệt trước **18/11/2026** để team dữ liệu bắt đầu dựng connector tuần 23/11.

## 1. Đích cần đi tới

Tên miền đo ngày 04/11/2026 qua log proxy khi chạy đúng các lệnh của từng việc (CDN có thể đổi tên; xin xem log "từ chối"
của proxy cho `bv-build-01` trong tuần đầu để bổ sung).

| Tên miền | Cổng | Máy nguồn | Mục đích | Tần suất | Dung lượng | Thời hạn | Đề nghị | Lý do |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `registry-1.docker.io` | 443 | `bv-build-01` | API Docker Hub: kéo image gốc `python:3.12-slim` ghim digest | Vài lần/tuần | Vài KB/lần | 28/02/2027 | Soi + tin CA | Docker daemon đọc trust store hệ thống; đã thử chạy sau proxy soi TLS |
| `auth.docker.io` | 443 | `bv-build-01` | Lấy token ẩn danh trước khi kéo | Như trên | Vài KB | 28/02/2027 | Soi + tin CA | Như trên |
| `production.cloudfront.docker.com` | 443 | `bv-build-01` | CDN chứa layer image (Docker Hub chuyển hướng tới đây) | Như trên | ~50 MB/image | 28/02/2027 | Soi + tin CA | Như trên |
| `pypi.org` | 443 | `bv-build-01` (trong container lúc build) | Chỉ mục gói Python | Vài lần/tuần | Vài trăm KB | 28/02/2027 | Soi + tin CA | pip/requests cấu hình được CA (mục 2) |
| `files.pythonhosted.org` | 443 | `bv-build-01` | Tệp gói Python (wheel) | Vài lần/tuần | < 50 MB/lần | 28/02/2027 | Soi + tin CA | Như trên; requirements có hash ⇒ tệp đổi là cài lỗi |
| `huggingface.co`, `us.aws.cdn.hf.co` | 443 | — | Tải model `llm-medium` | — | ~1,1 GB | — | **Không xin** (offline) | Tải ở văn phòng, ghim sha256, đóng vào bundle; model đi cùng đường duyệt với bundle |

Không xin: `upload.pypi.org` (đăng gói), Docker Hub `push`, mọi tên miền khác. Proxy chỉ cho `GET`/`CONNECT` tới đúng các tên
trên là đủ.

## 2. Chỗ phải tin CA của bệnh viện

| # | Chỗ | Cơ chế | Ai làm | Kiểm |
| --- | --- | --- | --- | --- |
| 1 | Hệ điều hành `bv-build-01` | CA vào `/usr/local/share/ca-certificates/`, `update-ca-certificates`; curl, apt, Python hệ thống đọc `/etc/ssl/certs/ca-certificates.crt` | anh Phong | `curl https://pypi.org/simple/pip/` trả 200, không `-k` |
| 2 | Docker daemon | Drop-in systemd đặt `HTTP(S)_PROXY`/`NO_PROXY` cho `docker.service`; dockerd đọc trust store hệ thống **lúc khởi động** ⇒ restart sau bước 1 | anh Phong | `docker pull python:3.12.14-slim-bookworm@sha256:…` thành công |
| 3 | Trust store trong mỗi image connector | Container không thừa hưởng CA của máy: build copy CA của máy vào image và chạy `update-ca-certificates` (chỉ cho image dùng ở bệnh viện) | team dữ liệu, FDE hỗ trợ | `docker run … curl https://pypi.org` trong image |
| 4 | pip trong image | pip 25 trên Python 3.12 dùng trust store hệ thống của image (`truststore`); đặt thêm `PIP_CERT=/etc/ssl/certs/ca-certificates.crt` để không phụ thuộc phiên bản pip | team dữ liệu | Bước `pip install` của build thành công |
| 5 | Python `requests` trong image | Dùng `certifi`, **không** đọc trust store hệ thống ⇒ `REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt` | team dữ liệu | `docker run … python -c "import requests; requests.get('https://pypi.org')"` |
| 6 | Công cụ khác nếu dùng sau | Node: `NODE_EXTRA_CA_CERTS`; Java: `keytool -importcert` vào truststore của JRE trong image | người thêm công cụ | Báo FDE trước khi thêm |

Biến proxy cho bước build truyền bằng `--build-arg` (không lưu vào image); không đặt `ENV http_proxy` trong Dockerfile.

## 3. Vùng bệnh án: cài và nâng cấp offline

- `bv-app-01` không có cấu hình proxy, không tên miền nào được mở; quillo không gọi dịch vụ ngoài nào khi chạy.
- Mỗi bản (~1,1 GB, mỗi tháng): FDE gửi qua MFT một thư mục gồm bundle, binary compose ghim sha256, `install.sh`,
  `SHA256SUMS`; sha256 của chính `SHA256SUMS` FDE đọc qua điện thoại cho anh Phong.
- Anh Phong kiểm `sha256sum --strict -c SHA256SUMS` trước khi chạy gì; `install.sh` kiểm lại từng tệp theo `manifest.json`
  của bundle trước khi nạp image. Không khớp ⇒ không cài, gửi lại.
- Image connector do team dữ liệu dựng trên `bv-build-01` nếu cần chạy ở vùng bệnh án thì đi cùng đường đó
  (`docker save` + sha256), không kéo trực tiếp.

## 4. Hỗ trợ từ xa

Không đề xuất kênh mới. Khi có sự cố: anh Phong mở phiên trên công cụ họp/chia sẻ màn hình bệnh viện đang dùng, chính
anh Phong gõ lệnh theo hướng dẫn của FDE; phiên có ghi hình theo quy định bệnh viện, kết thúc là đóng. FDE không có tài
khoản trên máy bệnh viện. Không dùng đường hầm tự dựng (reverse SSH, ngrok, TeamViewer cài thêm). Thu thập log bằng script
support bundle đã loại bí mật (module 01) gửi qua MFT.

## 5. Rủi ro, thu hồi và cam kết

| Rủi ro | Giảm thiểu | Ai chấp nhận |
| --- | --- | --- |
| Image/gói độc hại từ Docker Hub/PyPI (chuỗi cung ứng) | Chỉ image chính thức ghim digest; requirements ghim phiên bản **kèm hash**; proxy vẫn soi nên An ninh thấy được nội dung | chị Hoa |
| Đưa dữ liệu ra ngoài qua tên miền được mở | Không mở tên miền upload (`upload.pypi.org`, push Docker Hub); `bv-build-01` không có dữ liệu bệnh án; proxy ghi log | chị Hoa |
| CA bệnh viện nằm trong image connector | Image chỉ dùng trong bệnh viện; không đẩy lên registry ngoài; ghi trong tài liệu image | anh Phong |
| CDN đổi tên miền làm build hỏng giữa chừng | Xem log từ chối tuần đầu; đề nghị bổ sung bằng ticket, không mở rộng wildcard | FDE |

Thu hồi: anh Phong đóng 5 tên miền ngày **28/02/2027** (hết hạn đề nghị); gia hạn phải có ticket mới. Nếu team dữ liệu
dừng dựng connector sớm hơn, FDE báo để đóng sớm.

Cam kết: không ai trong team (FDE, team dữ liệu theo hướng dẫn của FDE) tắt kiểm chứng chỉ: không `verify=False`,
`--trusted-host`, `PYTHONHTTPSVERIFY=0`, `curl -k`, `insecure-registries`. An ninh tự kiểm được bằng:

- `grep -rnE 'verify *= *False|trusted-host|PYTHONHTTPSVERIFY|--insecure|insecure-registries'` trên thư mục build và
  `/etc/docker/` của `bv-build-01`.
- Chạy mỗi image connector tới một endpoint HTTPS dùng chứng chỉ tự ký (vd. `openssl s_server` trên `bv-build-01`): phải lỗi
  `CERTIFICATE_VERIFY_FAILED`.

## 6. Câu hỏi cho IT/An ninh

1. `bv-build-01` đi proxy bằng tài khoản nào: proxy cho theo IP, hay cần tài khoản dịch vụ (không dùng tài khoản cá nhân)?
2. Proxy có giới hạn dung lượng một lần tải hay chặn HTTP/2 không (layer image ~50 MB, Hugging Face không cần)?
3. Bệnh viện có mirror apt nội bộ cho Ubuntu 20.04 không, hay `bv-build-01` cần thêm `archive.ubuntu.com`/
   `security.ubuntu.com` (HTTP, cổng 80) để vá bảo mật?
4. Ai ký duyệt và ai là đầu mối xem log "từ chối" của proxy trong tuần đầu?
