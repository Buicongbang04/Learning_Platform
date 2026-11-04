# Lời giải: thiết kế multi-tenant GPU cho 3 đội

## Hướng làm

Không có đáp án duy nhất. Thiết kế tốt bắt đầu từ SLO chặt nhất (serving GPU của recommendation lúc đỉnh), giữ cứng phần đó, rồi cho phần còn lại chảy qua hàng đợi có mượn và đòi lại. Mỗi quyết định gắn với một metric để biết nó có đúng không.

## Một phương án tham khảo

**Ranh giới.** Mỗi đội 2–3 namespace (`<team>-serving`, `<team>-training`, `research-notebooks`). Node pool: `gpu-serving` (1 node, 8 card nguyên, taint `workload=serving:NoSchedule`), `gpu-batch` (2 node, 16 card nguyên), `gpu-research` (1 node: 4 card bật MIG chia 28 slice `1g.10gb` cho notebook, 4 card nguyên cho thử nghiệm), `cpu` (6 node). Một cluster chung vì GPU khó chia nếu tách cluster (mỗi cluster phải tự giữ dư); cluster riêng chỉ khi có yêu cầu tuân thủ.

| Đội | Serving (card nguyên, node `gpu-serving`) | ClusterQueue batch (card) | borrowingLimit | lendingLimit | Lý do |
| --- | --- | --- | --- | --- | --- |
| Recommendation | 6 (đỉnh 2 000 req/s, đo capacity mỗi card) | 8 | 8 | 8 | Fine-tune 16 GPU cần mượn; checkpoint 30 phút nên chịu bị lấy lại |
| Search | 2 (model nhỏ, có thể chạy CPU phần lớn) | 8 | 0 | 8 | Retrain 8 GPU đêm vừa quota; không cần mượn |
| Research | 0 | 8 (node `gpu-research`: 4 card nguyên + 28 slice MIG) | 8 | 4 | Đợt ngắn, chịu bị lấy lại; chỉ cho mượn 4 card nguyên, slice MIG của notebook không cho mượn |

Tổng: 8 (serving) + 8 (recommendation) + 8 (search) + 8 (research) = 32 card. Slice MIG là một ResourceFlavor riêng (`nvidia.com/mig-1g.10gb`), chỉ ClusterQueue research có quota cho nó. Một cohort `ml` cho cả ba ClusterQueue batch; `reclaimWithinCohort: Any` cho search và recommendation, `LowerPriority` cho research (research không giết job training dài trừ khi ưu tiên thấp hơn).

**Ưu tiên.** PriorityClass pod: `serving-critical` (1 000 000) > `batch-deadline` (10 000) > `training` (1 000) > `research` (500, `preemptionPolicy: Never` cho notebook). WorkloadPriorityClass Kueue: retrain đêm của search (cao, có hạn sáng) > fine-tune recommendation > thử nghiệm research. Job bị đẩy ra mất tối đa 30 phút (checkpoint); job không checkpoint không được mượn (chính sách, kiểm bằng nhãn hoặc admission policy).

**Chia GPU.** Serving và training: card nguyên. Notebook: MIG `1g.10gb` (cô lập bộ nhớ thật) thay vì time-slicing (một notebook OOM kéo người khác). Time-slicing chỉ cho môi trường dev không ai quan tâm hiệu năng.

**Serving.** Autoscale theo in-flight mỗi pod (Prometheus + KEDA), mục tiêu từ số đo capacity; `minReplicaCount` bằng đáy đêm, không về 0 (SLO 50 ms). Node `gpu-serving` giữ cứng 8 card cho serving: đỉnh tối không phải tranh với training. Ngoài giờ đỉnh có thể cho Kueue mượn bằng một ClusterQueue `serving-spare` chỉ nhận job chịu bị đẩy ra trong vài phút.

**Bảo vệ và quan sát.** RBAC: đội chỉ tạo Job/LocalQueue trong namespace mình (`kueue-batch-user-role`); ClusterQueue, PriorityClass chỉ đội platform (GitOps). NetworkPolicy mặc định chặn giữa namespace của đội khác nhau. Metric: GPU allocated vs DCGM utilization theo đội (card giữ mà không dùng), thời gian chờ admission p50/p95 theo ClusterQueue, số workload bị evict theo đội, tỉ lệ quota mượn. Báo cáo hằng tuần cho các trưởng nhóm.

**Mùa deadline.** Tăng `nominalQuota` của research bằng một thay đổi GitOps có ngày hết hạn, do trưởng nhóm ba đội đồng ý; recommendation dời fine-tune; quay lại tự động bằng revert theo lịch.

**Ba tình huống.** Tối thứ sáu: serving dùng node riêng nên không bị ảnh hưởng; fine-tune chạy trong quota + mượn từ search (search đã xong retrain đêm). Research nộp 40 job: Kueue xếp hàng trong quota 8 card + MIG, mượn được tới 8 nếu cohort rảnh, không tạo 40 pod Pending; thời gian chờ admission là metric để xem quota research có đủ. Node GPU chết: nếu là `gpu-serving` thì serving tràn sang `gpu-batch` bằng PriorityClass `serving-critical` (preempt training, mất tối đa 30 phút công); nếu là node batch thì Kueue thấy capacity giảm (hoặc cần giảm quota tay), job bị mất pod được requeue.

## Rubric (tối đa 20 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Ranh giới tenant và node pool rõ, có lý do không tách cluster | 3 |
| Bảng quota/borrowing/lending cộng khớp 32 card, có lý do theo tải từng đội | 4 |
| Ưu tiên và preemption nhất quán giữa pod và Kueue; nói rõ chi phí bị đẩy ra (checkpoint) | 3 |
| Chọn card nguyên / MIG / time-slicing đúng chỗ, nêu rủi ro cô lập | 2 |
| Serving giữ được SLO lúc đỉnh khi training cũng cần GPU | 3 |
| RBAC, NetworkPolicy, metric công bằng cụ thể (tên metric, ai xem) | 3 |
| Ba tình huống được đi hết, có mùa deadline | 2 |

Từ 14 điểm trở lên là đạt.
