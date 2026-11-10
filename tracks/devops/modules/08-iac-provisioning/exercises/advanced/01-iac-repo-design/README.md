---
title: Thiết kế repo IaC nhiều môi trường và nhiều tài khoản cho Olist Shop
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung thiết kế, điền mọi TODO
  - path: tests/test_design.py
    note: Không sửa; kiểm khung và vài quyết định đo được, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/advanced/01-iac-repo-design -q
---

## Mục tiêu

Thiết kế cách tổ chức code và state OpenTofu cho nhiều môi trường sao cho: một lỗi chỉ phá được một phần nhỏ (blast radius), quyền
apply prod tách khỏi dev, thay đổi đi qua review và promote theo thứ tự, secret không nằm trong state hay repo, và drift được phát
hiện thay vì tình cờ thấy.

## Đề bài

Hiện trạng hạ tầng của Olist Shop:

- Một thư mục `infra/` duy nhất, một state cho cả dev, staging, prod, chọn môi trường bằng tệp tfvars và CLI workspace.
- Mọi kỹ sư có quyền admin trên một tài khoản AWS và apply từ laptop. Access key dài hạn nằm trong secret của repo cho CI.
- Quý trước: apply nhầm workspace xoá bảng DynamoDB của staging; hai người apply cùng lúc ghi đè state; mật khẩu DB tìm thấy trong
  state và trong một tệp `prod.tfvars` đã commit.
- Kế hoạch: tách thành ba tài khoản (dev, staging, prod) cộng một tài khoản shared cho state; capstone m05 sẽ dựng Olist Shop bằng
  OpenTofu trên LocalStack theo thiết kế này.
- Team: 4 kỹ sư backend, 1 người vận hành (bạn); khoảng 15 PR hạ tầng mỗi tuần.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 8.`, không còn chữ `TODO`.

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và ràng buộc | Ít nhất 300 ký tự (không tính bảng, khối code); nói tới tài khoản (account) và môi trường |
| 2. Cấu trúc repo | Một khối ```` ```text ```` có cây thư mục chứa `modules/`, `dev`, `staging`, `prod` |
| 3. State và ranh giới | Bảng ít nhất 4 dòng đủ 5 cột (`Stack`, `Backend key`, `Khoá`, `Ai được apply`, `Blast radius`); backend key không trùng; có stack của prod (key chứa `prod`); cột Khoá của mọi dòng có `use_lockfile` hay `dynamodb` |
| 4. Workspaces hay thư mục | Ít nhất 200 ký tự; nói tới workspace và thư mục (directory) |
| 5. Module, version và promotion | Ít nhất 4 gạch đầu dòng; có `ref=` hay `version`, `.terraform.lock.hcl`, và promote (promotion, nâng bản) |
| 6. Luồng CI/CD | Một khối mermaid có `plan`, `apply`, `drift` và bước phê duyệt (approve, phê duyệt, duyệt) |
| 7. Bảo mật state và secret | Ít nhất 4 gạch đầu dòng; có encryption (hay mã hoá state), `ephemeral` (hay write-only, `value_wo`), `OIDC`, `KMS` |
| 8. Rủi ro và lộ trình | Ít nhất 4 gạch đầu dòng |

Toàn văn bản: không dòng nào đặt secret (password, mật khẩu, token, secret, passphrase) trong tệp `.tfvars`; câu phủ định như
"không bao giờ để password trong .tfvars" thì được.

Test đưa khung trống và một thiết kế yếu (một backend key cho mọi stack, không khoá, không có prod, không drift, không phê duyệt,
không lock file, không OIDC, mật khẩu trong `prod.tfvars`, không có `modules/`) vào cùng phép kiểm và đòi bị bắt, và đưa một
thiết kế tốt vào và đòi pass. Nội dung chấm bằng rubric trong `solutions/advanced/01-iac-repo-design/SOLUTION.md`; đọc rubric
**sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/08-iac-provisioning/exercises/advanced/01-iac-repo-design -q` pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Trả lời được: một kỹ sư mới sửa module `data-store`, thay đổi đi tới prod qua những bước nào, ai duyệt, và lúc nào thì prod mới
  thật sự nhận bản mới.
- Trả lời được: CI của dev bị lộ token, kẻ tấn công làm được gì với state và tài nguyên của prod.

## Gợi ý

### Gợi ý 1

Chia state theo hai trục: môi trường (ranh giới quyền, tài khoản) và tần suất thay đổi hay mức nguy hiểm (network ít đổi, app đổi
hằng ngày, data giữ dữ liệu khách). State nhỏ thì plan nhanh, khoá ít tranh chấp và lỗi chỉ phá một phần. Stack cần giá trị của
stack khác thì đọc output đã publish (SSM Parameter, `terraform_remote_state`) chứ không gộp state.

### Gợi ý 2

Promote một thay đổi hạ tầng là đổi `ref=` (hay `version`) của module lần lượt ở từng thư mục môi trường, mỗi lần một PR có plan
đính kèm. Apply ở prod nên dùng đúng plan đã duyệt (`tofu apply tfplan`), plan mã hoá. Drift phát hiện bằng job theo lịch chạy
`plan -refresh-only -detailed-exitcode`.
