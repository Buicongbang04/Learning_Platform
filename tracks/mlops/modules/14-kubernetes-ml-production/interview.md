# Câu hỏi phỏng vấn: Kubernetes cho ML production

## 1. HPA của service model đặt theo CPU 70% nhưng p95 vẫn vượt SLO lúc đỉnh mà không thêm replica. Bạn chẩn đoán thế nào?

So CPU với latency theo thời gian: nếu CPU thấp mà p95 cao thì pod đang chờ (GPU, feature store, I/O), CPU không phản ánh tải. Xem `kubectl describe hpa` (giá trị hiện tại, event), metric in-flight hoặc độ dài hàng đợi trong server. Đổi tín hiệu sang in-flight mỗi pod (Prometheus + adapter hoặc KEDA), mục tiêu từ số đo capacity; kiểm cả `maxReplicas` và ResourceQuota (HPA muốn thêm pod nhưng quota chặn thì ReplicaSet có event `exceeded quota`). Nếu latency cao vì phụ thuộc chậm thì thêm replica không giúp.

## 2. Khi nào scale một model về 0, khi nào không?

Về 0 khi model ít dùng, traffic theo đợt, chịu được cold start (batch, nội bộ), và tài nguyên rảnh đắt (GPU). Không về 0 khi có SLO latency cho request đầu, hoặc cold start dài (image và model lớn). Điều kiện kỹ thuật: metric kích hoạt phải đến từ thứ sống khi không có pod (hàng đợi, lag, proxy giữ request). Thường có lựa chọn thứ ba tốt hơn: gộp nhiều model ít dùng vào một server multi-model luôn chạy.

## 3. Cold start 0 → 1 của một model là 60 giây. Bạn giảm nó thế nào?

Đo từng thành phần trước: chờ phát hiện tải, xếp pod (có node chưa?), kéo image, tải model, nạp và warm-up. Tối ưu thành phần lớn nhất ở p95, không phải p50: pre-pull hoặc image nhỏ hơn, cache model trên node, định dạng nạp nhanh, `pollingInterval` ngắn hoặc proxy, node ấm (overprovisioning). Đặt SLO cho cold start và dừng khi đạt. Nếu không đạt với chi phí hợp lý thì giữ `minReplicaCount: 1` cho model đó.

## 4. KEDA khác HPA thế nào? Khi nào cần KEDA?

HPA scale 1..N theo metric qua metrics API, không về 0. KEDA là operator: đọc trigger từ nhiều nguồn (Kafka, Prometheus, Redis, HTTP endpoint...), tạo HPA với metric external do nó phục vụ, và tự đưa 0 ↔ 1. Cần KEDA khi muốn scale theo nguồn ngoài cluster/hàng đợi mà không dựng prometheus-adapter, hoặc khi cần scale-to-zero cho Deployment mà không dùng Knative.

## 5. Làm sao biết một service cần bao nhiêu replica cho 1 000 req/s?

Đo capacity một pod: tải mở (`constant-arrival-rate`) tăng dần tới khi p95 chạm SLO, lấy req/s đó làm `r` (đi qua Service hoặc NodePort, không qua port-forward). Số replica là `ceil(1000 / r)` cộng dự phòng (mất node, rolling update, `maxUnavailable`). Đặt đó làm mức tối thiểu ở giờ đỉnh, autoscale phần trên, rồi load test lại ở 1 000 req/s để kiểm. Đo lại khi model đổi.

## 6. Dynamic batching của Triton đổi gì lấy gì? Bạn chỉnh nó thế nào?

Đổi một phần latency (thời gian chờ gộp, `max_queue_delay_microseconds`) lấy thông lượng: một lần chạy model phục vụ nhiều request, rất lợi trên GPU. Chỉnh: đo p95 và thông lượng khi chưa bật; bật với delay nhỏ trong ngân sách latency; xem `nv_inference_exec_count` so với `nv_inference_request_success` và `queue_duration`; tăng `instance_group.count` khi một instance bão hoà; `preferred_batch_size` theo kích thước model chạy hiệu quả.

## 7. Kubernetes biết GPU qua cơ chế nào? Một pod có xin được nửa GPU không?

Device plugin (thường qua GPU Operator) quảng bá extended resource `nvidia.com/gpu` trên node và gắn thiết bị vào container. Extended resource là số nguyên, khai ở limits, không overcommit: không xin được 0,5. Chia GPU cần cơ chế riêng: time-slicing (plugin quảng bá mỗi card thành N bản, không cô lập bộ nhớ), MPS, hoặc MIG trên A100/H100 (chia phần cứng, cô lập thật, profile cố định như `mig-1g.10gb`). DRA là hướng mới cho thiết bị chi tiết hơn.

## 8. Vì sao cần Kueue khi đã có scheduler và ResourceQuota?

Scheduler xếp từng pod ngay khi có chỗ: job nhiều worker có thể chạy một phần và giữ GPU chờ phần còn lại. ResourceQuota từ chối pod ngay chứ không xếp hàng, và không có khái niệm mượn giữa đội. Kueue admission theo cả job (gang ở mức quota), xếp hàng có thứ tự, quota theo flavor, cohort cho mượn/đòi lại, preemption theo workload. Nó không thay scheduler: chỉ quyết định khi nào job bắt đầu.

## 9. Sự cố: job training có nhãn Kueue không có pod nào sau nhiều giờ, cluster rảnh. Bạn làm gì?

Không có pod thì không phải lỗi scheduler. `kubectl get job -o jsonpath='{.spec.suspend}'` (vẫn `true`), `kubectl get workloads`, `describe workload`: đọc condition `QuotaReserved` và message. Các nguyên nhân hay gặp: requests (gồm init container, tính `max`) × số pod vượt quota tối đa (`ExceedsMaxQuota`), resource không thuộc `coveredResources` của ClusterQueue, `namespaceSelector` không chọn namespace, LocalQueue trỏ ClusterQueue không tồn tại, flavor không khớp node nào. Sửa xong, thêm kiểm tĩnh trong CI và cảnh báo workload kẹt.

## 10. Thiết kế quota GPU cho ba đội: một đội serving có SLO, một đội training dài có checkpoint, một đội research theo đợt.

Serving: node pool riêng (taint) hoặc quota cứng không cho mượn, PriorityClass cao nhất. Training và research: ClusterQueue mỗi đội trong một cohort, `nominalQuota` theo nhu cầu nền, `borrowingLimit` cho đội cần đợt lớn, `lendingLimit` để luôn còn chỗ cho đội mình, `reclaimWithinCohort` để chủ quota lấy lại; chỉ job checkpoint được mới nên mượn. Notebook: MIG thay vì time-slicing. Đo: GPU allocated so với utilization theo đội, thời gian chờ admission, số lần bị preempt.

## 11. PriorityClass với `preemptionPolicy: Never` dùng để làm gì?

Pod được xếp trước pod ưu tiên thấp hơn trong hàng chờ, nhưng scheduler không xoá pod nào để lấy chỗ cho nó. Hợp với tải quan trọng hơn training nhưng không đáng giết job dài: notebook, thử nghiệm tương tác, batch không gấp. Không bao giờ đặt `globalDefault: true` tuỳ tiện trên cluster dùng chung: nó áp cho mọi pod mới không khai class.

## 12. Bạn tách serving và training của cùng một đội bằng gì?

Hai namespace với ResourceQuota riêng: serving không được xin GPU training (`requests.<gpu>: 0` hoặc quota GPU serving riêng), training có quota GPU và đi qua Kueue. LimitRange đặt mặc định và trần cho từng namespace, vì quota CPU/RAM bắt mọi pod khai requests. Node pool/taint nếu hai loại tải cần phần cứng khác nhau. PriorityClass serving cao hơn training để thiếu chỗ thì serving thắng. NetworkPolicy để job training không gọi thẳng vào service production.

## 13. Load test cho thấy thêm replica từ 3 lên 6 mà thông lượng không đổi. Những nguyên nhân nào?

Client giữ ít kết nối keep-alive hoặc dùng HTTP/2/gRPC nên dính vào vài pod (kube-proxy cân bằng theo kết nối); đo qua `port-forward` (một pod); nút cổ chai ở phía sau (feature store, database, GPU dùng chung); CPU limit làm throttle; máy sinh tải bão hoà (k6 hết CPU); pod mới chưa Ready hoặc kube-proxy chưa cập nhật. Kiểm từng cái bằng số: phân bố request theo pod, CPU của k6, metric của phụ thuộc, `container_cpu_cfs_throttled_seconds_total`.

## 14. Một add-on (Kueue, KServe) có webhook `failurePolicy: Fail`. Rủi ro là gì và bạn giảm nó thế nào?

Khi controller của add-on chết hoặc chưa lên, mọi request khớp webhook bị từ chối, kể cả workload không dùng add-on (Kueue chặn mọi `batch/v1` Job). Sau một lần node khởi động lại, job của mọi người lỗi. Giảm: giới hạn phạm vi webhook (`namespaceSelector`, `objectSelector`, chỉ bật integration cần), chạy nhiều replica controller với PodDisruptionBudget, giám sát độ trễ và lỗi của webhook, runbook "chờ controller Available"; với webhook không bắt buộc an toàn thì cân nhắc `Ignore`.
