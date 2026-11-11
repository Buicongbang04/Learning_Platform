# Lời giải: FinOps, rightsizing và chia chi phí

## Cách làm

- `cost` tính theo request vì scheduler giữ chỗ theo request: pod xin 2 vCPU mà dùng 0,3 vẫn chiếm 2 vCPU của node, node đó vẫn phải
  trả tiền. Đó là lý do rightsizing tiết kiệm thật.
- `rightsize` dùng CPU **p95** (CPU bị throttle khi thiếu, chậm chứ không chết) nhưng RAM **cao nhất** (thiếu RAM là OOMKilled). Headroom
  20% và làm tròn theo bậc để đề xuất không đổi mỗi tuần vì nhiễu.
- `allocate` chia chi phí chung theo tỉ lệ chi phí trực tiếp (proportional). Cách khác là chia đều hay theo một driver riêng (số log,
  số request); cách nào cũng được miễn tổng khớp hoá đơn và các team đồng ý trước.
- `unit_cost` đưa chi phí về đơn vị kinh doanh: cuối tháng không hỏi "tốn 1.693 USD có nhiều không" mà hỏi "4,11 USD cho mỗi 1000 đơn,
  tháng trước bao nhiêu".

## Kết quả tháng 10

| Team | USD |
| --- | --- |
| search | 467,02 |
| data | 418,58 |
| checkout | 393,40 |
| unallocated | 393,40 |
| platform | 20,71 |

- Tổng chi phí trực tiếp 1.314,10 USD, cộng 379 USD chi phí chung.
- Rightsizing tiết kiệm khoảng 892,76 USD mỗi tháng (68% chi phí trực tiếp), phần lớn từ `loadtest-rig`, `recs-model`, `search-api`.
- Hai workload phải **tăng**: `olist-worker` (RAM cao nhất 950 MiB trên request 1024, headroom còn 7%) và `search-indexer` (7900 trên 8192). Hai
  pod này sắp OOM; tăng trước khi cắt chỗ khác.
- Ba workload gần như rỗi: `feature-preview-142` và `loadtest-rig` (không team) và `olist-api` ở staging. Chi phí không nhãn bằng cả team checkout: việc
  đầu tiên là bắt buộc nhãn `team` (admission policy hay CI) và xoá môi trường preview tự động.
- Chi phí mỗi 1000 đơn: 4,1095 USD.

## Lưu ý khi áp dụng thật

- p95 một tháng bỏ sót đỉnh hiếm (Black Friday). Xem cả p99, max và mùa vụ trước khi cắt; với service quan trọng, giảm từng bước.
- Cắt request mà không đổi kích thước node thì hoá đơn chưa giảm: cần cluster autoscaler (hay Karpenter) gom pod lại để bớt node.
- `limits` RAM thường đặt bằng request để tránh OOM của node; `limits` CPU nhiều team bỏ hẳn để tránh throttle.
