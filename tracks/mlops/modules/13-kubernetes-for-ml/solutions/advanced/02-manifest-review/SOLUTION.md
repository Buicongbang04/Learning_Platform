# Lời giải: review manifest eta-api

## Các vấn đề

| # | Trường | Vấn đề | Hậu quả | Mức |
| --- | --- | --- | --- | --- |
| 1 | `Service.spec.selector: app: eta` | Không khớp nhãn pod `app: eta-api` | Service không có Endpoints, mọi request lỗi | Chặn |
| 2 | `Service targetPort: 8000` | Container nghe 8080 | Kể cả sửa selector vẫn `connection refused` | Chặn |
| 3 | `env MLFLOW_TRACKING_PASSWORD` | Mật khẩu production ghi thẳng trong manifest (và Git) | Lộ secret cho ai đọc repo hoặc `kubectl get deploy -o yaml` | Chặn |
| 4 | `image: ...:latest` + `Always` | Tag đổi được | Hai pod có thể chạy hai bản khác nhau; rollback không biết về đâu; registry chết thì pod mới không lên | Chặn |
| 5 | `securityContext.privileged: true` | Service suy luận không cần quyền host | Bị khai thác là chiếm node | Chặn |
| 6 | `livenessProbe` gọi `/readyz?check=mlflow`, `failureThreshold: 1` | Liveness phụ thuộc MLflow, một lần trượt là giết | MLflow chậm 5 giây là mọi pod bị restart cùng lúc; model nạp lại, sự cố lan rộng | Chặn |
| 7 | `requests: nvidia.com/gpu: 1` | Service CPU xin GPU; extended resource phải nằm ở `limits` | Manifest bị từ chối, hoặc nếu sửa vào limits thì giữ một GPU vô ích | Chặn |
| 8 | `limits.cpu: 100m`, không có requests cpu/memory | CPU bị throttle ở 0,1 nhân; không requests nên QoS `BestEffort` | Latency predict tăng mạnh; pod bị đuổi đầu tiên khi node thiếu bộ nhớ | Nên sửa |
| 9 | `hostPath: /mnt/models` | Model nằm trên đĩa một node | Pod chuyển node là mất model; `current` là đường dẫn đổi được, không biết đang chạy version nào | Nên sửa |
| 10 | Thiếu `startupProbe`/`readinessProbe` | Không có tín hiệu "đã nạp model" | Service nhận request khi model chưa nạp | Nên sửa |
| 11 | `replicas: 1`, namespace `default` | Không chịu được một pod chết; trộn với tài nguyên khác | Downtime khi rollout/node drain; RBAC, quota khó tách | Nên sửa |
| 12 | `type: NodePort` | Mở cổng trên mọi node | Bề mặt tấn công; nên ClusterIP sau Ingress/Gateway | Gợi ý |

## Bản sửa (rút gọn)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eta-api
  namespace: eta
spec:
  replicas: 2
  selector:
    matchLabels: {app: eta-api}
  template:
    metadata:
      labels: {app: eta-api, tier: serving}
    spec:
      securityContext: {runAsNonRoot: true, runAsUser: 10001}
      containers:
        - name: api
          image: registry.example.com/eta-serve@sha256:<digest>
          envFrom:
            - configMapRef: {name: eta-api-config}
          env:
            - name: MLFLOW_TRACKING_PASSWORD
              valueFrom:
                secretKeyRef: {name: mlflow-credentials, key: password}
          ports:
            - {name: http, containerPort: 8080}
          startupProbe:
            httpGet: {path: /healthz, port: http}
            periodSeconds: 5
            failureThreshold: 24
          readinessProbe:
            httpGet: {path: /readyz, port: http}
            periodSeconds: 5
          livenessProbe:
            httpGet: {path: /healthz, port: http}
            periodSeconds: 10
            failureThreshold: 3
          resources:
            requests: {cpu: 250m, memory: 512Mi}
            limits: {cpu: "1", memory: 1Gi}
          securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true}
---
apiVersion: v1
kind: Service
metadata:
  name: eta-api
  namespace: eta
spec:
  selector: {app: eta-api}
  ports:
    - {name: http, port: 80, targetPort: http}
```

Số requests/limits ở trên là chỗ giữ; con số thật phải lấy từ đo đạc ở staging.

## Câu hỏi cho tác giả

- Model version nào sẽ chạy, ghi ở đâu, test sau deploy kiểm nó thế nào?
- Service cần ghi gì vào MLflow lúc chạy? Nếu chỉ đọc model thì có cần mật khẩu không?
- Đã đo bộ nhớ và CPU của service ở staging chưa, đo lúc nào?
- `/readyz?check=mlflow` có cần cho readiness không, hay model đã nạp sẵn thì không phụ thuộc MLflow nữa?

## Rubric (tối đa 20 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Tìm được 2 lỗi đường request (selector, targetPort) | 3 |
| Secret, privileged, tag mutable: nêu đúng và xếp chặn | 4 |
| Liveness phụ thuộc bên ngoài và hậu quả lan rộng | 3 |
| GPU sai chỗ và sai nhu cầu; requests/limits CPU/bộ nhớ | 3 |
| hostPath, thiếu startup/readiness, replicas | 3 |
| Bản sửa apply được, không lỗi mới, câu hỏi cho tác giả đúng chỗ thiếu thông tin | 4 |

Từ 14 điểm trở lên là đạt.
