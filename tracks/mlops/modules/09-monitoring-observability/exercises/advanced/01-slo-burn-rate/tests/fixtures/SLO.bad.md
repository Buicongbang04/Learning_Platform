# SLO cho service ETA

## 1. SLI và SLO

Service phải chạy tốt.

| SLI | Định nghĩa (PromQL) | SLO | Cửa sổ |
| --- | --- | --- | --- |
| CPU | `avg(node_cpu_usage)` | 80% | 5m |

## 2. Error budget

Budget còn nhiều.

| Cửa sổ | SLO khả dụng | Budget (phút) |
| --- | --- | --- |
| 30d | 99.5% | 500 |

## 3. Burn-rate alert

| Mức | Burn rate | Cửa sổ dài | Cửa sổ ngắn | % budget tiêu | Hành động |
| --- | --- | --- | --- | --- | --- |
| Nhanh | 14.4 | 1h | 1h | 20 | page |

## 4. Quy trình khi budget cạn

Cố gắng hơn.

## 5. Giới hạn và rủi ro

Không có.
