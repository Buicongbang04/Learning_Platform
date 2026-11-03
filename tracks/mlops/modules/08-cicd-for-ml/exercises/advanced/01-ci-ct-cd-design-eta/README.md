---
title: Thiết kế CI, CT, CD cho dịch vụ ETA - ai chạy khi nào, chặn cái gì
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Tài liệu thiết kế, điền mọi TODO
  - path: tests/test_design.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/08-cicd-for-ml/exercises/advanced/01-ci-ct-cd-design-eta -q
---

## Mục tiêu

Thiết kế hệ thống pipeline cho một repo ML thật, thay vì dán một workflow mẫu: nhiều workflow, mỗi cái có trigger, cổng và
chi phí rõ ràng; và nêu chỗ hai lớp (code, model) giao nhau để không ai giao sai thứ cho ai.

## Đề bài

Bối cảnh: dịch vụ ETA taxi NYC (capstone). Đội 5 người, mỗi ngày 10 đến 20 PR vào code, dữ liệu mới về mỗi tháng (không kèm
commit), train lại một lần mỗi tuần hoặc khi dữ liệu đổi, train đầy đủ cần GPU 40 phút, train mẫu CPU 4 phút. Model lên
production bằng cách đổi alias `champion` trong registry (module 04); service đọc alias đó. Mã nguồn trên GitHub, dữ liệu nội bộ không
được rời mạng công ty, ngân sách GitHub-hosted runner có hạn.

Điền `starter/DESIGN.md`, sáu phần đánh số:

1. Bối cảnh: tối thiểu 300 ký tự văn xuôi nói rõ tần suất thay đổi và ràng buộc.
2. Sơ đồ mermaid, tối thiểu 8 cạnh, đi từ "PR mở" và "dữ liệu đổi" tới "model đang phục vụ".
3. Bảng workflow (tối thiểu 5 dòng, 4 cột: Workflow, Trigger, Chặn merge hay deploy, Thời gian ước tính). Trigger phải nêu sự
   kiện cụ thể; trong cả bảng phải có `paths`, `schedule`, `workflow_dispatch` và `alias`. Dòng nào là deploy hay release thì cột "Chặn" phải nêu cổng hay
   người duyệt.
4. Chỗ hai lớp nối nhau, tối thiểu 4 gạch đầu dòng: đổi alias thì kích hoạt gì, định danh nào (digest, commit, sha) được
   kiểm ở cả hai đầu, hai workflow cùng chạy thì xử lý ra sao, khi nào cần người duyệt.
5. Secrets, quyền, OIDC: tối thiểu 4 gạch đầu dòng, nhắc `OIDC`, `permissions` và PR từ `fork`.
6. Chi phí và rủi ro: tối thiểu 4 gạch đầu dòng, nhắc `cache`, `concurrency` và `self-hosted` (runner tự host, dùng cho GPU và
   dữ liệu nội bộ).

Test chỉ kiểm cấu trúc và vài ràng buộc; chất lượng lập luận chấm bằng rubric trong `solutions/advanced/01-ci-ct-cd-design-eta/SOLUTION.md`.

## Tiêu chí đạt

- Không còn `TODO`; đủ sáu phần đánh số.
- Phần 1 tối thiểu 300 ký tự; phần 2 có khối mermaid từ 8 cạnh.
- Bảng phần 3 từ 5 dòng đủ 4 cột; cột Trigger nêu sự kiện cụ thể; có `paths`, `schedule`, `workflow_dispatch`, `alias`; dòng deploy có cổng hay người duyệt.
- Phần 4 nói về `alias` và một định danh (`digest`, `commit` hoặc `sha`); phần 5 có `OIDC`, `permissions`, `fork`;
  phần 6 có `cache`, `concurrency`, `self-hosted`; mỗi phần 4 đến 6 từ 4 gạch đầu dòng.

## Gợi ý

### Gợi ý 1

Bắt đầu từ bảng phần 3, rồi vẽ sơ đồ từ bảng. Hỏi mỗi workflow: "cái gì kích hoạt nó, ai chờ nó, nếu nó đỏ thì điều gì dừng
lại?". Workflow nào không dừng được điều gì thì có đáng tồn tại không?

### Gợi ý 2

Phần 4 là chỗ dễ viết mơ hồ nhất. Một câu tốt có hai vế kiểm được: "workflow deploy nhận X từ workflow train" và "nó kiểm lại
X bằng cách nào trước khi dùng". Nếu bạn không nêu được vế sau, đó là một lỗ hổng.
