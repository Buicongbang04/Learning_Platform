# Lời giải: cài quillo ở khách air-gapped từ "USB"

## Khảo sát trước (lawfirm-staging, 2026-11-04)

| Hỏi | Thấy | Hệ quả |
| --- | --- | --- |
| `docker compose version` | `docker: unknown command: docker compose` | Gói `docker.io` của Ubuntu không kèm plugin; máy không có mạng để `apt install docker-compose-v2` ⇒ mang binary compose độc lập |
| `docker push 10.0.2.101:5000/…` | `http: server gave HTTP response to HTTPS client` | Registry HTTP chưa khai `insecure-registries` (bài basic 02) |
| `python3 --version` | 3.10.12 | `release.py verify` của công ty dùng `hashlib.file_digest` (3.11+) ⇒ không chạy được ở khách; kiểm bằng `sha256sum` + script tương thích 3.10 |
| `curl -I https://registry-1.docker.io` | `curl: (28) Resolving timed out` (không DNS) | Mọi image phải từ bundle → registry nội bộ |
| `ss -tlnp`, forward của lab | cổng forward vào `10.0.2.15` | `QUILLO_BIND=0.0.0.0` trong VM (README sản phẩm) |

## USB

```text
usb/
├── quillo-1.0.0.tar          bản phát hành, giữ nguyên byte
├── tools/docker-compose      compose v5.6.1 linux/amd64, sha256 47737f42… (đã kiểm khi đóng gói)
├── install.sh
└── SHA256SUMS                sha256 của ba tệp trên
```

`pack_usb.sh` kiểm sha256 của compose với giá trị ghim **trước** khi chép (binary sai mà đã qua cổng của khách thì không
sửa được tại chỗ), kiểm bundle có `quillo-1.0.0/manifest.json`, từ chối thư mục USB không rỗng, rồi in sha256 của chính
`SHA256SUMS` để gửi cho IT qua kênh khác (email/điện thoại): `SHA256SUMS` nằm trên USB nên kẻ sửa được USB cũng sửa được
nó; một chuỗi 64 ký tự đọc qua điện thoại thì không.

## `install.sh`: bảy bước, toàn vẹn trước tiên

1. `sha256sum --strict -c SHA256SUMS`: bắt chép hỏng mà không cần giải nén (1,1 GB ~3 s). Sai ⇒ dừng trước mọi thay đổi.
   Đo: bundle hỏng một byte bị từ chối sau 5,6–8,1 s, registry rỗng, không image, không container.
2. Preflight: lệnh cần có, Docker đang chạy, chỗ trống ở `/opt` và `/var/lib/docker` (≈3× kích thước bundle), registry
   trả lời `/v2/`.
3. Giải nén vào `/opt/quillo/releases/.1.0.0.partial`, kiểm **mọi** tệp theo `manifest.json` (thiếu, thừa, sai sha) bằng
   Python tương thích 3.10, rồi `mv -T` thành `releases/1.0.0`. Lớp này bắt bundle khác bản phát hành dù USB "khớp": test
   viết lại `SHA256SUMS` cho khớp một bundle đã bị sửa, installer vẫn dừng ở đây (đo 8,2–11,4 s), xoá `.partial`, registry rỗng.
   Chạy lại khi `releases/1.0.0` đã có: kiểm lại cây đó theo manifest (ai đó có thể đã sửa tay), không tin "đã có là đúng".
   Vì vậy cây release chỉ chứa đúng các tệp của bundle: tệp riêng của site (`compose.site.yaml`) nằm ở
   `/opt/quillo/site/1.0.0/`, thư mục `inbox` ở `/opt/quillo/data/inbox` (chồng `volumes:` của `worker` trong
   `compose.site.yaml`).
4. Cài compose vào `/usr/local/lib/docker/cli-plugins/docker-compose` (chỉ khi sha khác), `docker compose version`.
5. Thêm `10.0.2.101:5000` vào `insecure-registries`, giữ mọi khoá khác, ghi nguyên tử (tệp tạm cùng thư mục + `os.replace`,
   giữ bản `.bak`), restart Docker chỉ khi đổi. Không có `live-restore` thì restart dừng **mọi** container trên máy:
   installer in cảnh báo và ghi một dòng `warning` vào log; ở máy đang chạy dịch vụ khác, làm bước này trong cửa sổ bảo trì.
6. `docker load` từng `images/*.tar`, đọc tên từ `Loaded image:`, bỏ tên registry gốc (`ghcr.io/…` → `ggml-org/…`),
   `docker tag` + `docker push` vào `10.0.2.101:5000/…`.
7. Cấu hình ở `/etc/quillo/quillo.env` (0600, sinh một lần: `QUILLO_ADMIN_TOKEN`, `QUILLO_DB_PASSWORD` bằng
   `openssl rand -hex 24`, `QUILLO_BIND=0.0.0.0`); `compose.site.yaml` (sinh từ `docker compose config --format json`) đặt
   `image:` của từng dịch vụ sang registry nội bộ và chuyển `inbox` ra ngoài cây release, chồng lên `compose.yaml` gốc bằng
   `-f compose.yaml -f compose.site.yaml` (không sửa tệp có trong manifest);
   `docker compose -p quillo up -d --wait`, `curl /healthz`, ghi một dòng log.

Bí mật **không** đi trên USB: USB qua tay nhiều người và máy quét; mật khẩu sinh tại chỗ, chỉ nằm trên máy khách.

## Số đo (2026-11-04, laptop 16 core, NVMe, VM 5120 MB)

| Bước | Thời gian |
| --- | --- |
| `pack_usb.sh` (chép 1,1 GB trong `/var/tmp`) | 1,7 s |
| Boot `customer_site("lawfirm-staging")` + registry | 15,8 s |
| "Cắm USB" (`scp` 1,16 GB vào VM) | 4,9 s |
| `install.sh` với bundle hỏng (dừng ở bước 1) | 5,6–8,1 s |
| `install.sh` với bundle bị sửa + `SHA256SUMS` viết lại (dừng ở bước 3) | 8,2–11,4 s |
| `install.sh` thật (kiểm, giải nén, kiểm manifest, load 3 image, push qua registry nội bộ, compose up, healthz) | 63,8–79,6 s |
| **Cả bài** (ba lần đo, máy đang chạy việc khác) | **94,2–146,3 s** |
| Chạy lại `install.sh` lần hai (ngoài test): release đã có, compose không đổi gì | 16,1 s, thoát 0 |

Ngoài đời, USB 3.0 thực tế 50–150 MB/s, cổng chuyển tệp của khách có thể chậm hơn nhiều và còn chờ quét virus: lên lịch
chuyển trước ngày cài ít nhất một ngày, đừng để 1,1 GB nằm trên đường găng của buổi cài.

Ngoài phạm vi bài: nâng cấp và rollback (module 02 đã làm với `beacon`); installer này dừng và ghi log `failed` ở bước
lỗi, không tự quay về bản trước.

## Lỗi hay gặp

- Kiểm toàn vẹn **sau** `docker load`: image hỏng đã vào máy, có khi đã lên registry dùng chung, giờ phải dọn ở nhiều chỗ.
- `sed` sửa tên image trong `compose.yaml` của bundle: manifest không còn khớp, lần nâng cấp sau installer tưởng bundle
  bị sửa.
- Quên `QUILLO_BIND=0.0.0.0`: mọi thứ "healthy" trong VM, nhưng từ ngoài không vào được.
- Push bằng tên có registry gốc (`10.0.2.101:5000/ghcr.io/ggml-org/…`): registry chấp nhận, nhưng tên khó đọc và lệch quy
  ước đặt tên của khách; hỏi IT quy ước trước.
