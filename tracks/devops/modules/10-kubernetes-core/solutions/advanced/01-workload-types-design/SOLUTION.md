# Lời giải: chọn workload cho Olist Shop

Bài mẫu: `DESIGN.md`. Không có đáp án duy nhất cho các dòng không bị test ràng buộc; rubric chấm lập luận.

## Hướng làm

1. Với mỗi thành phần hỏi ba câu: chạy mãi hay chạy xong là hết; replica có cần danh tính, volume riêng không; có phải chạy trên mọi
   node không. Ra ngay: `fluent-bit` DaemonSet; `report` CronJob; `migration`, `thumbnail` Job; `api`, `worker` Deployment.
2. Thứ có trạng thái quan trọng (`postgres`): StatefulSet hay dịch vụ managed. Với RPO 5 phút, RTO 30 phút, đội bốn người, RDS là
   lựa chọn mặc định hợp lý; StatefulSet tự vận hành chỉ thắng khi cần chạy ngoài cloud, chi phí rất nhạy, hay có operator trưởng
   thành (CloudNativePG) và người hiểu nó.
3. Thứ ngoài cluster (`payment`, RDS): Service `ExternalName` cho code gọi một tên nội bộ ổn định. Nhớ giới hạn: chỉ là CNAME, không
   có health check, TLS vẫn phải khớp tên thật (`payments.partner.example`), và không dùng được với địa chỉ IP (lúc đó dùng Service
   không selector cộng EndpointSlice tay).
4. `thumbnail`: Job `completionMode: Indexed`, `completions: 20`, `parallelism: 10`; mỗi pod đọc `JOB_COMPLETION_INDEX` để biết phần
   của mình, `backoffLimitPerIndex` để một phần lỗi không làm hỏng cả lô.
5. Rollout: Deployment dùng maxUnavailable/maxSurge; StatefulSet dùng `partition` để canary trên replica số lớn trước, hay `OnDelete`
   khi muốn tự tay xoá từng pod; PDB để `kubectl drain` khi nâng cấp node không phá quorum hay capacity.

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Bối cảnh có số liệu (tải, RPO/RTO, đội, cluster) và mọi quyết định sau dẫn chiếu tới chúng | 2 |
| Postgres: chọn có lý do gắn RPO/RTO và năng lực đội; nêu cái giá của lựa chọn còn lại | 2 |
| Redis, worker: nói rõ dữ liệu nào mất được, mất thì sao | 1 |
| Job, CronJob: nêu concurrencyPolicy, startingDeadlineSeconds, Indexed, backoff; migration tương thích ngược để rollback | 2 |
| Rollout và PDB nhất quán với số replica (không đặt PDB minAvailable 100% cho Deployment 1 replica) | 1 |
| Storage: StorageClass, access mode, reclaim, `WaitForFirstConsumer` với volume theo zone, backup có diễn tập restore | 1 |
| Rủi ro: ít nhất một rủi ro của chính lựa chọn mình (không chỉ rủi ro chung chung) | 1 |

## Câu hỏi bảo vệ

- "Sao không chạy Postgres bằng StatefulSet cho rẻ?": được, nếu chấp nhận tự lo failover (Patroni, CloudNativePG), backup PITR, vá,
  nâng cấp major, và một node chết thì volume RWO theo zone phải chờ detach. Với đội bốn người và RTO 30 phút, phần việc đó đắt hơn
  tiền RDS.
- "Redis restart lúc 11.11 thì mất gì?": job đang trong hàng đợi chưa xử lý; doanh thu tính lại được vì đơn đã nằm trong Postgres.
  Nếu job không tính lại được (gửi email, trừ kho) thì Redis không còn là "mất được": cần hàng đợi bền (Redis có AOF và replica,
  hay SQS, Kafka).
