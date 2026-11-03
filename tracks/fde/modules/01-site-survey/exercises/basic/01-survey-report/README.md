---
title: Báo cáo survey máy khách (JSON 13 trường)
level: basic
services: []
files:
  - path: starter/site_survey.sh
    note: 6 TODO, POSIX sh, chạy trong VM với user thường
  - path: schema.json
    note: JSON Schema của báo cáo (không sửa)
  - path: tests/test_site_survey.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare hospital
  - nice -n 15 uv run python -m fdekit prepare bank
  - uv run pytest tracks/fde/modules/01-site-survey/exercises/basic/01-survey-report -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Viết script khảo sát mà bạn có thể gửi cho **bất kỳ** khách nào: chạy bằng user thường, không cần root, không cần mạng,
trên cả Ubuntu 20.04 lẫn Rocky Linux 8, và trả về một báo cáo máy đọc được để đưa thẳng vào preflight (bài 02).

## Đề bài

Viết `starter/site_survey.sh`. Test boot máy khách `hospital` rồi `bank` (mỗi lần một VM), chép script vào
`/home/fde/site_survey.sh` và chạy `sh /home/fde/site_survey.sh` với user `fde` qua SSH. Script in ra stdout **đúng một
object JSON** hợp lệ theo `schema.json`, gồm đúng 13 khoá sau (không thêm, không thiếu):

| Khoá | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `os_id` | chuỗi | `ID` trong `/etc/os-release`, vd. `ubuntu`, `rocky` |
| `os_version` | chuỗi | `VERSION_ID` trong `/etc/os-release`, vd. `20.04`, `8.10` |
| `kernel_major` | chuỗi | Hai thành phần đầu của `uname -r`, vd. `5.4` |
| `glibc` | chuỗi | Phiên bản glibc dạng `2.31` |
| `cpus` | số nguyên | Số CPU tiến trình dùng được |
| `mem_mb` | số nguyên | `MemTotal` trong `/proc/meminfo`, đổi ra MiB (chia 1024, bỏ phần lẻ) |
| `disk_free_gb_max` | số | Dung lượng còn trống **cho user thường** trên filesystem chứa `/`, đơn vị GiB, làm tròn 1 chữ số thập phân |
| `gpu` | chuỗi hoặc `null` | Tên GPU NVIDIA nếu có, không có thì `null` |
| `proxy_url` | chuỗi hoặc `null` | Proxy HTTPS khách cấu hình cho user (biến môi trường hoặc `/etc/environment`), không có thì `null` |
| `sudo` | boolean | `true` nếu user chạy được `sudo` **không cần mật khẩu** |
| `selinux` | chuỗi | `enforcing`, `permissive`, `disabled`, hoặc `n/a` khi máy không có SELinux |
| `runtime` | chuỗi hoặc `null` | `docker` hoặc `podman` (cái nào có lệnh trên máy; có cả hai thì `docker`), không có thì `null` |
| `egress` | chuỗi | `open`, `proxy` hoặc `none`, cùng định nghĩa với bài `01-lab-ready` của module 00 |

Tên khoá trùng với `fdekit.PROFILES[<hồ sơ>].facts`. Riêng `disk_free_gb_max`: trong hồ sơ đó là **cận trên** cho mọi
VM boot từ golden; trong báo cáo của bạn là con số **đo được**, nên phải nhỏ hơn hoặc bằng cận trên.

Ràng buộc:

- POSIX `sh` (trên Ubuntu `sh` là `dash`); không gọi `sudo` ngoài phép thử `sudo -n` cho khoá `sudo`; không ghi tệp
  ngoài `/tmp`.
- Máy khách không chắc có `python3`, `jq`: JSON phải được tạo bằng shell. Starter cho sẵn hàm `json_string`.
- Thoát mã `0` trong 30 giây kể cả khi không có mạng; không in gì khác ra stdout (thông báo phụ ra stderr).

Test không chỉ so với hồ sơ: nó đo lại "sự thật" ngay trong cùng VM bằng lệnh của chính nó, và **đổi máy** giữa hai lần
chạy. Trên `hospital` (boot với RAM khác mặc định): chạy lần một; rồi IT "gỡ proxy" khỏi `/etc/environment` và một tệp
1 GiB được ghi vào đĩa; chạy lần hai. In hằng số sẽ không qua.

## Tiêu chí đạt

- `test_survey_on_hospital_before_and_after_it_changes`, `test_survey_on_bank`: script thoát `0` trong ≤30 s, stdout là
  JSON khớp `schema.json` (treo quá 60 s thì test fail kèm thông báo).
- `os_id`, `os_version`, `glibc`, `kernel_major` khớp máy và hồ sơ; `cpus` bằng `nproc`.
- `mem_mb` lệch không quá 1 so với `MemTotal` / 1024 của chính VM đó; trên `bank` (RAM mặc định 2048 MB) nằm trong
  80–100% của `facts["mem_mb"]`.
- `disk_free_gb_max` lệch không quá 0,15 GiB so với cột "Available" của `df -P -k /` và không vượt cận trên của hồ sơ; sau
  khi ghi 1 GiB, giảm ít nhất 0,8.
- `gpu` là `null`; `sudo`, `selinux`, `runtime` bằng giá trị trong `facts`.
- `hospital` lần một: `proxy_url` = `http://10.0.2.100:3128`, `egress` = `proxy`. Lần hai (đã gỡ proxy): `proxy_url` =
  `null`, `egress` = `none`. `bank`: `proxy_url` = `null`, `egress` = `none`.

## Gợi ý

### Gợi ý 1

Mỗi trường có ít nhất hai nguồn; chọn nguồn có trên **cả hai** họ distro và không cần root. Phần 3 của lý thuyết có bảng
lệnh. Chạy thử từng lệnh trên VM trước khi ghép vào script: cuối phần 3 có đoạn Python mười dòng mở
`fdekit.customer_site("bank")` và in kết quả `s.vm.ssh("...")`.

### Gợi ý 2

`awk` dùng dấu thập phân theo locale. Trên máy khách đặt locale tiếng Việt hay tiếng Đức, `printf "%.1f"` có thể in `6,0`
và JSON hỏng. Cố định locale ở đầu script.

### Gợi ý 3

`set -e` và lệnh dò thất bại là cặp nguy hiểm: thiếu `getenforce` trên Ubuntu, thiếu `docker` trên Rocky, `sudo -n`
trả mã khác 0 khi không có quyền. Mỗi lệnh dò phải nằm trong `if` hoặc có `||`.
