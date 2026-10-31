# Hướng làm: chọn distro và baseline cho đợt chuyển máy chủ Olist Shop

Bài Advanced không có một đáp án duy nhất. Hai lựa chọn đều bảo vệ được: **một distro họ RHEL cho mọi máy**, hoặc
**Ubuntu LTS cho đa số và một máy họ RHEL cho phần mềm đối soát**. Chọn Ubuntu cho cả máy đối soát thì không đạt
(vi phạm ràng buộc bắt buộc). Phần dưới gồm cách sắp ràng buộc, một ADR mẫu, các quyết định cần cân nhắc và rubric.

## Sắp ràng buộc

| Ràng buộc | Loại | Hệ quả |
| --- | --- | --- |
| Phần mềm đối soát chỉ chứng nhận RHEL 9 hoặc tương thích nhị phân | Bắt buộc (cho 1 máy) | Máy đó phải là RHEL, Rocky hoặc AlmaLinux 9 |
| PCI DSS 4.0: vá trong 30 ngày, audit, MAC, cấu hình chuẩn | Bắt buộc | Mọi phương án được nếu có bản vá kịp thời và có CIS benchmark (RHEL, Rocky, Alma, Ubuntu đều có) |
| Chạy ít nhất 5 năm không cài lại | Bắt buộc | Tính từ hôm nay (11/2026): loại Debian 13 (LTS tới 06/2030, chưa tới 4 năm), loại CentOS Stream (nhánh đi trước RHEL, vòng đời ngắn); Ubuntu 24.04 chỉ đạt nếu mua Ubuntu Pro, 26.04 LTS thì đạt |
| Team quen Ubuntu, role Ansible cho `apt` | Nên có | Cộng điểm Ubuntu; chuyển sang `dnf` tốn vài tuần |
| Ngân sách license hạn chế | Nên có | Rocky/Alma miễn phí; RHEL có gói developer miễn phí tới 16 máy nhưng không dùng cho production có hỗ trợ |
| Vá kernel không reboot | Nên có | Ubuntu Pro (Livepatch, miễn phí tới 5 máy cá nhân, trả phí cho doanh nghiệp), RHEL (kpatch kèm subscription), Rocky/Alma (cần dịch vụ bên thứ ba như TuxCare) |

## ADR mẫu

```markdown
# ADR: Chọn distro và baseline cho máy chủ Olist Shop

## 1. Bối cảnh

Bắt buộc, theo thứ tự: (1) phần mềm đối soát chỉ được hỗ trợ trên RHEL 9 hoặc bản tương thích nhị phân; (2) PCI DSS
4.0 trong 9 tháng: vá lỗ hổng nghiêm trọng trong 30 ngày, audit log, MAC, cấu hình chuẩn CIS; (3) vòng đời tối thiểu
5 năm không cài lại. Nên có: team 3 người, hai người quen Ubuntu; role Ansible viết cho apt; ngân sách license hạn
chế; hạn chế reboot vì phải xin lịch bảo trì. Phần lớn workload sẽ lên Kubernetes, VM còn lại là Postgres và bastion.

## 2. Phương án

| Distro và phiên bản | Vòng đời hỗ trợ | Cập nhật bảo mật | MAC (SELinux/AppArmor) | Chi phí và hỗ trợ | Điểm (1-5) |
| --- | --- | --- | --- | --- | --- |
| Rocky Linux 9 | Tới 05/2032 theo RHEL 9 | Errata theo RHEL, chậm hơn RHEL vài giờ tới vài ngày; dnf-automatic | SELinux enforcing mặc định, policy targeted | Miễn phí; hỗ trợ trả phí qua CIQ nếu cần | 4 |
| RHEL 9 | 10 năm, tới 05/2032 (thêm ELS) | Errata chính thức, Insights, kpatch | SELinux enforcing, CIS và DISA STIG có profile OpenSCAP | Subscription mỗi máy; hỗ trợ của Red Hat | 4 |
| Ubuntu 26.04 LTS | 5 năm chuẩn tới 2031, 10 năm với Ubuntu Pro | unattended-upgrades, USN; Livepatch với Ubuntu Pro | AppArmor mặc định | Miễn phí; Ubuntu Pro trả phí theo máy | 3 |
| Debian 13 | Khoảng 08/2028, LTS tới 06/2030 | debian-security, unattended-upgrades | AppArmor mặc định | Miễn phí, hỗ trợ cộng đồng | 2 |

## 3. Quyết định

Chọn: Rocky Linux 9 cho cả 8 VM

Rocky 9 thoả cả ba ràng buộc bắt buộc mà chỉ cần một distro: tương thích nhị phân RHEL 9 nên phần mềm đối soát được
hỗ trợ, có CIS benchmark và profile OpenSCAP để chứng minh cấu hình chuẩn cho PCI DSS, vòng đời tới 2032. Một distro
cho mọi máy nghĩa là một bộ role Ansible, một luồng vá, một bộ tài liệu cho người trực. Cái giá: viết lại role từ apt
sang dnf (ước 3 tuần) và đào tạo hai người quen Ubuntu về SELinux. Nếu nhà cung cấp đối soát đòi hỗ trợ có hợp
đồng, chuyển riêng máy đó sang RHEL 9 (tương thích, không đổi role).

## 4. Baseline

| Hạng mục | Cấu hình | Lý do |
| --- | --- | --- |
| SSH | Chỉ key ed25519, `PasswordAuthentication no`, `PermitRootLogin no`, chỉ nhận kết nối từ bastion | Chặn dò mật khẩu, mọi truy cập đi qua một điểm có log |
| Người dùng và sudo | Tài khoản cá nhân, nhóm `wheel` có sudo, không dùng tài khoản chung | Truy được ai làm gì (PCI DSS 8) |
| Firewall | firewalld (nftables) mặc định chặn, chỉ mở cổng của vai trò máy | Giảm bề mặt tấn công, phân vùng mạng |
| Cập nhật bảo mật | dnf-automatic áp bản vá security hằng ngày; kernel vá trong cửa sổ bảo trì 2 tuần một lần | Đạt vá trong 30 ngày mà không reboot bất ngờ |
| Đồng bộ giờ | chrony với 2 nguồn NTP nội bộ | Log và audit có thứ tự đúng, TLS và Kerberos cần giờ chuẩn |
| Audit | auditd với bộ luật CIS (đổi user, sudo, sửa /etc, nạp module) | Bằng chứng truy cập cho PCI DSS 10 |
| MAC | SELinux enforcing, không tắt; viết policy module khi cần thay vì `setenforce 0` | Giới hạn thiệt hại khi một service bị chiếm |
| Log | journald lưu bền (`Storage=persistent`), chuyển về máy log tập trung qua rsyslog TLS | Log không mất khi máy hỏng, giữ 1 năm theo PCI DSS |
| Kernel và sysctl | `kernel.kptr_restrict=2`, `net.ipv4.conf.all.rp_filter=1`, tắt IP forwarding trừ máy cần | Chặn rò địa chỉ kernel, giả mạo IP nguồn |
| Filesystem | `/tmp` và `/var/tmp` mount `nodev,nosuid,noexec`; `/var/log` phân vùng riêng | Chặn chạy mã từ thư mục tạm; log đầy không làm đầy hệ thống |
| Kiểm tra | OpenSCAP profile CIS Level 1 chạy hằng tuần, báo cáo vào ticket | Chứng minh liên tục, phát hiện drift |

## 5. Rủi ro và đánh đổi

- Rocky phụ thuộc mã nguồn RHEL; Red Hat đã hạn chế công bố mã nguồn từ 2023. Nếu Rocky chậm vá quá 30 ngày, chuyển
  sang RHEL (cùng tương thích, ít rủi ro chuyển đổi).
- Team chưa quen SELinux: rủi ro tắt SELinux "cho chạy được". Giảm bằng đào tạo và chặn `setenforce 0` trong review.
- Viết lại role Ansible mất khoảng 3 tuần, trùng giai đoạn chuẩn bị PCI DSS.
- Không có livepatch miễn phí: vá kernel cần reboot theo lịch; lỗ hổng kernel nghiêm trọng cần cửa sổ khẩn cấp.

## 6. Khi nào xem lại quyết định

- Rocky có bản vá bảo mật trễ hơn RHEL quá 7 ngày hai lần trong một quý.
- Nhà cung cấp đối soát đổi chứng nhận (bỏ RHEL hoặc thêm Ubuntu).
- Hơn 80% workload đã lên Kubernetes: xem lại distro cho node (có thể là distro tối giản như Flatcar, Talos hoặc
  Bottlerocket).
- Nhà cung cấp đối soát chứng nhận RHEL 10: chuyển máy mới sang Rocky 10 (hỗ trợ tới 2035).
- Năm 2030, hai năm trước khi Rocky 9 hết hỗ trợ: lập kế hoạch nâng cấp.
```

## Các quyết định cần cân nhắc

- **Một distro hay hai?** Ubuntu cho đa số (team quen, role sẵn) cộng một máy Rocky cho đối soát cũng bảo vệ được,
  nếu ADR tính đúng cái giá: hai bộ role, hai luồng vá, hai bộ CIS, người trực phải nhớ `apt` lẫn `dnf`, AppArmor lẫn
  SELinux. Với team 3 người, đó là chi phí lớn.
- **Rocky hay AlmaLinux hay RHEL?** Rocky và Alma gần như tương đương; Alma từ 2023 chọn "tương thích ABI" thay cho
  "giống từng bit" với RHEL. RHEL đáng tiền khi cần hỗ trợ có hợp đồng, kpatch, Insights, hoặc nhà cung cấp chỉ nhận
  RHEL thật.
- **CentOS Stream** không phù hợp: là nhánh phát triển đi trước RHEL, vòng đời ngắn hơn, không có "bản vá cho bản đã
  phát hành" theo nghĩa truyền thống.
- **Debian** ổn định và nhẹ, nhưng Debian 13 kể cả LTS không đủ 5 năm tính từ bây giờ, và không có chứng nhận cho phần
  mềm đối soát.
- **Bản 9 hay 10?** RHEL 10 và Rocky 10 (2025) sống lâu hơn (tới 2035), nhưng nhà cung cấp đối soát mới chứng nhận
  bản 9. Chọn 9 cho mọi máy để giữ một luồng, hoặc 10 cho máy khác và 9 cho máy đối soát; ghi rõ lựa chọn.
- **Baseline phải kiểm được bằng lệnh** (`sshd -T | grep passwordauthentication`, `getenforce`, `chronyc tracking`,
  `auditctl -l`), vì module 09 sẽ biến từng dòng thành task Ansible và test.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Sắp ràng buộc | 15 | Tách bắt buộc và nên có; nhận ra ràng buộc chứng nhận và vòng đời loại phương án nào |
| So sánh phương án | 20 | Ít nhất 3 phương án với số liệu vòng đời đúng; tiêu chí so sánh gắn với ràng buộc, không chung chung |
| Quyết định | 20 | Thoả mọi ràng buộc bắt buộc; lý do dẫn từ bảng; nêu cái giá đã chấp nhận |
| Baseline | 25 | Đủ 7 nhóm bắt buộc, cấu hình cụ thể (giá trị, không chỉ "bật firewall"), mỗi dòng có lý do và kiểm được bằng lệnh |
| Rủi ro | 10 | Ít nhất 3 rủi ro thật kèm cách giảm; không liệt kê rủi ro chung chung |
| Xem lại | 10 | Tín hiệu đo được hoặc mốc thời gian cụ thể |

Từ 70 điểm là đạt. Chọn Ubuntu cho cả máy đối soát, hoặc tắt SELinux/AppArmor trong baseline, thì tối đa 50 điểm.
