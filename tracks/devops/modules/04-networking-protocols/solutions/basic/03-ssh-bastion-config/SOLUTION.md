# Lời giải: ssh_config cho bastion

Cấu hình đầy đủ ở `ssh_config` cạnh tệp này.

## Ba lỗi của cấu hình cũ

1. **`Host *` đứng đầu.** `ssh` lấy giá trị đầu tiên tìm thấy cho mỗi tuỳ chọn, nên `User root` của `Host *` thắng mọi
   `User` phía sau: `bastion` thành `root@bastion`, `app-1` thành `root@...`. Khối chung luôn đặt **cuối**.
2. **`ForwardAgent yes` + `ProxyCommand ssh -A`.** Agent forwarding tạo một socket trên bastion; root trên bastion (hoặc
   kẻ đã chiếm bastion) dùng socket đó để xác thực **bằng khoá của bạn** tới bất kỳ đâu trong lúc phiên còn mở. Khoá không
   bị lộ nhưng bị mượn. `ProxyJump` chỉ cho bastion chuyển tiếp một luồng TCP; phiên SSH tới `db-primary` được mã hoá và
   xác thực đầu-cuối từ laptop.
3. **`StrictHostKeyChecking no` + `UserKnownHostsFile /dev/null`.** Không bao giờ ghi nhớ và không bao giờ kiểm host key,
   tức là chấp nhận mọi kẻ đứng giữa. `accept-new` là thỏa hiệp hợp lý: tự nhận host mới, nhưng từ chối khi host key của
   một host đã biết thay đổi.

## Các lựa chọn còn lại

- **`IdentitiesOnly yes` + một `IdentityFile` cho mỗi nhóm host**: ssh không thử lần lượt mọi khoá trong agent (server
  thường cắt sau 6 lần thử, `Too many authentication failures`), và không tiết lộ cho một server lạ danh sách public key
  bạn có.
- **`ServerAliveInterval 30` / `ServerAliveCountMax 3`**: phát hiện kết nối chết sau khoảng 90 giây thay vì treo vô hạn
  sau NAT hay firewall cắt kết nối im lặng.
- **`ControlMaster auto` + `ControlPath ~/.ssh/cm-%C` + `ControlPersist 10m`**: các lệnh ssh/scp/rsync/Ansible sau dùng
  lại một kết nối, bỏ qua bắt tay (qua bastion là hai lần bắt tay). `%C` là hash của host, user, port, nên đường dẫn
  không quá dài cho socket Unix và không lộ tên host. Socket nằm trong `~/.ssh` (quyền 700), không trong `/tmp`.
- **`PasswordAuthentication no`** phía client: không bao giờ gõ mật khẩu vào một server giả mạo.

## Xa hơn trong production

- **SSH certificate** (`ssh-keygen -s ca_key -I id -n deploy -V +8h`): server tin CA (`TrustedUserCAKeys`), không cần phát
  `authorized_keys` tới từng máy; cert hết hạn sau vài giờ. Host certificate (`@cert-authority` trong `known_hosts`) giải
  quyết luôn câu hỏi "có tin host key này không".
- Thay bastion SSH bằng công cụ có audit và không mở cổng 22: AWS SSM Session Manager, Teleport, Tailscale SSH, GCP IAP.
- Phía server (`sshd_config`): `PermitRootLogin no`, `PasswordAuthentication no`, `AllowAgentForwarding no` trên bastion,
  `AllowTcpForwarding` chỉ bật ở bastion, `MaxAuthTries 3`. Kiểm bằng `sshd -T`.
