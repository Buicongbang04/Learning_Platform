# Lời giải: kế hoạch chuyển ETA sang Kubernetes

## Hướng làm

Không có đáp án duy nhất. Một kế hoạch tốt bắt đầu từ thành phần có trạng thái, chuyển từng phần có đường lùi, và đo bằng request thật.

## Ánh xạ tham khảo

| Compose | Kubernetes | Lý do, đánh đổi |
| --- | --- | --- |
| `api` | InferenceService custom predictor (hoặc Deployment + Service) | KServe chuẩn hoá đường `/v1/models/...`, nhãn, Service; đổi lại thêm một CRD phải vận hành |
| `mlflow` | Deployment + Service, image ghim | Không trạng thái nếu backend và artifact ở ngoài |
| `postgres` | Managed database (RDS/Cloud SQL) hoặc StatefulSet + PVC + backup | Chạy database trong cluster nghĩa là tự lo backup, nâng cấp, failover |
| `minio` | Object storage của cloud (S3/GCS) | Như trên; trên kind dùng MinIO trong cluster cho dev |
| Prometheus/Grafana | kube-prometheus-stack (Helm, track DevOps) | Không dạy lại |
| cron retrain | Argo `CronWorkflow` (prepare → train → evaluate → register) | Retry, artifact, lịch sử chạy, log trong cluster |

## Model và cấu hình

- Model nạp từ registry theo **version cố định** (không phải alias) ghi trong ConfigMap hoặc spec; đổi model là một commit, rollback là commit ngược. Alias `champion` chỉ để pipeline quyết định version nào sẽ được ghi vào manifest.
- Secret: thông tin đăng nhập MLflow/S3 trong Secret (hoặc External Secrets), không trong ConfigMap; không đưa vào image.
- Sau mỗi deploy: smoke test gọi `/v1/models/eta` và một `predict` mẫu qua Service, so `model_version` với version mong đợi; sai thì rollback tự động.

## Probe và tài nguyên

- startupProbe với ngân sách gấp đôi thời gian nạp đo được; readiness kiểm model đã nạp; liveness chỉ kiểm tiến trình, không kiểm MLflow/Postgres.
- requests/limits lấy từ **số đo**: chạy pod ở staging với limit rộng, đo bộ nhớ cao nhất trong suốt vòng đời (từ lúc khởi động tới lúc chịu tải, qua `container_memory_working_set_bytes` của cAdvisor hoặc `kubectl top` khi có metrics-server), CPU p95 lúc tải; requests quanh mức dùng thường, limit bộ nhớ có dư so với mức cao nhất đo được. Đo lại khi model đổi kích thước.

## Phát hành

- Canary trên RawDeployment: hai InferenceService (`eta-stable`, `eta-canary`) sau một Service chung theo nhãn; tỉ lệ theo số replica (1/4 = 25%). Muốn tỉ lệ chính xác hơn (1%) cần Gateway API/Istio hoặc chuyển sang Serverless.
- Điều kiện: tăng khi tỉ lệ lỗi và p95 của canary không xấu hơn stable trong N phút với đủ request; rút về 0% (stop annotation hoặc bỏ nhãn) khi vượt ngưỡng. Rollback mục tiêu dưới 2 phút.

## Bước chuyển

1. Dựng staging trên K8s dùng chung Postgres/MinIO hiện tại; chạy song song, so dự đoán (shadow) 1 tuần.
2. Chuyển pipeline training sang Argo, giữ cron cũ ở chế độ chỉ đọc để so kết quả.
3. Chuyển traffic API theo phần trăm ở load balancer phía trước; dừng nếu lỗi hoặc `model_version` lệch.
4. Tắt Compose sau 2 tuần ổn định; giữ khả năng bật lại 1 tháng.

## Rubric (tối đa 20 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Ánh xạ đủ thành phần, có quyết định rõ cho Postgres/MinIO kèm đánh đổi | 4 |
| Đường đi của model và cách kiểm `model_version` sau deploy | 3 |
| Probe đúng vai trò; requests/limits dựa trên số đo trong suốt vòng đời pod, không đoán | 3 |
| Canary khả thi trên RawDeployment, có điều kiện tăng/rút và rollback cụ thể | 4 |
| Pipeline training trên Argo có retry, artifact, parameter, ghi registry | 3 |
| Bước chuyển có chạy song song, tiêu chí dừng và đường lùi | 3 |

Từ 14 điểm trở lên là đạt.
