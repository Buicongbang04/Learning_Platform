# Lời giải: runbook cài ở khách air-gapped

## Hướng làm

1. Lấy các mốc cứng làm khung: cửa sổ 08:00–11:00, quay về bắt đầu muộn nhất 10:30, CAB cần runbook trước 5 ngày làm
   việc, MFT quét tới 24 giờ. Tính ngược ra lịch gửi tệp và hạn của từng mục checklist.
2. Đi lại bài intermediate 02 (staging) và liệt kê **mọi khác biệt** của production: registry HTTPS với CA nội bộ, Harbor
   cần tài khoản, bạn không có sudo, người dùng vào từ mạng văn phòng. Mỗi khác biệt thành một mục checklist, một bước,
   hoặc một câu hỏi.
3. Viết bước ngày cài dạng bảng: lệnh, "đúng thì thấy gì", thời gian (lấy từ số đo staging, ghi rõ nguồn), người làm.
   Kiểm tra đứng trước thay đổi. Đặt go/no-go ở chỗ sau đó việc quay về đắt hơn.
4. Viết phần quay về từ 10:30 ngược lại, kiểm tổng thời gian.
5. Đọc lại với con mắt của chị Lan: chỗ nào có bí mật, chỗ nào tắt bảo mật, chỗ nào tin thứ chưa kiểm.

Những chỗ hay sai: mốc go/no-go kiểu "nếu ổn thì tiếp"; quay về chỉ ghi "rollback"; dùng `insecure-registries` vì staging
đã dùng; đính kèm output `docker inspect` (có mật khẩu DB trong biến môi trường) vào bằng chứng; quên rằng Harbor cần đăng
nhập và tài khoản đẩy khác tài khoản kéo.

## Rubric (tự chấm, đạt đủ 10 mục)

| # | Bài mẫu đạt ở đâu |
| --- | --- |
| R1 | "Tóm tắt": 7 dòng, có điều kiện xong (bốn kiểm ở G3) và điều kiện quay về (10:30) |
| R2 | Mục 1: 14 mục, chia IT hạ tầng / An ninh / IT ứng dụng / FDE, mỗi mục có người xác nhận và hạn, đủ các chủ đề bắt buộc |
| R3 | Mục 2: gửi 01/12 (quét 24 h, dự phòng 03/12); sha256 của `SHA256SUMS` đọc qua điện thoại cho chị Lan; không khớp ⇒ không cài, gửi lại; GGUF có thể bị chặn nhầm ⇒ gửi trước sha256 để Security đưa vào danh sách cho phép |
| R4 | Mục 4: 9 bước, mỗi bước có lệnh, "đúng thì thấy", thời gian có nguồn đo, người làm; preflight và kiểm toàn vẹn đứng trước mọi thay đổi |
| R5 | Mục 4: G1 08:30, G2 09:30, G3 10:15, tiêu chí đo được (mã HTTP, tên/Id image, trạng thái dịch vụ) |
| R6 | Mục 5: bảng hoàn tác theo bước, 10:30 là mốc cứng, ~15 phút; chưa có dữ liệu khách nên `down -v` không mất gì của khách |
| R7 | Mục 3: CA vào `/etc/docker/certs.d/registry.minhan.internal/ca.crt` (không restart, không `insecure-registries`), đọc fingerprint với chị Lan qua điện thoại |
| R8 | Mục 6: mật khẩu DB/token sinh tại chỗ trong `/etc/quillo/quillo.env` 0600 root; token do chị Hạnh tự đọc trên máy khi đã tạm dừng chia sẻ màn hình; mật khẩu robot Harbor gõ qua `--password-stdin`, logout tài khoản đẩy |
| R9 | Mục 6: danh sách bằng chứng (log, `sha256sum -c`, `Id`/`RepoDigests` so với biên bản diễn tập, `/healthz`), loại trừ `.env`, `docker inspect`, `config.json`; anh Tuấn và chị Hạnh ký biên bản |
| R10 | Mục 7: 5 điều không làm, 4 câu hỏi còn mở |

Kiểm tổng thời gian: thời lượng các bước trong cửa sổ cộng dồn 80 phút (dự kiến xong ~10:00 nếu không trục trặc, mốc
G3 10:15), quay về ~15 phút bắt đầu muộn nhất 10:30 ⇒ xong trước 10:45, nằm trong cửa sổ.

---

## Bài mẫu

# Runbook: cài quillo 1.1.0 trên qa-prod-01 (Công ty luật Minh An)

Phiên bản runbook: 1.0 (27/11/2026) · Người viết: FDE … · Duyệt CAB: phiên 30/11/2026 · Cửa sổ: thứ Bảy 05/12/2026,
08:00–11:00

## Tóm tắt

- Cài `quillo` 1.1.0 (trợ lý hỏi đáp tài liệu, chạy hoàn toàn nội bộ) lên `qa-prod-01`, image lấy từ Harbor `vendors`.
- Thứ Bảy 05/12, 08:00–11:00. Anh Tuấn gõ lệnh sudo, FDE dẫn theo runbook qua chia sẻ màn hình, chị Hạnh nghiệm thu.
- Tệp vào qua MFT, gửi 01/12; chị Lan duyệt CA và sha256 trước 04/12.
- Xong khi: G3 đạt (`/healthz` 200 bản 1.1.0 từ mạng văn phòng, 5 dịch vụ chạy image từ Harbor, câu hỏi mẫu có trích
  dẫn).
- Quay về nếu 10:30 chưa qua G3: gỡ sạch như mục 5, máy trở lại trạng thái trước 08:00.
- Không có dữ liệu khách trong cửa sổ; 2 000 hợp đồng được nạp sau bàn giao.
- Không lệnh nào cần internet.

## 1. Checklist trước ngày cài

| # | Mục | Ai xác nhận | Hạn |
| --- | --- | --- | --- |
| 1 | MFT: giới hạn 2 GB/tệp (bundle 1,16 GB, compose 33 MB: đạt), thời gian quét tối đa, thư mục đến `/srv/mft-inbox/` | anh Tuấn | 25/11 |
| 2 | Harbor: địa chỉ `registry.minhan.internal`, project `vendors` đã tạo, quota ≥ 2 GB | anh Tuấn | 27/11 |
| 3 | Harbor: tài khoản robot **đẩy** (chỉ dùng trong cửa sổ, vô hiệu sau đó) và robot **kéo** (lâu dài, chỉ đọc `vendors`) | anh Tuấn, chị Lan | 01/12 |
| 4 | CA "Minh An Root CA" (PEM) gửi FDE; fingerprint SHA-256 đọc qua điện thoại | chị Lan | 01/12 |
| 5 | Docker `docker.io` 29 trên `qa-prod-01`; không có plugin compose (sẽ cài binary v5.6.1 từ USB, sha256 `47737f42…db8c0`) | anh Tuấn | 25/11 |
| 6 | Chỗ trống: `/opt` ≥ 4 GB, `/var/lib/docker` ≥ 4 GB (≈ 3× bundle); RAM trống ≥ 6 GB | anh Tuấn (`df -h`, `free -m` gửi lại) | 27/11 |
| 7 | Cổng `18080` trên IP `qa-prod-01` chưa dùng; tường lửa cho `10.20.0.0/16` → `18080` | anh Tuấn | 01/12 |
| 8 | DNS nội bộ phân giải `registry.minhan.internal` từ `qa-prod-01`; NTP đồng bộ (`timedatectl`: `System clock synchronized: yes`; lệch giờ làm hỏng kiểm chứng chỉ) | anh Tuấn | 27/11 |
| 9 | Snapshot VM `qa-prod-01` trước 08:00 thứ Bảy (phương án quay về cuối cùng) | anh Tuấn | 05/12 07:45 |
| 10 | Người liên hệ trong cửa sổ: anh Tuấn (sudo), chị Lan (chứng chỉ, gọi được 08:00–11:00), chị Hạnh (nghiệm thu) | chị Hạnh | 27/11 |
| 11 | Runbook nộp CAB | FDE | 27/11 |
| 12 | Diễn tập trên staging bằng đúng bundle và script sẽ mang đi, ghi thời gian từng bước | FDE | 30/11 |
| 13 | Tài liệu mẫu không nhạy cảm để kiểm hỏi đáp (`samples/hop-dong-mau.pdf`, có trong danh sách checksum) | FDE | 30/11 |
| 14 | Kênh giao token quản trị và người nhận (chị Hạnh) | chị Lan | 01/12 |

## 2. Chuyển giao và toàn vẹn

- Nội dung gửi qua MFT, một thư mục `quillo-1.1.0/`: `quillo-1.1.0.tar`, `tools/docker-compose`, `install.sh`,
  `samples/hop-dong-mau.pdf`, `SHA256SUMS` (sha256 của bốn tệp kia).
- Lịch: gửi **thứ Ba 01/12** (quét tối đa 24 h ⇒ đến trước thứ Tư). Thứ Tư 02/12 anh Tuấn chạy `sha256sum --strict -c
  SHA256SUMS` trong `/srv/mft-inbox/quillo-1.1.0/` và gửi lại output. Lỗi ⇒ gửi lại thứ Năm 03/12 (khe dự phòng). Thứ Sáu
  04/12 chưa có bản đúng ⇒ hoãn cửa sổ, báo CAB.
- Neo tin cậy: sha256 của chính `SHA256SUMS` FDE đọc qua **điện thoại** cho chị Lan (không gửi qua MFT hay email cùng
  tệp); chị Lan so với `sha256sum SHA256SUMS` trên máy.
- Không khớp (dù một tệp): không cài, không "thử xem sao", gửi lại từ bản gốc; ghi nhận vào biên bản.
- Máy quét có thể chặn nhầm hoặc quá hạn với tệp GGUF lớn (binary nén cao, không có chữ ký số). Gửi trước sha256 của từng
  model cho chị Lan (01/12) để Security đưa vào danh sách cho phép theo hash; nếu vẫn bị cách ly thì dùng khe 03/12.

## 3. Chứng chỉ và registry

- Harbor dùng chứng chỉ do "Minh An Root CA" cấp. Docker cần tin CA đó **cho đúng registry này**:
  `/etc/docker/certs.d/registry.minhan.internal/ca.crt`. Docker đọc thư mục này mỗi lần kết nối: không restart daemon,
  không đụng `daemon.json`, không đụng container khác trên máy.
- Không dùng `insecure-registries`, không tắt kiểm chứng chỉ ở đâu. Staging dùng `insecure-registries` vì registry staging là
  HTTP; production có TLS thì dùng TLS.
- CA cũng vào trust store hệ thống (`/usr/local/share/ca-certificates/minhan-root-ca.crt`, `update-ca-certificates`) để
  `curl` ở bước preflight kiểm được Harbor.
- Kiểm CA: `openssl x509 -in minhan-root-ca.pem -noout -subject -fingerprint -sha256`; FDE đọc fingerprint, chị Lan xác nhận
  qua điện thoại khớp với CA gốc của công ty.

## 4. Các bước ngày cài

Thời gian ước tính lấy từ diễn tập trên staging (mục 1, #12) cộng biên; staging đo: kiểm toàn vẹn 1,1 GB ~5 s, `install.sh`
từ đầu tới `/healthz` 64–80 s trên máy 2 CPU. Bước 0 làm trước cửa sổ và không thay đổi máy. Để gọn, `C` dưới đây là
`sudo docker compose -p quillo --project-directory /opt/quillo/current --env-file /etc/quillo/quillo.env -f
/opt/quillo/current/compose.yaml -f /opt/quillo/current/compose.site.yaml`.

| # | Giờ | Bước | Lệnh | Đúng thì thấy | Thời gian | Người |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 07:45 | Snapshot, mở cuộc gọi | (Hypervisor của khách) | Snapshot tên `qa-prod-01-pre-quillo-0512` | 15 phút | anh Tuấn |
| 1 | 08:00 | Preflight | `df -h /opt /var/lib/docker; free -m; docker version --format '{{.Server.Version}}'; ss -tlnp \| grep 18080; getent hosts registry.minhan.internal; timedatectl \| grep synchronized` | Đủ chỗ như #6; `29.x`; **không** có dòng 18080; có IP Harbor; `yes` | 10 phút | anh Tuấn |
| 2 | 08:10 | Toàn vẹn | `cd /srv/mft-inbox/quillo-1.1.0 && sha256sum SHA256SUMS && sha256sum --strict -c SHA256SUMS` | Dòng đầu khớp giá trị chị Lan giữ; mọi dòng `OK` | 5 phút | anh Tuấn, chị Lan |
| 3 | 08:15 | CA | `sudo install -D -m 0644 minhan-root-ca.pem /etc/docker/certs.d/registry.minhan.internal/ca.crt && sudo install -m 0644 minhan-root-ca.pem /usr/local/share/ca-certificates/minhan-root-ca.crt && sudo update-ca-certificates` | `1 added` | 5 phút | anh Tuấn |
| 4 | 08:20 | Harbor trả lời qua TLS | `curl -sS -o /dev/null -w '%{http_code}\n' https://registry.minhan.internal/v2/` | `401` (TLS đạt, cần đăng nhập); lỗi chứng chỉ ⇒ dừng ở G1 | 5 phút | anh Tuấn |
| **G1** | **08:30** | **Go/no-go 1** | | Bước 1–4 đều đúng. Không ⇒ dừng, máy chưa bị thay đổi gì ngoài CA (gỡ như mục 5) | | FDE, anh Tuấn |
| 5 | 08:30 | Đăng nhập robot đẩy | `sudo docker login registry.minhan.internal -u 'robot$vendors+push' --password-stdin` (anh Tuấn dán mật khẩu, không hiện trên màn hình chia sẻ) | `Login Succeeded` | 5 phút | anh Tuấn |
| 6 | 08:35 | Cài | `sudo QUILLO_REGISTRY=registry.minhan.internal/vendors bash install.sh` (bản production của script staging: preflight gọi `https://registry.minhan.internal/v2/`, bước khai registry chỉ kiểm `certs.d`, không sửa `daemon.json`; diễn tập #12 chạy đúng bản này) | Từng dòng `install: n/7`; kết thúc `xong: quillo 1.1.0`, mã 0 | 15 phút (staging 80 s, chừa cho push qua LAN) | anh Tuấn |
| 7 | 08:50 | Thu quyền đẩy | `sudo docker logout registry.minhan.internal`, rồi `sudo docker login … -u 'robot$vendors+pull' --password-stdin` | `Removing login credentials`, `Login Succeeded` | 5 phút | anh Tuấn |
| **G2** | **09:30** | **Go/no-go 2** | `C config --images`, rồi `sudo docker image inspect --format '{{.Id}} {{.RepoDigests}}'` từng image; Harbor UI | Mọi image dịch vụ dùng có tên `registry.minhan.internal/vendors/…`, digest trong `RepoDigests` có trên Harbor, `Id` khớp Id ghi trong biên bản diễn tập staging (cùng bundle đã kiểm theo `manifest.json` ở bước 6) | 10 phút | FDE |
| 8 | 09:40 | Kiểm từ mạng văn phòng | Từ máy chị Hạnh: `curl -sS http://qa-prod-01:18080/healthz` | `{"status":"ok","version":"1.1.0",…}` | 5 phút | chị Hạnh |
| 9 | 09:45 | Hỏi đáp mẫu | Nạp `samples/hop-dong-mau.pdf` qua UI, hỏi "Thời hạn hợp đồng là bao lâu?" | Câu trả lời có trích dẫn `[1]` trỏ đúng đoạn | 15 phút | chị Hạnh |
| **G3** | **10:15** | **Go/no-go 3 (xong)** | `C ps` | Bước 8, 9 đạt; 5 dịch vụ `running (healthy)`; G2 đạt | | chị Hạnh, FDE |

## 5. Quay về

Mốc cứng: **10:30** chưa qua G3 ⇒ quay về, không xin thêm giờ. Quay về mất ~15 phút (đã diễn tập trên staging).

| Đã làm tới | Hoàn tác |
| --- | --- |
| Bước 3–4 (CA) | `sudo rm /etc/docker/certs.d/registry.minhan.internal/ca.crt /usr/local/share/ca-certificates/minhan-root-ca.crt && sudo update-ca-certificates --fresh` (hoặc giữ lại nếu chị Lan đồng ý: CA của chính công ty) |
| Bước 5–7 (đăng nhập) | `sudo docker logout registry.minhan.internal`; anh Tuấn vô hiệu robot đẩy trên Harbor |
| Bước 6 (cài) | `imgs=$(C config --images)`, `C down -v`, `sudo docker image rm $imgs` (chỉ image của quillo, không đụng image khác trên máy), `sudo rm -rf /opt/quillo /etc/quillo /usr/local/lib/docker/cli-plugins/docker-compose` |
| Image trên Harbor | Giữ (không ảnh hưởng gì) hoặc anh Tuấn xoá trong project `vendors` |
| Mọi cách trên thất bại | Khôi phục snapshot `qa-prod-01-pre-quillo-0512` (anh Tuấn quyết, ~10 phút) |

Dữ liệu: trong cửa sổ chưa có dữ liệu khách; `down -v` chỉ xoá database rỗng vừa tạo và tài liệu mẫu. Quay về sau khi
khách đã nạp dữ liệu là quy trình khác (sao lưu volume trước), không thuộc runbook này.

## 6. Bí mật và bằng chứng bàn giao

Bí mật:

- `QUILLO_ADMIN_TOKEN`, `QUILLO_DB_PASSWORD` do `install.sh` sinh tại chỗ (`openssl rand -hex 24`) vào
  `/etc/quillo/quillo.env`, chủ root, quyền `0600`. Không có trên USB, trong runbook, trong log cài đặt.
- Token quản trị: anh Tuấn **tạm dừng chia sẻ màn hình** (FDE xác nhận không còn thấy màn hình), chạy
  `sudo grep QUILLO_ADMIN_TOKEN /etc/quillo/quillo.env` để chị Hạnh đọc tại chỗ, `clear`, rồi mới chia sẻ lại; chị Hạnh lưu
  token vào kho mật khẩu của công ty. FDE không thấy và không giữ bản nào.
- Mật khẩu robot Harbor: do anh Tuấn nhập qua `--password-stdin`; robot đẩy bị vô hiệu sau cửa sổ; robot kéo lưu trong
  `/root/.docker/config.json` (base64, không mã hoá: quyền `0600`, nêu trong câu hỏi mở).

Bằng chứng (thư mục `bangiao-quillo-0512/`, chị Hạnh giữ một bản):

- Output `sha256sum --strict -c SHA256SUMS` và sha256 của `SHA256SUMS`.
- `/var/log/quillo-install.log` (dòng `… 1.1.0 installed`).
- `C ps`, `Id` và `RepoDigests` của từng image, kèm biên bản diễn tập staging để so.
- `/healthz` từ mạng văn phòng, ảnh chụp câu hỏi mẫu có trích dẫn.
- **Không** đính kèm: `/etc/quillo/quillo.env`, `docker inspect` của container (biến môi trường chứa mật khẩu DB),
  `/root/.docker/config.json`.

Ký nhận: anh Tuấn (đã cài theo runbook), chị Hạnh (nghiệm thu G3), FDE.

## 7. Không làm và câu hỏi còn mở

Không làm:

- Không phát mạng từ điện thoại hay cắm USB 4G vào `qa-prod-01` để "tải nhanh" thứ còn thiếu.
- Không cắm laptop của FDE vào mạng khách; FDE chỉ xem qua chia sẻ màn hình.
- Không dùng `insecure-registries`, `curl -k`, `--insecure` hay bất kỳ cách tắt kiểm chứng chỉ nào.
- Không sửa tệp trong bundle tại chỗ (sha256 sẽ lệch manifest); thiếu gì thì quay về và gửi lại.
- Không kéo dài cửa sổ quá 10:30 để "gỡ nốt".

Câu hỏi còn mở (cần trả lời trước CAB 30/11):

1. Khách có reverse proxy/TLS sẵn (nginx, F5) để đặt trước cổng 18080 không? Nếu chưa, chấp nhận HTTP trong mạng
   `10.20.0.0/16` cho giai đoạn pilot có thời hạn?
2. Chính sách lưu thông tin đăng nhập registry trên máy chủ: chấp nhận `/root/.docker/config.json` hay cần credential
   helper?
3. Snapshot `qa-prod-01` giữ bao lâu sau cửa sổ, ai xoá?
4. Ai được nhận token quản trị lâu dài và quy trình xoay token (mỗi quý?) do bên nào làm?
