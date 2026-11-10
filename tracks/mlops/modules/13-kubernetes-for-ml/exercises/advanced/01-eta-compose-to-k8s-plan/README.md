---
title: Kế hoạch chuyển ETA từ Compose sang Kubernetes
level: advanced
services: []
files:
  - path: starter/PLAN.md
    note: Khung kế hoạch của bạn
run: []
---

## Mục tiêu

Viết kế hoạch chuyển một hệ ML đang chạy bằng Docker Compose sang Kubernetes như một kỹ sư sẽ trình cho đội: từng thành phần đi đâu, đánh đổi nào, chuyển theo bước nào, khi nào dừng lại.

## Đề bài

Dịch vụ ETA của capstone hiện chạy bằng `setup/mlops/compose.yaml` và compose của dự án: API FastAPI (model sklearn ~30 MB nạp từ MLflow registry theo alias `champion`), MLflow server + Postgres + MinIO, Prometheus/Grafana, một cron trên máy chủ chạy script retrain hằng đêm. Đích: một cluster K8s có KServe (RawDeployment) và Argo Workflows như cluster kind của module. Viết `starter/PLAN.md` theo khung có sẵn:

1. **Ánh xạ object**: mỗi service Compose thành gì (Deployment, StatefulSet, InferenceService, Job/CronWorkflow, managed service ngoài cluster), có bảng và lý do. Nói rõ Postgres/MinIO có nên chạy trong cluster không.
2. **Cấu hình, secret, model**: ConfigMap/Secret nào; model đến pod bằng đường nào (đóng vào image, `storageUri`, tải từ MLflow lúc khởi động); `model_version` được kiểm sau deploy thế nào.
3. **Probe và tài nguyên**: startup/readiness/liveness cho API; cách bạn chọn số requests/limits (đo gì, ở đâu, lúc nào), không đoán.
4. **Phát hành và rollback**: canary trên RawDeployment (không có `canaryTrafficPercent`), điều kiện tăng hay rút canary, thời gian rollback mục tiêu.
5. **Pipeline training**: cron thành Argo `CronWorkflow` với DAG, artifact, retry, parameter; chỗ ghi model vào registry.
6. **Các bước chuyển**: thứ tự, chạy song song Compose và K8s bao lâu, điều kiện dừng/quay lại.
7. **Những gì chưa làm**: GitOps (Argo CD), autoscale, GPU: làm lúc nào, vì sao chưa.

## Tiêu chí đạt

- Mỗi quyết định có lý do và một đánh đổi; có ít nhất hai sơ đồ hoặc bảng.
- Có cách kiểm `model_version` sau mỗi lần deploy và cách rollback cụ thể (lệnh, thời gian).
- Tự chấm theo rubric trong `SOLUTION.md`, đạt từ 14/20.

## Gợi ý

### Gợi ý 1

Bắt đầu từ thành phần có trạng thái (Postgres, MinIO): chúng quyết định độ khó của cả kế hoạch hơn là API.

### Gợi ý 2

Mỗi bước chuyển cần một con số để biết thành công (tỉ lệ lỗi, p95, `model_version` đúng) và một đường lùi.
