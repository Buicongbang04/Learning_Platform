# Lời giải: HPA theo CPU cho API

Lời giải nằm trong `k8s/api.yaml`, `k8s/hpa.yaml`. Starter có ba lỗi:

1. Container chỉ có `limits.memory`, không có `requests.cpu`. CPU `Utilization` là phần trăm **của request**, nên HPA báo
   `FailedGetResourceMetric: missing request for cpu` và đứng yên, dù metrics-server có số. Bài mẫu đặt `requests.cpu: 100m`, `limits.cpu:
   500m`.
2. HPA trỏ `olist-api`, Deployment không tồn tại: `ScalingActive False, FailedGetScale`.
3. HPA thiếu metric và behavior; Deployment còn `replicas: 2`.

HPA mẫu: min 1, max 4, CPU 60%, `scaleUp` không chờ, tối đa 2 pod mỗi 15 giây; `scaleDown` cửa sổ 30 giây, cho bớt 100% mỗi 15 giây.

## Công thức

`desired = ceil(current × currentUtilization / target)`. Hai pod, request 100m, mỗi pod dùng 150m: utilization 150%, `ceil(2 × 150 / 60) =
5`, bị chặn ở max 4. Lệch dưới 10% thì bỏ qua (tolerance) để không dao động.

## Vì sao bỏ `spec.replicas`

HPA ghi số replica vào `spec.replicas` của Deployment. Manifest còn `replicas: 2` thì mỗi `kubectl apply` hay `helm upgrade` kéo về 2 (giữa
đỉnh tải là cắt nửa capacity), rồi HPA kéo lên lại. Bỏ trường đó: lần tạo đầu Deployment mặc định 1, sau đó HPA quản. Với Helm, chart thường
có `{{- if not .Values.autoscaling.enabled }} replicas: ... {{- end }}`.

## Vì sao production giữ cửa sổ scale-down dài

Tải web dao động theo phút; thu nhỏ sau 30 giây thì đợt tải kế tiếp gặp ít pod hơn, pod mới mất thời gian khởi động và làm ấm cache. Mặc định
300 giây lấy mức cao nhất trong 5 phút. Scale-up nên nhanh, scale-down nên chậm.

## Số đo trên `devops-lab`

metrics-server 0.9.1, `--metric-resolution=15s`, HPA sync 15 giây: số liệu đầu tiên sau 26 giây, lên 2 replica sau 31 giây có tải và chạm 4,
về 1 sau 72 giây hết tải. Trên cluster thật thêm thời gian kéo image và Cluster Autoscaler thêm node (vài phút), nên đặt HPA đủ sớm (mục tiêu
60 tới 70%, không 90%) và có `minReplicas` chịu được đợt tăng đầu tiên.
