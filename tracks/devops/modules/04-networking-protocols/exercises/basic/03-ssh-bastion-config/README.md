---
title: ssh_config cho bastion - ProxyJump, không agent forwarding, thứ tự Host
level: basic
services: []
files:
  - path: starter/ssh_config
    note: Cấu hình cũ có lỗi, viết lại
  - path: tests/test_ssh_config.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/04-networking-protocols/exercises/basic/03-ssh-bastion-config -q
---

## Mục tiêu

Viết cấu hình SSH client cho một hạ tầng có bastion mà vẫn an toàn khi bastion bị chiếm: không mang agent theo, không bỏ
kiểm host key, mỗi đích chỉ nhận đúng khoá của nó. Hiểu quy tắc "giá trị đầu tiên thắng" của `ssh_config`, nguồn gốc của
rất nhiều cấu hình "viết đúng mà không ăn".

## Đề bài

Team vận hành Olist Shop dùng chung `starter/ssh_config`. Tuần trước bastion bị chiếm qua một lỗ hổng, và kẻ tấn công
dùng agent được forward của một kỹ sư để đăng nhập vào `db-primary`. Cấu hình hiện tại còn tắt kiểm host key và cho mọi
host dùng `root`. Viết lại tệp để `ssh -G -F starter/ssh_config <host>` (in cấu hình cuối cùng sau khi áp mọi khối `Host`,
không kết nối mạng) cho đúng các giá trị sau.

Hạ tầng:

| Host gõ trên dòng lệnh | Kết nối tới | User | Cổng | Đi qua | Khoá (chỉ khoá này, `IdentitiesOnly yes`) |
| --- | --- | --- | --- | --- | --- |
| `bastion` | `bastion.olist-shop.com.br` | `ops` | 2222 | Trực tiếp | `~/.ssh/olist_ops_ed25519` |
| `app-<gì cũng được>` | `<tên gõ vào>.internal.olist-shop.com.br` | `deploy` | 22 | `ProxyJump bastion` | `~/.ssh/olist_ops_ed25519` |
| `db-<gì cũng được>` | `<tên gõ vào>.internal.olist-shop.com.br` | `dba` | 22 | `ProxyJump bastion` | `~/.ssh/olist_ops_ed25519` |
| `github.com` | `github.com` | `git` | 22 | Trực tiếp | `~/.ssh/github_ed25519` |
| Host khác bất kỳ | Chính tên đó | Không quy định | Không quy định | Trực tiếp | Không được nhận `olist_ops_ed25519` hay `github_ed25519` |

Với **mọi** host (kể cả host lạ), output của `ssh -G` phải có:

| Khoá trong `ssh -G` | Giá trị chấp nhận |
| --- | --- |
| `forwardagent` | `no` |
| `forwardx11` | `no` |
| `passwordauthentication` | `no` |
| `stricthostkeychecking` | `yes` (một số bản in `true`) hoặc `accept-new` |
| `userknownhostsfile` | Không có đường dẫn nào là `/dev/null` |
| `serveraliveinterval` | Số nguyên 15..60 |
| `serveralivecountmax` | Số nguyên 2..5 |
| `controlmaster` | `auto` |
| `controlpath` | Nằm trong `~/.ssh/` và kết thúc bằng `%C` (tuỳ phiên bản OpenSSH, `ssh -G` in nguyên `%C` hoặc đã mở rộng thành 40 ký tự hex; cả hai đều được chấp nhận) |
| `controlpersist` | 60..1800 giây (viết `10m` thì `ssh -G` in `600`) |
| `proxycommand` | Không có, hoặc `none`: dùng `ProxyJump`, không dùng `ProxyCommand` |
| `proxyjump` | `bastion` cho `app-*` và `db-*`; không có (hoặc `none`) cho mọi host khác, **kể cả chính `bastion`** |

Không dùng `Match exec`. Test copy tệp của bạn vào thư mục tạm và chạy `ssh -G -F <tệp> <host>` cho `bastion`, `app-1`,
`app-17`, `db-primary`, `db-replica-2`, `github.com`, `partner.example.org` trong sandbox bubblewrap (thiếu `bwrap` thì
skip; `Match exec` hay `Include` có thể chạy lệnh hay đọc tệp khi phân tích cấu hình). `-F` làm ssh bỏ qua cả
`/etc/ssh/ssh_config` lẫn `~/.ssh/config` của bạn, nên cấu hình riêng trên máy không ảnh hưởng. Thiếu `ssh` hoặc
OpenSSH cũ hơn 8.0 thì skip. Một test nữa chạy cùng phép kiểm trên bản gốc của tệp (`tests/fixtures/ssh_config.original`)
và đòi phép kiểm bắt được các lỗi đã biết của nó, để chứng minh test không cho qua cấu hình cũ.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/04-networking-protocols/exercises/basic/03-ssh-bastion-config -q` pass.
- Giải thích được vì sao `ProxyJump` an toàn hơn `ForwardAgent yes` khi bastion bị chiếm: với ProxyJump, bastion chỉ
  chuyển tiếp một luồng TCP đã mã hoá đầu-cuối; với agent forwarding, root trên bastion dùng được socket agent của bạn
  trong suốt phiên.
- Nói được vì sao khối `Host *` đặt **đầu** tệp làm mọi khối sau mất tác dụng với các tuỳ chọn nó đã đặt.

## Gợi ý

### Gợi ý 1

`ssh` đọc cấu hình từ trên xuống và với mỗi tuỳ chọn, **giá trị đầu tiên tìm thấy thắng** (trừ `IdentityFile`,
`LocalForward`... được cộng dồn). Vì vậy khối cụ thể đặt trước, `Host *` đặt cuối làm giá trị mặc định. Một khối có thể
liệt kê nhiều mẫu: `Host app-* db-*`.

### Gợi ý 2

`db-*` vừa khớp khối riêng (user `dba`) vừa khớp khối chung với `app-*` (user `deploy`): khối riêng phải đứng trước.
`ssh -G -F starter/ssh_config db-primary | grep -E '^(user|proxyjump|identityfile) '` cho bạn thấy ngay kết quả,
không cần tới test.
