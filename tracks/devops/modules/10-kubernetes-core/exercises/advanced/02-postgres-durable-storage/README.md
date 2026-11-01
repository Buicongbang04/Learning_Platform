---
title: Postgres bền trên volume local, backup bằng CronJob, restore bằng Job
level: advanced
services: []
files:
  - path: starter/k8s/postgres.yaml
    note: StatefulSet đang dùng emptyDir
  - path: starter/k8s/backup.yaml
    note: PVC và CronJob backup
  - path: starter/restore/pg-restore.yaml
    note: Job restore, chỉ apply khi cần
  - path: tests/fixtures/secret.yaml
    note: Secret olist-db do test tạo
  - path: tests/test_postgres_durable_storage.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/10-kubernetes-core/exercises/advanced/02-postgres-durable-storage -q -rs
---

## Mục tiêu

Làm chủ đường đi của dữ liệu trong Kubernetes: PV tĩnh do admin cấp và PVC bind vào nó qua StorageClass, PV động do provisioner
tạo, reclaim policy, StatefulSet giữ volume qua lần pod bị tạo lại, rồi backup và restore có kiểm chứng bằng Job và CronJob.

## Đề bài

Admin của cluster đã cấp cho namespace của bạn một ổ local 1Gi trên `devops-lab-worker`: PV có `storageClassName: olist-local`,
`accessModes: [ReadWriteOnce]`, reclaim `Retain`, giữ sẵn (`claimRef`) cho PVC `data-postgres-0`. Bạn **không** tạo PV hay
StorageClass (quyền của bạn không có, giống ở công ty).

1. `starter/k8s/postgres.yaml`: StatefulSet `postgres` dùng volume đó cho `/var/lib/postgresql/data` (`PGDATA` là thư mục con
   `pgdata`). Service `postgres` headless có sẵn. Biến `POSTGRES_*` lấy từ Secret `olist-db` (test tạo).
2. `starter/k8s/backup.yaml`: PVC `pg-backups` (StorageClass `standard`, 1Gi, ReadWriteOnce) và CronJob `pg-backup` chạy `pg_dump
   -Fc` (image `postgres:16.15-alpine`) mỗi đêm vào PVC đó, giữ 7 bản mới nhất. `concurrencyPolicy: Forbid`, có
   `startingDeadlineSeconds`; Job có `activeDeadlineSeconds` và `backoffLimit` từ 1 tới 3; mật khẩu từ Secret.
3. `starter/restore/pg-restore.yaml`: Job `pg-restore` khôi phục bản dump mới nhất trong `pg-backups` vào Postgres (xoá object
   hiện có trước khi tạo lại). Tệp này không apply cùng `k8s/`; người trực apply khi cần.

**Cách test chấm.** Test gọi `lab.admin_local_pv(...)` để cấp PV, tạo Secret `olist-db` từ `tests/fixtures/secret.yaml`, apply
`k8s/` rồi:

| Bước | Test kiểm |
| --- | --- |
| Rollout | `statefulset/postgres` rollout xong; PVC `data-postgres-0` Bound **vào đúng PV admin cấp**; pod chạy trên `devops-lab-worker` |
| Bền | Tạo bảng `marker` có một dòng; xoá pod `postgres-0`; pod mới (uid khác) vẫn đọc được dòng đó |
| CronJob an toàn | `concurrencyPolicy: Forbid`, có `startingDeadlineSeconds`, `activeDeadlineSeconds`, `backoffLimit` 1 tới 3, không có mật khẩu trong spec, Job mount một PVC |
| Backup, restore | `kubectl create job pg-backup-now --from=cronjob/pg-backup` Complete; `drop table marker`; apply `restore/`; Job `pg-restore` Complete; bảng `marker` trở lại với đúng dòng cũ |

Khoảng 1 phút. Bài dùng PV của admin trên một worker cố định; không chạy song song với bài khác dùng `node_action`.

## Tiêu chí đạt

- Mọi test pass.
- Trả lời được (ghi vào ghi chú của bạn, chấm theo rubric trong `SOLUTION.md`): `devops-lab-worker` chết hẳn thì Postgres thế nào và
  RTO của thiết kế này là bao nhiêu; reclaim `Retain` khác `Delete` ra sao khi ai đó xoá namespace; bản dump nằm cùng cluster thì bảo
  vệ được trước những sự cố nào và không bảo vệ được trước sự cố nào.

## Gợi ý

### Gợi ý 1

PVC bind vào PV khi khớp `storageClassName`, `accessModes`, dung lượng; PV có `claimRef` thì chỉ bind với đúng PVC đó. PVC sinh từ
`volumeClaimTemplates` tên `<template>-<statefulset>-<số>`. PV `local` có nodeAffinity, nên scheduler đặt pod lên đúng node có ổ.

### Gợi ý 2

`pg_dump -Fc` cho bản dump nén, `pg_restore --clean --if-exists` xoá object cũ rồi tạo lại. Ghi ra `<tên>.part` rồi `mv` để bản dump
dở dang không bao giờ trông như bản tốt nhất. `kubectl create job --from=cronjob/...` chạy CronJob ngay, không chờ lịch.
