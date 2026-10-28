---
title: Manifest Kubernetes CronJob cho job ingest Olist
level: intermediate
services: []
files:
  - path: starter/k8s.yaml
    note: 7 TODO
  - path: tests/test_k8s_cronjob.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/intermediate/02-k8s-cronjob -q
---

## Mục tiêu

Viết được manifest Kubernetes cho một job dữ liệu chạy theo lịch: tách cấu hình (ConfigMap) và bí
mật (Secret), giới hạn tài nguyên, không chạy chồng, retry có giới hạn và chạy non-root.

## Đề bài

Image `ghcr.io/acme/olist-ingest:1.4.0` nạp đơn hàng Olist mỗi giờ vào PostgreSQL. Hoàn thiện
`starter/k8s.yaml` gồm 3 tài liệu YAML (ngăn bởi `---`), tất cả trong namespace `data`:

1. **ConfigMap** `olist-ingest-config` với `TARGET_SCHEMA: staging` và `BATCH_SIZE: "5000"`
   (giá trị trong ConfigMap phải là chuỗi).
2. **Secret** `olist-db` kiểu `Opaque`, dùng `stringData` chứa `DB_PASSWORD` (giá trị bất kỳ cho
   môi trường dev).
3. **CronJob** `olist-ingest` (`apiVersion: batch/v1`):
   - chạy đầu mỗi giờ (`0 * * * *`), `concurrencyPolicy: Forbid`;
   - `jobTemplate.spec.backoffLimit` từ 1 tới 5;
   - Pod `restartPolicy: OnFailure`, `securityContext.runAsNonRoot: true` (ở cấp Pod hoặc container);
   - container dùng image ở trên (có tag, không `latest`), `envFrom` tham chiếu **đúng tên**
     ConfigMap và Secret ở trên;
   - `resources.requests` và `resources.limits` đều có `cpu` và `memory`.

## Tiêu chí đạt

- Parse được bằng `yaml.safe_load_all`, có đúng 3 tài liệu với kind ConfigMap, Secret, CronJob,
  cùng namespace `data`.
- ConfigMap có hai khoá trên, mọi giá trị là chuỗi.
- Secret dùng `stringData` có `DB_PASSWORD`.
- CronJob có schedule `0 * * * *`, `concurrencyPolicy: Forbid`, `backoffLimit` 1–5.
- Pod: `restartPolicy: OnFailure`, `runAsNonRoot: true`.
- Container: image có tag khác `latest`, `envFrom` khớp tên ConfigMap và Secret, có requests và
  limits cho cả cpu lẫn memory.

## Gợi ý

### Gợi ý 1

Cấu trúc lồng: `CronJob.spec.jobTemplate.spec.template.spec.containers[]`. CronJob → Job → Pod.

### Gợi ý 2

`BATCH_SIZE: 5000` không ngoặc là số nguyên trong YAML, Kubernetes sẽ từ chối ConfigMap. Viết
`"5000"`. `envFrom` là một list: `- configMapRef: {name: ...}` và `- secretRef: {name: ...}`.
