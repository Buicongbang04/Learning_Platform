---
title: "Khách chuyển sang OpenShift: values và kế hoạch cài lại"
level: advanced
services: []
files:
  - path: starter/openshift-plan.md
    note: Khung kế hoạch, bạn viết
run:
  - "Không có test tự động: tự chấm theo rubric trong solutions/advanced/01-openshift-move/SOLUTION.md"
---

## Mục tiêu

Ba tháng sau khi quillo chạy trên k3s, công ty luật hợp nhất hạ tầng về OpenShift 4 do một đội platform ở tập đoàn
quản. Bạn không có cluster OpenShift để thử trước. Bạn phải nói trước, có căn cứ, **những gì trong bản cài hiện tại sẽ
gãy**, sửa thế nào, và cần đội platform cấp gì, để buổi cài lại không thành buổi gỡ lỗi trước mặt khách.

## Đề bài

Đầu vào: values bạn đã dùng cho `lawfirm-prod` (bài intermediate 01), chart quillo 1.0.0 (mục "Helm chart" của
[README sản phẩm](../../../../../product/README.md)), và thông tin đội platform gửi:

- OpenShift 4.x, project `quillo` đã tạo sẵn, bạn có vai trò `admin` trong project (không cluster-admin).
- SCC mặc định cho ServiceAccount của project là `restricted-v2`; namespace có annotation dải UID
  `openshift.io/sa.scc.uid-range`. Không cấp SCC khác nếu không có lý do bằng văn bản.
- Registry: internal image registry của OpenShift hoặc registry tập đoàn (TLS, cần pull secret).
- Truy cập từ người dùng qua `Route` với TLS edge do tập đoàn cấp; không có Ingress controller khác.
- Có NetworkPolicy chặn sẵn như cũ; egress ra ngoài cluster do `EgressFirewall` quản.

Viết `starter/openshift-plan.md` (tối đa ~2 trang) gồm:

1. **Bảng khác biệt**: mỗi dòng một khác biệt giữa `lawfirm-prod` (k3s + PSA restricted) và OpenShift ảnh hưởng tới quillo
   (ít nhất 6 dòng): cơ chế, ảnh hưởng cụ thể tới thành phần nào, cách xử lý.
2. **Values cho OpenShift**: khối YAML đầy đủ phần khác với values của `lawfirm-prod`, mỗi thay đổi một dòng lý do.
3. **Thứ tự cài và kiểm**: các bước, lệnh kiểm ở mỗi bước (`oc`/`kubectl`), điểm dừng nếu gặp lỗi.
4. **Câu hỏi và yêu cầu gửi đội platform**: những gì bạn cần họ trả lời hoặc cấp trước ngày cài.

## Tiêu chí đạt

Tự chấm theo rubric 10 điểm trong `solutions/advanced/01-openshift-move/SOLUTION.md` (đạt từ 7 điểm), gồm: nhận ra
vấn đề UID cố định với SCC `restricted-v2`, quyền ghi thư mục với UID ngẫu nhiên, đường vào qua Route và TLS, cách đưa
image vào cluster, NetworkPolicy/EgressFirewall, và không xin SCC rộng hơn khi không cần.

## Gợi ý

### Gợi ý 1

So từng dòng `securityContext` trong values hiện tại với cách `restricted-v2` cấp UID, GID và `fsGroup`. Dòng nào là
"bạn chọn", dòng nào sẽ thành "cluster chọn"?

### Gợi ý 2

Với mỗi image, hỏi: tiến trình trong container cần ghi vào đâu, thư mục đó thuộc UID/GID nào trong image?

### Gợi ý 3

Đọc tài liệu OpenShift về "Managing security context constraints" và "Creating images" (mục hỗ trợ arbitrary user ID)
trước khi viết bảng khác biệt.
