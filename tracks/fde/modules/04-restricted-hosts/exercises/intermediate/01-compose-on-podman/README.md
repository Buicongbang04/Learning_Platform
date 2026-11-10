---
title: "Hiện trường: compose trên Podman của công ty luật"
level: intermediate
services: []
files:
  - path: starter/deploy.sh
    note: Script triển khai của team, chạy tốt trên máy Docker; bạn sửa
  - path: starter/compose.yaml
    note: Compose của dịch vụ notice; bạn sửa
  - path: tests/test_compose_podman.py
    note: Không sửa (cũng là nơi dựng image notice từ BusyBox đã ghim)
run:
  - nice -n 15 uv run python -m fdekit prepare lawfirm-hardened
  - uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/intermediate/01-compose-on-podman -q -s
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Một dịch vụ nhỏ đóng bằng compose, chạy tốt trên mọi máy Docker của team, phải lên được ở máy siết bảo mật nhất của khách:
không root, không Docker, SELinux enforcing. Bạn phải làm nó chạy **mà không hạ một lớp bảo vệ nào** của khách, và chạy
bền: sống qua lúc bạn đăng xuất, triển khai lại được khi cấu hình đổi.

## Đề bài

Dịch vụ `notice` hiển thị bảng thông báo nội bộ: image `localhost/notice:1.0` đọc `/etc/notice/notice.conf` lúc khởi động
và phục vụ nội dung tệp đó qua HTTP cổng 8080 trong container. `starter/compose.yaml` publish cổng 18081 của máy và bind
mount thư mục `config/` cạnh compose vào `/etc/notice`. `starter/deploy.sh` là script team dùng trên máy Docker (đã chạy
tốt trên `lab-open`).

Máy `lawfirm-hardened` của công ty luật: Rocky Linux 8.10, SELinux enforcing, user `fde` **không** có sudo, không mạng,
Podman 4.9 rootless (không có Docker, IT không cho cài). Quy định của IT: được mang binary `docker-compose` v5.6.1 (đã
ghim sha256, phần `0. Cài đặt` của module 03) để chạy compose của sản phẩm; mọi thứ chạy dưới user `fde`.

IT đã thử triển khai theo hướng dẫn của team và báo lại:

> Container khởi động được rồi thoát ngay, log chỉ có một dòng `Permission denied`. Bên em không tắt SELinux đâu nhé.

Test dựng image `notice` từ BusyBox tĩnh đã ghim (phần `0. Cài đặt` của README module), boot `lawfirm-hardened` (2048 MB,
cổng 18081 của VM forward ra host), chép vào `/home/fde/notice-bundle/`: `notice-image.tar` (docker-archive), binary
`docker-compose` (đã `chmod 0755`), `compose.yaml`, `deploy.sh` của bạn, và ghi `config/notice.conf` với một dòng ngẫu
nhiên. Rồi:

1. Chạy `cd /tmp && sh /home/fde/notice-bundle/deploy.sh` (≤120 s).
2. Ghi một dòng ngẫu nhiên **khác** vào `config/notice.conf`, không mở phiên SSH nào trong 10 s, rồi chạy lại đúng lệnh trên
   trong một phiên SSH mới.

Đo trên máy của repo: cả bài ~40 s. Tự boot máy để điều tra: `with fdekit.customer_site("lawfirm-hardened",
memory_mb=2048, forwards=(18081,)) as s:` rồi `s.vm.ssh(...)`; image dựng bằng hàm `build_image` trong tệp test.

## Tiêu chí đạt

`test_compose_on_rootless_podman_lawfirm_hardened`:

- Hai lần `deploy.sh` đều thoát `0`.
- Sau mỗi lần, trong 30 s, `GET /` qua cổng 18081 của VM trả `200` với đúng nội dung `notice.conf` hiện tại.
- Có đúng một container đang chạy của dịch vụ `notice` trong project compose `notice` (nhãn
  `com.docker.compose.project=notice`, `com.docker.compose.service=notice`), và container đó:
  - chạy dưới SELinux type `container_t` (nhãn tiến trình của Podman), không `privileged`;
  - có `/etc/notice` là bind mount của `/home/fde/notice-bundle/config`.
- `getenforce` vẫn là `Enforcing`.
- Trong 10 s không có phiên SSH nào giữa hai lần triển khai, dịch vụ vẫn trả nội dung cũ.

## Gợi ý

### Gợi ý 1

Làm theo đúng từng bước của `deploy.sh` bằng tay trên VM và dừng ở lỗi **đầu tiên**. Mỗi lỗi kế tiếp chỉ hiện ra sau khi
lỗi trước được sửa; đừng đoán trước.

### Gợi ý 2

`docker-compose` chỉ là client của một API. Trên máy này, chương trình nào phục vụ API đó, nó nghe ở đâu, và nó có đang
chạy khi bạn không đăng nhập không?

### Gợi ý 3

Khi `Permission denied` xảy ra với một tệp mà quyền `rw` cho phép, quyền tệp không phải lớp kiểm soát duy nhất trên máy
này. Bạn không đọc được log audit ở đây; phần 4 của README module nói cách chẩn đoán khi đó.
