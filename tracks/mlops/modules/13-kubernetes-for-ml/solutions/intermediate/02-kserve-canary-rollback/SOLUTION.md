# Lời giải: canary trên KServe RawDeployment

Xem `canary.yaml` và `rollback.yaml`.

- Hai InferenceService, mỗi cái gắn nhãn chung `eta-traffic: "on"` qua `spec.predictor.labels`; Service `eta` chọn theo nhãn đó. kube-proxy chọn ngẫu nhiên đều giữa các Endpoints cho mỗi kết nối mới, nên 1 pod v2 trên 4 pod là ~25%.
- Rollback: annotation `serving.kserve.io/stop: "true"` trên `eta-canary`. KServe xoá Deployment predictor của nó (giải phóng tài nguyên) nhưng giữ InferenceService; bật lại bằng cách bỏ annotation. Cách khác: đổi nhãn của canary (`eta-traffic: "off"`), pod vẫn chạy ấm nên bật lại tức thì, đổi lại vẫn tốn tài nguyên. Không xoá InferenceService: mất spec đã duyệt, bật lại phải apply lại từ đầu.

## Giới hạn của chia theo replica

- Độ mịn: 1 trên N pod. Muốn 5% cần 19 pod stable. Chia chính xác cần L7 (Gateway API `HTTPRoute` với `weight`, Istio) hoặc chế độ Serverless của KServe.
- kube-proxy cân bằng theo **kết nối**: client giữ kết nối lâu (HTTP keep-alive, gRPC) có thể dính một pod mãi. Test dùng `Connection: close` để mỗi request là một kết nối.
- Tỉ lệ thực tế dao động; với 200 request, độ lệch chuẩn của số request v2 là căn của 200 × 0,25 × 0,75, khoảng 6, nên test cho khoảng 10-45%.

## Vì sao không dùng `canaryTrafficPercent`

Ở Serverless, KServe giữ revision cũ và mới trên Knative, rồi chia traffic theo phần trăm. Ở RawDeployment không có revision: trường bị bỏ qua, Deployment rolling update, 100% sang bản mới; kiểm bằng `kubectl get pods` sẽ thấy pod cũ bị thay hết. Đọc chế độ deploy của cluster (`inferenceservice-config`, `deploy.defaultDeploymentMode`) trước khi tin một trường trong spec.
