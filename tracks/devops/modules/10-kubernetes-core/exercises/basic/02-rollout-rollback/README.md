---
title: Rollout và rollback API Olist Shop không mất capacity
level: basic
services: []
files:
  - path: starter/api.yaml
    note: Deployment và Service của API, thiếu strategy và probe
  - path: starter/release.sh
    note: Script phát hành
  - path: starter/rollback.sh
    note: Script quay lui
  - path: tests/fixtures/deps.yaml
    note: Postgres, Redis, ConfigMap, Secret do test dựng
  - path: tests/test_rollout_rollback.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/10-kubernetes-core/exercises/basic/02-rollout-rollback -q -rs
---

## Mục tiêu

Cấu hình Deployment để một bản lỗi không bao giờ lấy mất pod đang phục vụ, viết script phát hành có change-cause, đọc
`rollout history`, và quay lui về đúng ReplicaSet cũ, cả về bản ngay trước lẫn về một revision chỉ định.

## Đề bài

1. Sửa `starter/api.yaml`: Deployment `api` 4 replica với `strategy` RollingUpdate `maxUnavailable: 0`, `maxSurge: 1`;
   `revisionHistoryLimit` từ 3 tới 10; `progressDeadlineSeconds` tối đa 90; readinessProbe gọi `/readyz`, livenessProbe gọi
   `/healthz`.
2. Viết `starter/release.sh VERSION [TÊN=GIÁ_TRỊ ...]`: đặt `APP_VERSION=VERSION` (cộng các biến thêm nếu có) cho
   `deployment/api` trong **một** revision, ghi annotation `kubernetes.io/change-cause` là `release VERSION`, chờ rollout tối đa
   150 giây. Rollout không xong thì trả mã khác 0 và **không** tự rollback (quyết định quay lui là của người trực).
3. Viết `starter/rollback.sh [REVISION]`: không đối số thì quay về revision trước, có thì về đúng revision đó; chờ rollout xong.

Hai script chạy bằng `kubectl` với kubeconfig và namespace mặc định đã đặt sẵn (không truyền `--kubeconfig`, `--context`, `-n`).

**Cách test chấm.** Test dựng Postgres, Redis, ConfigMap `olist-config`, Secret `olist-db` từ `tests/fixtures/deps.yaml` trong
namespace riêng, apply `api.yaml` (bản 1.0), rồi chạy script của bạn trong sandbox:

| Bước | Test kiểm |
| --- | --- |
| Apply | `replicas: 4`, `maxUnavailable` 0, `revisionHistoryLimit` 3 tới 10, `progressDeadlineSeconds` ≤ 90, readinessProbe `/readyz` |
| `release.sh 1.1` | Mã 0; mọi request qua Service `api` (gọi `/healthz` từ trong pod) trả `version` 1.1; có ReplicaSet mới |
| `release.sh 1.2 DATABASE_URL=<host không tồn tại>` | Mã khác 0; Deployment vẫn `availableReplicas: 4`; Service vẫn trả 1.1; template vẫn là 1.2 (không tự rollback) |
| `rollback.sh` | Mã 0; ReplicaSet đang chạy **chính là** ReplicaSet của bản 1.1 (không tạo cái mới); Service trả 1.1 |
| `rollout history` | Có change-cause `release 1.1` và `release 1.2` |
| `rollback.sh 1` | Mã 0; ReplicaSet đang chạy là ReplicaSet của bản 1.0 |

Khoảng 2,5 phút, phần lớn là chờ bản 1.2 vượt `progressDeadlineSeconds`.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao với 4 replica, strategy mặc định (25%) để mất một pod đang phục vụ khi bản mới lỗi, còn 3 replica thì
  không.
- Nói được `rollout undo` làm gì với ReplicaSet và số revision, và vì sao `revisionHistoryLimit: 0` làm mất khả năng quay lui.

## Gợi ý

### Gợi ý 1

`kubectl set env deployment/api A=1 B=2` đổi hai biến trong một lần sửa template, tức một revision. `rollout history` đọc
change-cause từ annotation của ReplicaSet; controller chép annotation của Deployment sang ReplicaSet mới, nên ghi annotation cùng lúc
với thay đổi template là chắc nhất: `kubectl rollout pause`, sửa, ghi annotation, `kubectl rollout resume` là một cách gọn.

### Gợi ý 2

`kubectl rollout status --timeout=...` trả mã khác 0 khi hết giờ hay khi Deployment báo `ProgressDeadlineExceeded`. Xem
ReplicaSet và `pod-template-hash` bằng `kubectl get rs -l app.kubernetes.io/name=api -o wide`, lịch sử bằng
`kubectl rollout history deployment/api --revision=N`.
