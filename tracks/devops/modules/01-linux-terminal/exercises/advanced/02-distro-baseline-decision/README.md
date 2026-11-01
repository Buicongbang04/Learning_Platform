---
title: Chọn distro và baseline cho đợt chuyển máy chủ Olist Shop
level: advanced
services: []
files:
  - path: starter/DECISION.md
    note: Khung ADR, điền mọi TODO
  - path: tests/test_decision.py
    note: Không sửa; kiểm khung, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/01-linux-terminal/exercises/advanced/02-distro-baseline-decision -q
---

## Mục tiêu

Ra một quyết định hạ tầng có hệ quả nhiều năm theo cách một senior bảo vệ được trước CTO và đội bảo mật: liệt kê ràng
buộc, so sánh phương án bằng tiêu chí đo được, chọn, nói rõ cái giá phải trả, và định nghĩa baseline cấu hình mà mọi
máy mới phải đạt.

## Đề bài

Olist Shop đang chạy trên 3 VM CentOS 7 dựng tay từ 2019. Bạn được giao chọn hệ điều hành cho 8 VM mới (2 Nginx,
3 API/worker, 2 Postgres, 1 bastion) và viết baseline cấu hình mà Ansible (module 09) sẽ áp. Ghi chép sau hai tuần
tìm hiểu:

- CentOS 7 đã hết hỗ trợ (EOL 30/06/2024): không còn bản vá bảo mật, repo chính thức đã chuyển sang vault.
- Công ty bắt đầu nhận thanh toán thẻ trực tiếp, phải đạt **PCI DSS 4.0** trong 9 tháng: vá lỗ hổng nghiêm trọng
  trong 30 ngày, có audit log, kiểm soát truy cập bắt buộc, chứng minh được cấu hình chuẩn (CIS benchmark là lựa chọn
  phổ biến).
- Team vận hành 3 người. Hai người quen Ubuntu, một người từng làm RHEL ở ngân hàng. Các role Ansible hiện có viết
  cho `apt`.
- Ngân sách license hạn chế; CFO hỏi "vì sao phải trả tiền cho Linux". Có thể xin ngân sách nếu có lý do rõ.
- Nhà cung cấp phần mềm đối soát thanh toán (chạy trên 1 trong 3 máy API) chỉ chứng nhận chạy trên "RHEL 9 hoặc
  bản tương thích nhị phân"; họ không hỗ trợ khi chạy trên Ubuntu.
- Máy chủ phải chạy ít nhất 5 năm không phải cài lại hệ điều hành; reboot để vá kernel phải xin lịch bảo trì.
- Tương lai (module 10–11) phần lớn workload lên Kubernetes; VM vẫn giữ cho Postgres và bastion.

Điền `starter/DECISION.md` theo dạng ADR (Architecture Decision Record):

1. **Bối cảnh**: các ràng buộc quyết định lựa chọn, xếp theo mức quan trọng.
2. **Phương án**: bảng ít nhất 3 phương án, có ít nhất một distro họ RHEL (RHEL, Rocky, AlmaLinux, CentOS Stream,
   Oracle Linux) và một họ Debian (Debian, Ubuntu). Đủ 6 cột, cột cuối là điểm nguyên 1–5.
3. **Quyết định**: dòng `Chọn: <distro và phiên bản>` (tên phải khớp một dòng trong bảng; được chọn kết hợp, ví dụ
   một distro cho đa số máy và một cho máy đặc thù, miễn tên chính nằm trong bảng) và lý do gắn với ràng buộc.
4. **Baseline**: bảng `Hạng mục | Cấu hình | Lý do`, ít nhất 8 hạng mục, phủ: SSH, firewall, cập nhật bảo mật, đồng bộ
   giờ, audit, MAC (SELinux hoặc AppArmor), log.
5. **Rủi ro và đánh đổi**: ít nhất 3.
6. **Khi nào xem lại quyết định**: ít nhất 2 tín hiệu cụ thể.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/01-linux-terminal/exercises/advanced/02-distro-baseline-decision -q` pass. Test
  chỉ kiểm khung và độ phủ; chất lượng chấm theo rubric trong
  `solutions/advanced/02-distro-baseline-decision/SOLUTION.md`.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi hạng mục baseline kiểm được bằng một lệnh (để module 09 viết thành task Ansible và test).

## Gợi ý

### Gợi ý 1

Xếp ràng buộc thành "bắt buộc" và "nên có" trước khi chấm điểm. Ràng buộc bắt buộc (chứng nhận của nhà cung cấp,
PCI DSS, vòng đời 5 năm) loại phương án; ràng buộc nên có (team quen gì, role Ansible sẵn có) chỉ cộng trừ điểm.
Tra vòng đời chính thức: Ubuntu LTS (5 năm chuẩn, thêm 5 năm ESM qua Ubuntu Pro), RHEL (10 năm), Rocky và AlmaLinux
(theo RHEL), Debian (khoảng 3 năm + 2 năm LTS).

### Gợi ý 2

Không bắt buộc một distro cho mọi máy, nhưng mỗi distro thêm vào là thêm một bộ role Ansible, một luồng vá, một bộ
CIS benchmark, và một thứ để người trực phải nhớ. Nếu chọn hai, nói rõ ranh giới và chi phí đó. Với vá kernel không
reboot, tìm hiểu Canonical Livepatch, kpatch (RHEL) và TuxCare/KernelCare: cái nào cần trả tiền, cái nào đi kèm
subscription.
