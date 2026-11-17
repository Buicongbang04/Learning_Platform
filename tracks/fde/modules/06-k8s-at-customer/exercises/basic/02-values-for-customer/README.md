---
title: "Values file của quillo cho cluster công ty luật"
level: basic
services: []
files:
  - path: starter/values.yaml
    note: Values của khách, bạn viết
  - path: tests/test_values.py
    note: Không sửa
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare lawfirm-prod
  - uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/basic/02-values-for-customer -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Chart của vendor viết cho "một cluster nào đó"; cluster của khách có luật riêng. Bạn viết values file của **khách này**
và chứng minh trước buổi cài rằng API server của khách chấp nhận mọi thứ chart sinh ra, rằng tổng tài nguyên vừa phần
namespace còn lại kể cả lúc nâng cấp, mà không cắt tài nguyên xuống dưới mức sản phẩm chạy được. Không tốn một pod nào:
mọi thứ kiểm bằng `helm template` và `--dry-run=server`.

## Đề bài

Chart `quillo-1.0.0.tgz` nằm trong bundle (`chart/` của `quillo-1.0.0.tar`), bảng values ở mục "Helm chart" của
[README sản phẩm](../../../../../product/README.md). Release tên `quillo`, namespace `quillo` trên `lawfirm-prod`.

Thông tin IT công ty luật gửi:

- Namespace `quillo` gắn nhãn Pod Security Admission `enforce=restricted`, có ResourceQuota `quillo-quota` và
  LimitRange `quillo-limits` (đọc bằng `kubectl describe` với kubeconfig của `fde`).
- Image chỉ được kéo từ registry nội bộ, dưới project của vendor: `10.0.2.101:5000/vendors/quillo/…`, giữ nguyên đường
  dẫn và tag gốc (bỏ host gốc như `ghcr.io`). Bốn image của quillo 1.0.0 phải là đúng:
  `10.0.2.101:5000/vendors/quillo/quillo-api:1.0.0`, `…/pgvector/pgvector:0.8.6-pg16`,
  `…/ggml-org/llama.cpp:server-b11718`, `…/quillo-models:1.0.0`.
- Trong namespace đã có pod `it-backup-agent` của IT (requests cpu `200m`, memory `1Gi`; limits cpu `500m`, memory
  `1Gi`), không được đụng tới.
- Node chỉ có 2 vCPU dùng chung: tổng `requests.cpu` của **cả namespace** không vượt `1000m`, dù quota cho phép nhiều
  hơn.

Mức tối thiểu vendor ghi trong tài liệu sizing (dưới mức này sản phẩm chạy chậm hoặc bị OOM-kill):

| Thành phần | requests.cpu | requests.memory | limits.memory |
| --- | --- | --- | --- |
| api | 100m | 256Mi | 512Mi |
| worker | 50m | 128Mi | 384Mi |
| db | 100m | 256Mi | 512Mi |
| llm | 250m | 1Gi | 1536Mi |
| embed | 100m | 384Mi | 512Mi |

Viết `starter/values.yaml`. Test boot `lawfirm-prod`, tạo pod `it-backup-agent` như trên, chép chart và values vào VM
rồi chạy `helm template quillo quillo-1.0.0.tgz -n quillo -f values.yaml` và kiểm. Đo trên máy của repo: ~15 s.

## Tiêu chí đạt

`test_values_fit_lawfirm_prod`:

- `helm template` thành công; tập image của mọi container và initContainer trong các Deployment/StatefulSet đúng bằng
  bốn image ở trên.
- Mọi container và initContainer chạy với `runAsUser` là số khác `0` (đặt ở pod hoặc container).
- `kubectl apply --dry-run=server -n quillo -f <manifest>` thành công và không in dòng `Warning:` nào.
- Pod dựng từ template của từng Deployment/StatefulSet (`kubectl create --dry-run=server`) được chấp nhận.
- Tài nguyên tính cho mỗi pod = max(tổng các container, initContainer lớn nhất) theo từng loại. Mỗi thành phần đạt mức
  tối thiểu trong bảng trên.
- Cộng mọi pod (số replica, cộng thêm **một** pod cho mỗi Deployment dùng `RollingUpdate` vì lúc nâng cấp pod mới lên
  trước khi pod cũ tắt) cùng mức đã dùng của quota (đọc từ `status.used`, gồm `it-backup-agent`): `requests.cpu` ≤
  `1000m`; `requests.memory` và `limits.memory` không vượt `status.hard` của `quillo-quota`.

## Gợi ý

### Gợi ý 1

Đọc luật trước khi viết: `kubectl describe resourcequota,limitrange -n quillo` và nhãn của namespace. Mỗi object nói
cho bạn một điều kiện mà container nào cũng phải thoả.

### Gợi ý 2

`kubectl apply --dry-run=server` một Deployment hầu như luôn thành công: cái bị từ chối là pod mà ReplicaSet tạo ra
sau đó. Cảnh báo in ra lúc apply Deployment là thứ đáng đọc nhất.

### Gợi ý 3

Lập bảng: mỗi thành phần một dòng, ba cột tài nguyên, rồi một dòng cho pod thêm lúc rolling update. Khi tổng vượt, xem
cột nào có chỗ hạ mà vẫn trên mức tối thiểu.
