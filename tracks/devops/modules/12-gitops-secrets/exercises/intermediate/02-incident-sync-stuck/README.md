---
title: Sự cố - môi trường preview mới, sync kẹt mãi và commit mới không vào
level: intermediate
services: []
files:
  - path: starter/gitops/shop/migrate.yaml
    note: Job migrate schema
  - path: starter/gitops/shop/kustomization.yaml
    note: Kustomize của Olist Shop
  - path: starter/gitops/shop/postgres.yaml
    note: Postgres (bài này không dùng mật khẩu)
  - path: starter/gitops/shop/api.yaml
    note: api
  - path: starter/application.yaml
    note: Application
  - path: tests/fixtures/incident/application.yaml
    note: Bản lúc sự cố (cả thư mục incident), test dùng để tái hiện triệu chứng
  - path: tests/test_incident_sync_stuck.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/12-gitops-secrets/exercises/intermediate/02-incident-sync-stuck -q -rs
---

## Mục tiêu

Gỡ một lần sync của ArgoCD bị kẹt: đọc `operationState` của Application, lần từ thông điệp của ArgoCD xuống pod đang kẹt, hiểu vì sao
cùng một repo chạy ổn ở môi trường cũ mà kẹt ở môi trường mới, rồi sửa để sync tự hoàn tất trên namespace trống và hỏng thì hỏng nhanh.

## Đề bài

Team Olist Shop vừa thêm Job `migrate` (tạo schema) vào repo GitOps; trên staging, namespace đã chạy từ nhiều tháng, lần sync sau đó xong
trong một phút. Hôm nay team dựng một môi trường preview mới cho một pull request, namespace trống, cùng repo, cùng Application. Ghi nhận
của người trực:

1. `kubectl get applications.argoproj.io olist-shop`: sync `OutOfSync`, health `Missing`. `status.operationState.phase` là `Running` đã
   hơn 20 phút, `message` là `waiting for completion of hook batch/Job/migrate`.
2. `kubectl get pods`: chỉ có một pod `migrate-xxxxx`, trạng thái `CreateContainerConfigError`. Không có pod nào của api, postgres, redis.
3. Team đẩy commit đổi `APP_VERSION` sang `1.1` cho preview. Vài phút sau Application vẫn báo đang sync commit cũ
   (`operationState.operation.sync.revision` không đổi), không có gì mới được apply.
4. `kubectl describe pod migrate-xxxxx`: event `Error: configmap "olist-config-<hash>" not found`.
5. Ai đó đề xuất "xoá namespace rồi tạo lại"; làm thử thì y hệt.

Sửa `starter/` để:

| Yêu cầu | Chi tiết |
| --- | --- |
| Namespace trống | Sync tự hoàn tất, `Synced` và `Healthy` trong 4 phút |
| Thứ tự | `migrate` chạy mỗi lần sync và chỉ khi mọi thứ nó cần đã sẵn sàng; api không nhận traffic trước khi schema có |
| `migrate` vẫn là hook | Chạy lại mỗi lần sync; lần sync sau tạo lại được Job cùng tên |
| Hỏng thì hỏng nhanh | `backoffLimit` tối đa 2, `activeDeadlineSeconds` tối đa 300 (mặc định Job thử 6 lần, kéo hơn 6 phút; Job không có hạn thì treo mãi) |
| Thử lại có giới hạn | `syncPolicy.retry` với `limit` từ 1 tới 5 và có `backoff` |
| Commit tiếp theo | `APP_VERSION=1.1` được sync, api trả version mới |

Viết postmortem ngắn (không chấm tự động): nguyên nhân gốc, vì sao staging không lộ ra, vì sao commit mới không cứu được, và lần sau phát
hiện sớm hơn thế nào.

**Cách test chấm.**

| Test | Cần cluster | Kiểm |
| --- | --- | --- |
| `test_sync_order_satisfies_migrate_dependencies` | Không | Render Kustomize: `migrate` là hook; theo đúng thứ tự ArgoCD áp object (phase rồi sync wave), thứ `migrate` cần đứng trước nó và api đứng sau nó |
| `test_migration_fails_fast_and_reruns` | Không | `backoffLimit` ≤ 2, `activeDeadlineSeconds` từ 1 tới 300, `hook-delete-policy` có `BeforeHookCreation` |
| `test_application_retries_bounded` | Không | `retry.limit` từ 1 tới 5, có `retry.backoff.duration` |
| `test_fresh_namespace_syncs` | Có | Lab mới (namespace trống): `Synced`, `Healthy` trong 240 giây; kết quả sync có Job `migrate` `Succeeded` |
| `test_next_commit_deploys` | Có | Đẩy commit đổi `APP_VERSION=1.0` thành `1.1` (giữ `configMapGenerator` `olist-config` có literal này): sync đúng commit mới, `/healthz` của api trả `1.1` |
| `test_incident_reproduces_symptoms` | Có | Lab thứ hai chạy `tests/fixtures/incident/` (giống starter): trong 90 giây thao tác sync `Running` chờ `migrate`, pod `migrate` lỗi hay kẹt; đẩy commit mới, 25 giây sau thao tác cũ vẫn chạy trên commit cũ; chưa có Deployment api |

Khoảng 2 phút khi đã sửa; starter fail các test của bản sửa trong khoảng 2 phút 20 giây.

## Tiêu chí đạt

- Mọi test pass, kể cả ca tái hiện.
- Postmortem giải thích được triệu chứng 1, 3 và 5 bằng cùng một nguyên nhân.
- Nói được cách huỷ một thao tác sync đang kẹt trên cluster thật mà không xoá namespace, và ai có quyền làm việc đó.

## Gợi ý

### Gợi ý 1

`kubectl get applications.argoproj.io olist-shop -o jsonpath='{.status.operationState}'` cho biết thao tác nào đang chạy, trên revision
nào, đang chờ gì. Rồi `kubectl kustomize gitops/shop` để thấy đúng thứ ArgoCD render, kể cả tên ConfigMap có hậu tố hash và annotation
của từng object.

### Gợi ý 2

Liệt kê những gì pod `migrate` cần để chạy được, rồi hỏi: trên một namespace trống, lúc ArgoCD tạo Job này thì những thứ đó đã tồn tại
chưa? Tài liệu "Sync Phases and Waves" và "Resource Hooks" của ArgoCD nói rõ ArgoCD áp object theo thứ tự nào.
