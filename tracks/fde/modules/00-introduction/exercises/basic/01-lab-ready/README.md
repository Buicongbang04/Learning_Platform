---
title: Lab sẵn sàng — boot "máy khách" đầu tiên
level: basic
services: []
files:
  - path: starter/lab_ready.sh
    note: 5 TODO, POSIX sh, chạy trong VM
  - path: tests/test_lab_ready.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - uv run pytest tracks/fde/modules/00-introduction/exercises/basic/01-lab-ready -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Chuẩn bị xong lab VM của track (KVM, QEMU, golden image `lab-open`) và viết script đầu tiên chạy **bên trong máy
khách**: một "phiếu lab sẵn sàng" năm dòng cho biết máy là gì, bạn là ai trên máy đó, và máy có những gì để cài sản phẩm.

## Đề bài

Làm `## 0. Cài đặt` của lý thuyết module trước: `/dev/kvm` đọc/ghi được, có `qemu-system-x86_64`, `qemu-img`, `ssh`, rồi
dựng golden image một lần:

```bash
nice -n 15 uv run python -m fdekit prepare lab-open
```

Lệnh in đường dẫn golden, kích thước và thời gian dựng (khoảng 1–5 phút lần đầu, chạy lại thì trả ngay).

Sau đó viết `starter/lab_ready.sh`. Test boot một VM `lab-open` mới (overlay trên golden, xoá khi xong), chép script vào
`/home/fde/lab_ready.sh` và chạy bằng `sh /home/fde/lab_ready.sh` với user `fde` qua SSH. Script phải in ra stdout
**đúng năm dòng** dạng `khoá=giá_trị`, theo thứ tự:

| Khoá | Giá trị |
| --- | --- |
| `os` | `<ID>-<VERSION_ID>` lấy từ `/etc/os-release`, vd. `ubuntu-22.04` |
| `user` | tên user đang chạy script |
| `docker` | phiên bản Docker **server** (daemon) mà user này nói chuyện được, vd. `29.1.3`; không có hoặc không gọi được daemon thì `missing` |
| `compose` | `yes` nếu `docker compose` (plugin v2) chạy được, ngược lại `no` |
| `egress` | `open` nếu tới thẳng được `https://pypi.org/simple/` không qua proxy; `proxy` nếu chỉ tới được qua proxy khai trong biến môi trường; `none` nếu không đường nào |

Ràng buộc:

- POSIX `sh` (trên Ubuntu `sh` là `dash`, không có `[[ ]]`, mảng, `source`); không dùng `sudo`.
- Thoát mã `0` và xong trong 30 giây kể cả khi không có mạng (đặt timeout cho mọi lệnh mạng).
- Không in gì khác ra stdout; thông báo phụ (nếu có) ghi ra stderr.

Script này phải đúng trên **mọi** hồ sơ khách, không chỉ `lab-open`: đừng in hằng số. Test chạy script **hai lần** trong
cùng VM `lab-open`: lần đầu như máy vừa boot; rồi dừng Docker daemon (`sudo systemctl stop docker.socket docker.service`)
và chạy lại. Lần hai phải in `docker=missing` (client vẫn còn nhưng không có daemon trả lời), `compose=yes` (plugin
compose là phần của client, vẫn chạy `docker compose version` được), còn `os`, `user`, `egress` giữ nguyên. Bạn sẽ dùng
lại ý tưởng này ở module 01 trên máy `hospital` và `bank`.

Xong bài, kiểm không còn VM hay tệp tạm sót lại:

```bash
uv run python -m fdekit leftovers      # phải in "Không còn gì sót lại"
```

## Tiêu chí đạt

- `test_golden_image_is_prepared`: golden `lab-open` đã dựng (thiếu thì test skip kèm lệnh `prepare`; skip không tính là đạt).
- `test_lab_ready_reports_the_customer_machine`: cả hai lần chạy, script thoát `0` trong ≤30 s và in đúng năm khoá theo thứ
  tự trên; script treo quá 60 s thì test fail kèm thông báo.
- `os` khớp `ID`/`VERSION_ID` của VM, `user` là `fde`.
- `docker` bằng đúng phiên bản server mà `docker version --format '{{.Server.Version}}'` trả trong VM.
- `compose` khớp việc `docker compose version` chạy được hay không trong VM; `egress` là `open` trên `lab-open`
  (máy bạn không tới được `https://pypi.org/simple/` thì test skip kèm lý do, vì VM ra mạng qua máy bạn).
- Sau khi dừng daemon: `docker=missing`, `compose=yes`, `os`/`user`/`egress` như lần đầu.
- `uv run python -m fdekit leftovers` in "Không còn gì sót lại" sau khi chạy test.

## Gợi ý

### Gợi ý 1

`/etc/os-release` là tệp gán biến shell; đọc nó trong một subshell `( . /etc/os-release && echo "$ID" )` để không làm bẩn
biến của script. Docker client có `--format` theo Go template giống `docker inspect`.

### Gợi ý 2

Phân biệt "client có" và "daemon trả lời": `docker --version` chỉ là client, chạy được cả khi daemon chết hay user không
có quyền socket. Phiên bản server chỉ có khi client nói chuyện được với daemon.

### Gợi ý 3

Với `egress`, `curl -I --noproxy '*' --max-time 8` thử đường thẳng (`-I` chỉ gửi HEAD: trang `/simple/` của PyPI nặng
~48 MB, bạn chỉ cần biết có tới được không); đường qua proxy thì lấy proxy từ `HTTPS_PROXY`/`https_proxy`.
Proxy có TLS inspection sẽ làm HTTPS lỗi chứng chỉ dù mạng vẫn đi được: thử qua proxy bằng URL `http://` để tách "có
đường" khỏi "có trust CA" (chuyện CA là của module 03).
