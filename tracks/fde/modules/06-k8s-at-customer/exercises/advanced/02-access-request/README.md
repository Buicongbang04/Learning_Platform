---
title: "Yêu cầu quyền tối thiểu gửi platform team"
level: advanced
services: []
files:
  - path: starter/access-request.md
    note: Email và Role YAML, bạn viết
run:
  - "Không có test tự động: tự chấm theo rubric trong solutions/advanced/02-access-request/SOLUTION.md"
---

## Mục tiêu

Một khách mới (ngân hàng, cluster do platform team quản, quy trình phê duyệt quyền mất một tuần) hỏi: "Vendor cần quyền
gì trong cluster?". Trả lời "cluster-admin cho nhanh" là mất hợp đồng; trả lời thiếu thì ngày cài bị kẹt chờ thêm một
tuần nữa. Bạn viết yêu cầu quyền **tối thiểu nhưng đủ** cho toàn bộ vòng đời của quillo: cài, nâng cấp, sao lưu, gỡ lỗi,
gỡ cài đặt, kèm lý do từng verb để người duyệt ký được.

## Đề bài

Ngữ cảnh: chart quillo 1.0.0 (mục "Helm chart" của [README sản phẩm](../../../../../product/README.md)), cài bằng Helm 3
vào một namespace platform team tạo sẵn; namespace đã có PSA, quota và NetworkPolicy chặn sẵn như `lawfirm-prod`.
Vòng đời cần hỗ trợ: `helm upgrade --install` và `helm rollback`, `ops/backup.sh --kubectl` (exec `pg_dump` trong pod
db), xem log và `kubectl port-forward` để kiểm, mở NetworkPolicy cho đúng luồng của quillo, `helm uninstall`.

Viết `starter/access-request.md` gồm:

1. **Email ngắn** gửi platform team (≤15 dòng): phạm vi, thời hạn, ai dùng, cách thu hồi.
2. **Role YAML** (một hay nhiều `Role` + `RoleBinding` cho một ServiceAccount hoặc group do họ đặt tên) trong namespace.
3. **Bảng lý do**: mỗi cặp `resource` + `verb` một dòng, lệnh nào của vòng đời cần nó, rủi ro nếu cấp, và có thể bỏ được
   không (bỏ thì mất gì).
4. **Những gì bạn không xin** và vì sao (quyền cluster, CRD, namespace, `escalate`/`bind`, `*`…), cùng cách làm khi
   cần đến chúng (nhờ platform team làm hộ, ticket).
5. **Cách kiểm sau khi cấp**: lệnh tự kiểm trước ngày cài (vd. script của bài basic 01) và kết quả mong đợi.

## Tiêu chí đạt

Tự chấm theo rubric 10 điểm trong `solutions/advanced/02-access-request/SOLUTION.md` (đạt từ 7 điểm), gồm: Role chỉ
trong namespace và không có `*`, đủ quyền cho mọi bước vòng đời (kể cả Secret lưu release của Helm, `pods/exec`,
`pods/portforward`), lý do từng verb, phân biệt quyền RBAC với chính sách admission, và cách kiểm.

## Gợi ý

### Gợi ý 1

Liệt kê từng lệnh của vòng đời rồi hỏi: lệnh này gọi API nào? Helm 3 còn tự đọc/ghi một loại object để nhớ release.

### Gợi ý 2

`kubectl auth can-i --list --as=system:serviceaccount:<ns>:<tên>` (người có quyền impersonate chạy) cho platform team
kiểm Role trước khi cấp.

### Gợi ý 3

Chart có tạo object cluster-scoped nào không? `helm template` rồi lọc theo `kind` trả lời trong một lệnh.
