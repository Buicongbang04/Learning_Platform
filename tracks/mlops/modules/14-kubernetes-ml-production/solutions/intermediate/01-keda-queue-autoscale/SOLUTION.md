# Lời giải: KEDA scale worker theo hàng đợi

Lời giải ở `scaledobject.yaml`:

```yaml
  minReplicaCount: 0
  maxReplicaCount: 4
  pollingInterval: 5
  cooldownPeriod: 20
  triggers:
    - type: metrics-api
      metadata:
        url: "http://batch-queue.__NAMESPACE__.svc.cluster.local:8080/pending"
        format: json
        valueLocation: pending
        targetValue: "10"
        activationTargetValue: "0"
```

- **Vì sao hàng đợi, không phải metric của worker**: ở 0 replica không có worker nào để xuất metric; hàng đợi luôn sống và biết có việc. KEDA hỏi nó mỗi `pollingInterval`, metric > `activationTargetValue` thì đưa 0 → 1, rồi HPA (do KEDA tạo) đưa 1 → `ceil(pending / 10)`, tối đa 4.
- **URL đầy đủ**: KEDA operator chạy ở namespace `keda`; tên ngắn `batch-queue` sẽ phân giải trong namespace `keda` và lỗi.
- **Cold start đo được** trên laptop: ~8–12 giây = chờ KEDA hỏi (0–5 s) + xếp pod và chạy container (~1–2 s, image đã có trên node) + nạp model 5 s. Thành phần lớn nhất là nạp model, sau đó là `pollingInterval`. Ở `pollingInterval` mặc định 30 thì chờ KEDA chiếm phần lớn.
- **Về 0**: `cooldownPeriod` chỉ áp cho bước 1 → 0, đếm từ lần cuối trigger active. Bước N → 1 do HPA quyết định, có `stabilizationWindowSeconds` mặc định 300 giây cho scale down; KEDA bỏ qua HPA khi đưa về 0, nên bài không cần chỉnh `advanced.horizontalPodAutoscalerConfig`.
- **Job đang chạy khi pod bị xoá**: worker nhận SIGTERM thì làm nốt job (`terminationGracePeriodSeconds: 10`); hàng đợi có lease, job lấy mà không báo xong trong `2 × thời gian + 10 s` được trả lại hàng đợi. Không có lease, một pod bị xoá giữa chừng làm `pending` không bao giờ về 0 và worker không bao giờ về 0.

Ngoài đời, hàng đợi là Kafka (trigger `kafka`, metric là consumer lag), Redis list, SQS, RabbitMQ. Với online serving cần scale về 0, dùng KEDA HTTP add-on hoặc Knative: một proxy giữ request trong lúc pod dậy.
