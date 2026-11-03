---
title: Hiện trường — support bundle không ra ở ngân hàng
level: intermediate
services: []
files:
  - path: starter/support_bundle.sh
    note: Script của đồng nghiệp, đang dùng ở nhiều khách
  - path: tests/test_support_bundle.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - nice -n 15 uv run python -m fdekit prepare bank
  - uv run pytest tracks/fde/modules/01-site-survey/exercises/intermediate/01-support-bundle -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Sửa một công cụ thu thập chẩn đoán đang "chạy tốt ở mọi khách" để nó chạy được ở khách mới, khi bạn **không** ngồi trước
máy đó và mỗi vòng gửi đi gửi lại tốn một ngày.

## Đề bài

`starter/support_bundle.sh` là script đồng nghiệp viết từ năm ngoái: khách chạy `sh support_bundle.sh <thư mục>`, script
gom thông tin máy vào `<thư mục>/support-bundle.tar.gz`, khách gửi lại tệp đó cho đội hỗ trợ. Nó đã chạy ở hơn chục khách
(máy lab `lab-open` của bạn cũng chạy được).

Tuần này ngân hàng (hồ sơ `bank`) chạy theo hướng dẫn. Anh Khoa bên vận hành gửi lại:

> Chào anh, em chạy đúng như hướng dẫn trên máy app01 thì ra thế này, không thấy tệp tar.gz nào:
>
> ```text
> [fde@app01 ~]$ sh support_bundle.sh /tmp/sb-out
> support_bundle.sh: line 9: lsb_release: command not found
> support_bundle.sh: line 10: lsb_release: command not found
> [fde@app01 ~]$ ls /tmp/sb-out
> support-bundle
> ```
>
> Mỗi lần chạy script mới bên em phải xin phê duyệt change, nên anh gửi bản sửa một lần cho đủ giúp em nhé.

Sửa `starter/support_bundle.sh` để **cùng một script** chạy được trên cả `lab-open` lẫn `bank`. Bundle phải có:

- Thư mục gốc `support-bundle/` (mọi tệp nằm trong đó), với các tệp **không rỗng**: `summary.json`, `os-release.txt`,
  `uname.txt`, `meminfo.txt`, `disk.txt`, `net.txt`, `dns.txt`, `listening.txt`, `runtime.txt`, `security.txt`,
  `kernel.txt`, `time.txt`, `limits.txt`. Một lệnh thu thập không chạy được trên máy này thì tệp tương ứng ghi lý do,
  không bỏ trống, và script vẫn đi tiếp.
- `summary.json` là object đúng 5 khoá:

| Khoá | Giá trị |
| --- | --- |
| `os` | `<ID>-<VERSION_ID>` từ `/etc/os-release`, vd. `rocky-8.10` |
| `kernel` | `uname -r` |
| `runtime` | `docker <phiên bản server>` nếu Docker daemon trả lời user này, ngược lại `podman <phiên bản>` nếu có Podman, không có thì `none` |
| `dns` | Danh sách (không trùng) địa chỉ DNS server **thật** máy dùng để phân giải, không phải stub resolver cục bộ `127.0.0.53` |
| `mem_kb` | `MemTotal` trong `/proc/meminfo` (số nguyên, kB) |

Ràng buộc: POSIX `sh`, chạy bằng user thường, thoát `0` trong 60 giây.

Test boot `lab-open` rồi `bank` (mỗi lần một VM, RAM chọn ngẫu nhiên 1024 hoặc 1280 MB), chạy
`sh /home/fde/support_bundle.sh /tmp/sb-out`, tải tarball về và so `summary.json` với số đo lại trong cùng VM.

## Tiêu chí đạt

- `test_bundle_from_lab_open_and_bank`: trên cả hai máy, script thoát `0` trong ≤60 s và tạo
  `/tmp/sb-out/support-bundle.tar.gz` chỉ chứa đường dẫn dưới `support-bundle/`.
- Đủ 13 tệp ở trên, không tệp nào rỗng.
- `summary.json` đúng 5 khoá; `os`, `kernel`, `runtime`, `mem_kb` khớp máy; `dns` là danh sách, không chứa `127.0.0.53`,
  và đúng tập DNS server thật của máy.

## Gợi ý

### Gợi ý 1

Output khách gửi chỉ cho thấy chỗ **đầu tiên** script dừng. Hãy giả định phía sau còn nữa và tìm hết trước khi gửi bản
sửa: chạy test chỉ là cách bạn kiểm tra, ở hiện trường thật bạn không có VM của khách.

### Gợi ý 2

Đi từng dòng và hỏi ba câu: lệnh này có trong bản cài tối thiểu của distro kia không; nó có cần quyền mà user này không
có không; nó có giả định một dịch vụ hệ thống đang chạy không. Bảng ở phần 3 lý thuyết so Ubuntu với Rocky.

### Gợi ý 3

Không phải chỗ hỏng nào cũng in ra màn hình: để ý những dòng chuyển stderr vào tệp.
