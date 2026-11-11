---
title: Chính sách error budget và quy trình on-call cho team checkout
level: advanced
services: []
files:
  - path: starter/POLICY.md
    note: Khung chính sách, 7 phần
  - path: starter/policy.yaml
    note: Phần máy đọc của chính sách
  - path: starter/oncall.yaml
    note: Lịch trực 4 tuần, leo thang, page budget
  - path: tests/test_policy.py
    note: Kiểm cấu trúc, ràng buộc lịch, số liệu; không sửa
run:
  - uv run pytest tracks/devops/modules/16-sre-operations/exercises/advanced/02-error-budget-policy-oncall -q
---

## Mục tiêu

Viết chính sách error budget mà product và kỹ thuật ký trước khi có sự cố, cộng một quy trình on-call bền vững: lịch trực công
bằng, leo thang có thời hạn, page budget, vai trò khi có sự cố. Phần máy kiểm được nằm trong YAML, phần cần lập luận nằm trong
`POLICY.md` và chấm bằng rubric.

## Đề bài

Team checkout của Olist có 6 kỹ sư: An, Bình, Chi, Dũng, Giang, Hà. SLO của checkout: 99,9% request không lỗi trong cửa sổ trượt
28 ngày. Ràng buộc:

- Lịch trực 4 tuần, mỗi tuần bắt đầu thứ Hai: 2026-11-16, 2026-11-23, 2026-11-30, 2026-12-07; mỗi tuần một primary và một secondary,
  hai người khác nhau.
- Không ai trực (vai nào cũng vậy) hai tuần liền.
- Giang nghỉ phép tuần 2026-11-30. Hà mới vào team: chỉ làm secondary.
- Ai cũng có ít nhất 1 ca, không ai quá 2 ca trong 4 tuần.

**1. `starter/oncall.yaml`.** Giữ `team`, `members`, `timezone`. Điền:
- `handoff`: `weekday: monday`, `time` dạng `HH:MM`;
- `weeks`: bốn mục `{start, primary, secondary}` theo đúng ngày trên (YAML đọc `2026-11-16` thành ngày);
- `escalation`: ít nhất 3 mức `{level, after_minutes}`, mức đầu 0 phút, tăng dần, mức cuối không quá 30 phút;
- `page_budget`: `night_per_week` từ 1 tới 2, `per_week` lớn hơn nó và không quá 14.

**2. `starter/policy.yaml`.**
- `slo.budget_minutes`: số phút budget của cửa sổ.
- `thresholds`: đúng bốn mức theo thứ tự `normal`, `caution`, `freeze-features`, `freeze-all`. `remaining_above` (phần budget còn lại
  phải **lớn hơn** để ở mức đó) là số giảm dần cho ba mức đầu, mức `freeze-features` là 0, mức cuối là `null` (budget đã cạn hoặc
  âm). Mỗi mức có `actions` không rỗng và `allowed` (loại thay đổi được release: `feature`, `bugfix`, `security-fix`, `rollback`):
  mọi mức đều cho `security-fix` và `rollback`, hai mức đóng băng không cho `feature`.
- `exceptions`: `approver` (một vai trò, ví dụ VP Engineering) và `max_per_window` 1 hoặc 2.

**3. `starter/POLICY.md`**, giữ bảy tiêu đề. Test kiểm: không còn `TODO`; phần 2 nêu số phút budget; phần 3 có bảng nhắc cả bốn state
trong dấu backtick; phần 4 nêu đúng `approver`; phần 5 nêu hai con số page budget, bàn giao ca và chế độ bù cho người trực; phần 6
có bảng SEV1 tới SEV3, vai trò incident commander và một sơ đồ mermaid ít nhất 4 cạnh; phần 7 đặt giới hạn toil bằng phần trăm.

Test cũng chạy bộ kiểm trên các tệp mẫu (hỏng, yếu, đạt) để chứng minh nó bắt được lỗi. Nội dung chấm bằng rubric trong
`SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest ... -q` pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10.
- Trả lời được: vì sao chính sách phải được ký **trước** sự cố; budget cạn vì cổng thanh toán bên ngoài sập thì có đóng băng release
  không; page budget bị vượt ba tuần liền thì làm gì.

## Gợi ý

### Gợi ý 1

Lịch trực là một bài xếp lịch nhỏ: đặt người có ràng buộc trước (Hà chỉ secondary, Giang tránh tuần thứ ba), rồi kiểm "không hai tuần
liền". 8 ca chia 6 người thì hai người có 2 ca.

### Gợi ý 2

Đọc chương "Embracing Risk", "Being On-Call" của sách Google SRE và ví dụ "Error Budget Policy" của SRE Workbook (link ở phần tài liệu
tham khảo của module). Chính sách tốt trả lời được "ai quyết, dựa trên số nào, trong bao lâu".
