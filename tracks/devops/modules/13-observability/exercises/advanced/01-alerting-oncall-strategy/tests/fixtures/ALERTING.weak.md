# Alert cho Olist Shop

## 1. Nguyên tắc

- Alert mọi thứ có thể hỏng để không bỏ sót.
- Mỗi alert có runbook khi có thời gian viết.
- Alert gửi vào kênh chat chung để ai rảnh thì xem, page khi nghiêm trọng theo triệu chứng.

## 2. Danh mục alert

| Alert | Service | Tín hiệu | Severity | Receiver | Runbook |
| --- | --- | --- | --- | --- | --- |
| OlistServiceDown | olist-api | `up == 0` | page | oncall-pager | https://runbooks.example/down |
| OlistApiCpuHigh | olist-api | `rate(process_cpu_seconds_total[5m]) > 0.8` | page | oncall-pager | https://runbooks.example/cpu |
| OlistNodeMemoryHigh | olist-api | `node_memory_MemAvailable_bytes < 1e9` | page | oncall-pager | xem wiki |
| OlistApiErrors | olist-api | lỗi 5xx > 1% trong 1 phút | ticket | shop-tickets | https://runbooks.example/errors |
| OlistWorkerSlow | olist-worker | job chậm | ticket | shop-tickets | https://runbooks.example/worker |
| OlistDiskHigh | olist-postgres | `node_filesystem_avail_bytes` dưới 30% | ticket | shop-tickets | https://runbooks.example/disk |

## 3. Routing, grouping, inhibition

- Mọi alert gửi tới oncall-pager, group_by theo alertname.
- Không dùng inhibit để không mất alert nào.
- Không cần watchdog vì Prometheus rất ổn định.

## 4. On-call

- Ai thấy alert thì xử lý.
- Trưởng nhóm luôn nhận mọi page.
- Không cần lịch cố định.
- Cuối tuần tắt pager.

## 5. Đo chất lượng alert

- Không đo, vì mỗi page đều quan trọng.
- Mỗi tháng xem lại nếu có người phàn nàn về nhiễu.
- Đếm số page khi có thời gian.

## 6. Rủi ro và giới hạn

- Có thể nhiều page vào ban đêm.
