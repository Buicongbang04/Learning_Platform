# Lời giải: trắc nghiệm Kubernetes cho ML

- **devops-inherited**: RBAC, NetworkPolicy và Helm là K8s chung, học ở track DevOps (module 10-12). Probe cho model nạp chậm và KServe là phần riêng của ML, dạy ở module này.
- **raw-canary**: ở RawDeployment, KServe biến InferenceService thành một Deployment thường; `canaryTrafficPercent` cần Knative (chế độ Serverless) để chia traffic theo revision. Trường này không bị từ chối mà bị **bỏ qua**: Deployment rolling update và 100% traffic sang v2. Đây là lý do module dạy canary bằng hai InferenceService sau một Service chung (tỉ lệ theo số replica).
- **ready-not-enough**: Ready và Available chỉ nói container trả lời probe. Tag image đúng vẫn có thể nạp sai model (biến `MODEL_PATH`, ConfigMap, storageUri). Bằng chứng là một request thật trả `model_version` và dự đoán khớp model mong đợi.
- **gpu-request**: GPU là extended resource do device plugin quảng bá; khai trong `limits` (requests tự bằng limits), số nguyên. Chia GPU cần cơ chế riêng (time-slicing, MIG), không phải số thập phân. `nodeSelector` chỉ chọn node, không cấp card.
- **argo-vs-argocd**: Argo Workflows chạy DAG các pod (có `CronWorkflow` cho lịch); Argo CD so trạng thái cluster với Git và đồng bộ. Hai dự án khác nhau dưới cùng tổ chức Argo.
- **kind-scope**: kind chạy node K8s trong container Docker: tốt cho dev và CI. Không có GPU passthrough dễ dàng, không có LoadBalancer cloud, không phải môi trường production.
