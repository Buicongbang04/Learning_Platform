---
title: Ôn thi Associate - lock file, state, OpenTofu khác Terraform, chọn công cụ IaC
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Trả lời được các câu hỏi tình huống kiểu Terraform Associate 004 (lock file, `count`/`for_each`, data source, drift, refactor
state, secret, khoá state, workspace, HCP Terraform) và phân biệt rõ tính năng nào chỉ có ở OpenTofu, để vừa làm việc với `tofu`
vừa thi được chứng chỉ của HashiCorp.

## Đề bài

Bài này không có code. Làm 13 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 12 câu chọn một đáp án, một câu chọn mọi
đáp án đúng. Đọc mục 2 tới 6 của module trước khi làm.

Với mỗi câu, tự hỏi:

1. Lệnh hay khối nào thay đổi **state**, lệnh nào thay đổi **hạ tầng thật**, lệnh nào chỉ đọc?
2. Câu hỏi đang hỏi về Terraform (đề thi) hay OpenTofu (công việc hằng ngày)? Tính năng đó có ở cả hai không?
3. Phương án nào review được trong PR và lặp lại được ở mọi môi trường?

## Tiêu chí đạt

- Đúng ít nhất 10/13 câu.
- Với mỗi câu sai, nói lại được vì sao đáp án đúng đúng và khi nào phương án bạn chọn mới đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Ràng buộc version trong `required_providers` nói bản nào **được phép**; `.terraform.lock.hcl` ghi bản **đã chọn** kèm checksum.
`moved`, `import`, `removed` là khối cấu hình (đi qua review); `state mv`, `state rm`, `import` CLI là thao tác tay trên một state.

### Gợi ý 2

Tính năng chỉ có ở OpenTofu: mã hoá state và plan, early evaluation (biến trong backend và `source` của module), `-exclude`,
`for_each` trên provider, đuôi `.tofu`. `moved`, `import` block, `removed` có ở cả hai (cú pháp gần như nhau).
