# Lời giải: Installer chạy lại bao nhiêu lần cũng được

Lời giải ở `install.sh` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/intermediate/01-idempotent-installer -q
```

Đo 2026-11-04: cả bài 78 s (boot `lab-open` ~10 s, chờ rollback 60 s là phần lớn còn lại).

## Cấu trúc

```text
/opt/beacon/
  current -> releases/1.1.0        (symlink, đổi bằng ln -sfn + mv -T)
  releases/1.0.0/                  (bản trước, giữ để quay về)
  releases/1.1.0/                  (manifest.json + app/ config/ systemd/ models/)
  releases/.1.2.0.partial/         (chỉ tồn tại trong lúc giải nén, bị xoá bởi trap EXIT)
/etc/beacon/beacon.env              (của khách sau lần cài đầu: không bao giờ ghi đè)
/etc/systemd/system/beacon.service  (chỉ ghi khi khác bản trong bundle, kèm daemon-reload)
/var/log/beacon/install.log
```

## Luồng

1. **Preflight**: root, có bundle, có `python3 tar systemctl useradd df`, máy chạy systemd. Đọc riêng `manifest.json`
   (`--occurrence=1` dừng ngay khi thấy, không đọc hết tar vài GB), kiểm tên sản phẩm, dạng version, đường dẫn an toàn.
2. **Đường tắt idempotent**: manifest trong bundle **giống từng byte** manifest của release đang là `current`, unit giống,
   config có, user có, dịch vụ `enabled` + `active` + `/healthz` đúng version ⇒ ghi `unchanged`, thoát `0`. Không có lệnh
   ghi nào chạy trước điểm này.
3. **Chuẩn bị release** (chỉ khi chưa có đúng release đó): kiểm chỗ trống (tổng `size` + 5% + 64 MiB), giải nén vào
   `releases/.<v>.partial` với `--no-same-owner --no-same-permissions`, kiểm từng tệp theo manifest (thiếu, thừa, sai
   sha256/size), rồi `mv -T` thành `releases/<v>`.
4. **Áp cấu hình không đổi bản**: user hệ thống, env chỉ khi chưa có. Chép unit đang dùng sang thư mục tạm để còn đường
   quay về.
5. **Chuyển + xác minh trong một hàm `activate`** gọi dưới `if`: unit mới (chỉ khi khác) + `daemon-reload`, `enable`, đổi
   `current`, `restart`, chờ `/healthz` đúng version 60 s; mỗi lệnh `|| return 1`. Trong ngữ cảnh `if`, `set -e` không
   còn tác dụng, nên không lệnh nào được phép lỗi im lặng. Đạt ⇒ dọn release cũ (giữ bản hiện tại + bản trước),
   `installed`. **Bất kỳ** bước nào lỗi (unit không nạp được, `restart` lỗi, health quá giờ) ⇒ `rollback`: trả unit cũ,
   `daemon-reload`, trỏ `current` về bản trước, xoá release vừa giải nén ở lần chạy này (máy có thể có đĩa nhỏ), restart,
   chờ bản cũ khoẻ ⇒ `rolled-back`, thoát 1. Bản cũ cũng không lên ⇒ `failed`, log nói rõ cần người xem.
6. **Log**: mọi thông báo vào stderr và log; dòng cuối mỗi lần chạy do `finish` ghi, kể cả khi `die`.

## Những chi tiết hay sai

| Chi tiết | Vì sao |
| --- | --- |
| Kiểm sha256 **trước** khi dừng dịch vụ | Bundle hỏng phát hiện sau khi đã `systemctl stop` là downtime không cần thiết |
| Không ghi đè `/etc/beacon/beacon.env` | Đó là cấu hình của khách. Muốn đưa khoá mới vào thì ghi `beacon.env.new` và báo trong log, như dpkg làm với conffile |
| `--no-same-owner` | Tar dựng trên máy khác có uid/gid lạ; chạy bằng root mà giữ owner thì tệp thuộc về một user ngẫu nhiên trên máy khách |
| Health check gọi `127.0.0.1` với `ProxyHandler({})` | Máy khách có `http_proxy` trong môi trường (bệnh viện): gọi localhost qua proxy là lỗi kinh điển |
| Thư mục tạm cạnh chỗ cài | `mv` trong cùng filesystem là đổi tên nguyên tử, không chép lại dữ liệu |
| Đọc cổng từ env của khách | Khách đổi `BEACON_PORT` thì health check vẫn đúng |
| `trap cleanup EXIT` | Ctrl-C hay `die` giữa chừng không để lại `.partial` hay thư mục tạm |
| Unit được ghi trong `activate`, không trước đó | Ghi unit mới rồi `daemon-reload` *trước* khi có đường quay về là cách để rollback trả mã cũ mà chạy bằng unit mới (lỗi) |
| `set -e` không phải cơ chế rollback | Lệnh lỗi sau khi đã đổi `current` mà thoát thẳng bằng `set -e` là bỏ máy ở trạng thái nửa cũ nửa mới, đúng lỗi phần 4 của README module cảnh báo |

## Không làm trong lời giải (nên nói trong tài liệu bàn giao)

- Khoá chạy song song (`flock /run/beacon-install.lock`): hai người cùng chạy installer là chuyện có thật.
- Migration dữ liệu khi lên version: rollback mã dễ, rollback **schema** thì không (xem README module, phần versioning).
- Gỡ cài (`uninstall.sh`): khách nào cũng hỏi, trả lời "xoá `/opt/beacon`" là chưa đủ (user, unit, log, dữ liệu).
