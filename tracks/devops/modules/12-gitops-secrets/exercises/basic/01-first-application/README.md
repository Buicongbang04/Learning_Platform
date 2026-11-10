---
title: Application đầu tiên - Olist Shop tự sync, tự dọn, tự sửa drift
level: basic
services: []
files:
  - path: starter/application.yaml
    note: Application của ArgoCD, 2 TODO
  - path: starter/gitops/shop/kustomization.yaml
    note: Kustomize của Olist Shop, 1 TODO
  - path: starter/gitops/shop/api.yaml
    note: Deployment và Service api
  - path: starter/gitops/shop/redis.yaml
    note: Deployment và Service redis
  - path: starter/gitops/shop/legacy-flags.yaml
    note: ConfigMap cũ, commit thứ hai của test xoá nó
  - path: tests/test_first_application.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/12-gitops-secrets/exercises/basic/01-first-application -q -rs
---

## Mục tiêu

Viết một `Application` của ArgoCD trỏ thư mục Kustomize của Olist Shop trong repo Git, bật sync tự động, prune và self-heal, rồi tự thấy
ba hành vi của vòng reconcile: commit mới được áp lên cluster, object bị xoá khỏi Git bị xoá khỏi cluster, sửa tay trên cluster bị đưa
về đúng Git.

## Đề bài

`starter/gitops/` là nội dung repo GitOps: thư mục `shop/` chứa Kustomize của api và redis. Api đọc cấu hình từ ConfigMap `olist-config`,
sinh bằng `configMapGenerator` để mỗi lần đổi cấu hình là tên ConfigMap đổi theo hash và Deployment rollout lại.

1. Trong `gitops/shop/kustomization.yaml`, thêm `configMapGenerator` tên `olist-config` với bốn literal:

   | Khoá | Giá trị |
   | --- | --- |
   | `APP_VERSION` | `1.0` |
   | `LOG_LEVEL` | `INFO` |
   | `REDIS_URL` | `redis://redis:6379/0` |
   | `DATABASE_URL` | `sqlite:////tmp/olist_shop.db` (bài này không cần Postgres) |

   Giữ `legacy-flags.yaml` trong `resources`.
2. Trong `starter/application.yaml`: `spec.source.path` trỏ thư mục Kustomize, và `syncPolicy` để ArgoCD tự sync mỗi commit mới, xoá
   object đã bỏ khỏi Git, đưa thay đổi tay về trạng thái của Git. Giữ nguyên ba placeholder `LAB_PROJECT`, `LAB_REPO_URL`,
   `LAB_NAMESPACE`: mỗi lần chạy test có một namespace, một AppProject và một repo git riêng, test thay placeholder bằng giá trị thật.
   Khi tự làm tay trên cluster của bạn, ghi thẳng giá trị thật vào ba chỗ đó.

**Cách test chấm.** Không cần cluster cho hai test đầu; phần còn lại cần cluster `devops-lab` có ArgoCD (mục 0 của module).

| Bước | Test làm | Kiểm |
| --- | --- | --- |
| Tĩnh | Đọc `application.yaml` | `path: shop`, `targetRevision: main`, destination in-cluster và `LAB_NAMESPACE`, `automated` có `prune: true`, `selfHeal: true`, không plugin hay Helm |
| Tĩnh | `kubectl kustomize gitops/shop` trong sandbox | Có Deployment, Service của api và redis, ConfigMap `legacy-flags`, ConfigMap `olist-config-<hash>` với `APP_VERSION=1.0`; không ghi `namespace`; image đúng tag đã nạp vào cluster |
| Commit 1 | `KubeLab`: tạo AppProject của lab, đẩy `gitops/` lên git server của lab, apply Application bằng token của lab | `Synced` và `Healthy` trong 180 giây; `/healthz` của api trả version `1.0` |
| Commit 2 | Đóng vai đồng nghiệp: bỏ `legacy-flags.yaml` khỏi `resources` (xoá tệp), đổi `APP_VERSION=1.0` thành `1.1`, đẩy commit mới | ArgoCD sync đúng commit mới; api rollout, `/healthz` trả `1.1`; ConfigMap `legacy-flags` không còn |
| Drift | `kubectl scale deployment/api` lên số replica trong Git cộng 2 | Trong 90 giây replicas quay về giá trị trong Git |

Starter fail ở bước tĩnh và test không chờ ArgoCD. Bản đúng chạy khoảng 1 phút 10 giây.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được ba đường đi của một thay đổi: commit trong Git, object bị xoá khỏi Git, sửa tay trên cluster; mỗi đường thì ArgoCD làm
  gì khi bật và khi tắt `prune`, `selfHeal`.
- Nói được vì sao `configMapGenerator` có hậu tố hash làm api rollout khi đổi cấu hình, còn ConfigMap viết tay thì không.

## Gợi ý

### Gợi ý 1

Trạng thái của Application nằm trong chính object: `kubectl get applications.argoproj.io olist-shop -o yaml` rồi đọc `status.sync`,
`status.health`, `status.operationState`. Bản core của ArgoCD không có UI, `kubectl` là đủ.

### Gợi ý 2

`spec.syncPolicy.automated` là một object; `prune` và `selfHeal` là hai trường của nó, mặc định `false`. `spec.source.path` tính từ gốc
repo, tức là gốc thư mục `gitops/`.
