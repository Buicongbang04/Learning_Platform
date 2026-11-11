---
title: "Hiện trường: quillo lên cluster production của công ty luật"
level: intermediate
services: []
files:
  - path: starter/deploy.sh
    note: Script triển khai theo hướng dẫn của vendor; bạn sửa
  - path: starter/values.yaml
    note: Values IT đã dùng; bạn sửa
  - path: tests/test_quillo_k8s.py
    note: Không sửa
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare lawfirm-prod
  - uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/intermediate/01-pods-not-up -q -s
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Công ty luật đã chạy thử quillo trên máy staging và giờ muốn lên cluster production do IT quản. Bạn có một kubeconfig
trong một namespace, một bundle offline và một ticket ngắn ngủn. Việc của bạn: đưa quillo lên **đầy đủ** (hỏi đáp có
trích dẫn, nạp tài liệu chạy), bằng một script chạy lại được, mà không xin thêm quyền và không nới lỏng bất kỳ chính sách
nào của khách.

## Đề bài

Máy `lawfirm-prod`: Ubuntu 22.04, k3s air-gapped do IT quản, user `fde` không có sudo, không có Docker, không ra
internet. `fde` chỉ có `~/.kube/config` trong namespace `quillo`. Có sẵn `kubectl`, `helm`, `python3` (3.10), `curl`,
`tar`. Registry nội bộ của khách: `10.0.2.101:5000` (HTTP, không cần đăng nhập). Bundle `quillo-1.0.0.tar` (đã kiểm
sha256) nằm ở `/home/fde/quillo-1.0.0.tar`; cách cài bằng Helm ở mục "Helm chart" của
[README sản phẩm](../../../../../product/README.md).

Quy định của IT:

- Cluster chỉ chạy image kéo từ `10.0.2.101:5000/`.
- Không sửa namespace, quota, LimitRange hay NetworkPolicy `default-deny`; release Helm tên `quillo` trong namespace
  `quillo`.
- Pod khác trong namespace không được nói chuyện thẳng với database hay model server của quillo; database không được mở
  kết nối ra ngoài.

IT đã làm theo hướng dẫn cài của vendor (chính là `starter/deploy.sh` với `starter/values.yaml`) và gửi ticket:

> Helm báo `STATUS: deployed` nhưng pod không lên, `kubectl get pods` không có pod nào của quillo.

Sửa `starter/deploy.sh` và `starter/values.yaml`; được thêm tệp của bạn (script, công cụ đã ghim…) vào `starter/`. Test
boot `lawfirm-prod` (`customer_site`, registry phía host luôn mới), chép bundle vào `/home/fde/quillo-1.0.0.tar`, chép
**mọi tệp** trong `starter/` vào `/home/fde/deploy/`, rồi chạy `cd /home/fde && sh /home/fde/deploy/deploy.sh` (≤180 s)
và kiểm bằng `kubectl` của `fde` cùng `kubectl port-forward svc/quillo-api 18080:8080` chạy trong VM.

Đo trên máy của repo với lời giải tham chiếu: cả bài ~90 s. Tự boot máy để điều tra:
`with fdekit.customer_site("lawfirm-prod") as s:` rồi `s.vm.ssh(...)`, `s.vm.put(...)`.

## Tiêu chí đạt

`test_quillo_up_in_namespace`:

- `deploy.sh` thoát `0` trong 180 s.
- Release `quillo` ở trạng thái `deployed` từ chart `quillo-1.0.0`; trong 90 s sau đó Deployment `quillo-api`,
  `quillo-worker`, `quillo-llm`, `quillo-embed` có pod available và StatefulSet `quillo-db` có pod ready.
- Mọi container và initContainer của pod thuộc release (`app.kubernetes.io/instance=quillo`) dùng image bắt đầu bằng
  `10.0.2.101:5000/`.
- Qua port-forward: `GET /healthz` trả `200` với `"version": "1.0.0"`; tải một tài liệu qua `POST /api/documents`
  (token admin lấy từ Secret mà Deployment `quillo-api` tham chiếu cho `QUILLO_ADMIN_TOKEN`) trả `201`; một tệp đặt vào
  `/data/inbox/` của pod worker (`kubectl cp`) xuất hiện trong `GET /api/documents` trong 60 s; `POST /api/ask` về nội
  dung tài liệu vừa tải trả `200` và trích dẫn đúng tài liệu đó.
- Một pod thử khác trong namespace (được phép egress tới mọi pod trong namespace) không kết nối được tới service
  `quillo-db:5432` và `quillo-llm:8080`; từ pod `quillo-db-0` không mở được kết nối tới `10.0.2.101:5000`.
- `spec` của `default-deny` giữ nguyên.

## Gợi ý

### Gợi ý 1

`STATUS: deployed` chỉ có nghĩa API server đã nhận các object. Pod do controller tạo về sau; khi controller bị từ chối,
lý do nằm ở chỗ controller để lại, không ở output của Helm.

### Gợi ý 2

Sửa từng lỗi một rồi chạy lại, đọc lại từ đầu: lỗi sau thường chỉ lộ ra khi lỗi trước đã qua, và mỗi lỗi lộ ra ở một
chỗ khác nhau (sự kiện của controller, trạng thái container, readiness, log ứng dụng).

### Gợi ý 3

Pod đã được tạo thì `kubectl describe pod` cho biết nó đang chờ gì; pod `Running` mà không `Ready` thì hỏi chính ứng
dụng: probe gọi gì, endpoint đó trả gì, log nói gì. Mỗi tầng trả lời một câu hỏi khác.
