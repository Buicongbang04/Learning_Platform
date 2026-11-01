# Lời giải: NetworkPolicy chỉ cho API nói chuyện với Postgres và Redis

Lời giải nằm trong `k8s/networkpolicies.yaml`, bảy policy nhỏ, mỗi cái một việc (dễ review, dễ xoá đúng một luồng):

| Policy | Chọn pod | Làm gì |
| --- | --- | --- |
| `default-deny-all` | Mọi pod | `policyTypes: [Ingress, Egress]`, không luật: chặn hết hai chiều |
| `allow-dns` | Mọi pod | Egress UDP, TCP 53 tới pod `k8s-app: kube-dns` trong namespace `kube-system` (namespaceSelector **và** podSelector trong cùng phần tử) |
| `api-egress-data` | api | Egress tới postgres:5432, redis:6379 |
| `postgres-from-api`, `redis-from-api` | postgres, redis | Ingress chỉ từ api, đúng cổng |
| `api-from-analytics` | api | Ingress 8000 chỉ từ analytics |
| `analytics-egress-api` | analytics | Egress 8000 tới api |

Starter có deny-all và luồng api tới dữ liệu nhưng thiếu `allow-dns`: api không phân giải được `postgres`, `/readyz` trả 503 (hay treo
khoảng 20 giây rồi lỗi) dù nối theo IP vẫn được. Đó là bẫy phổ biến nhất của default-deny. Starter cũng không mở luồng analytics tới api.

Những điểm đáng nhớ:

- Pod A gọi pod B khi cả hai đều có policy: cần egress ở A **và** ingress ở B. Gói trả lời của kết nối đã được phép tự qua (CNI theo
  dõi kết nối), không cần luật chiều ngược.
- `- namespaceSelector: ... \n  podSelector: ...` (một phần tử) là **và**: pod kube-dns trong kube-system. Tách thành hai phần tử `-` là
  **hoặc**: mọi pod của kube-system hoặc mọi pod có nhãn kube-dns ở **namespace của mình**. Một dấu gạch lệch là mở rộng cửa.
- DNS mở cho cả TCP vì câu trả lời lớn (nhiều bản ghi) chuyển sang TCP.
- Restart sau khi đổi policy: kết nối Postgres, Redis đã mở trong pool của api sống qua policy mới (đã thấy trên `devops-lab`: bản thiếu
  DNS vẫn trả `/readyz` 200 cho tới khi pod được tạo lại). Sự cố thật thường lộ ra ở lần deploy sau.
- Egress tới API server bị chặn vì api không cần nó; workload nào cần (controller, operator) thì mở egress tới IP của API server cổng
  6443 hay 443 tuỳ cluster.
- Ingress controller hay Gateway ở namespace khác gọi vào api thì thêm ingress từ `namespaceSelector` của namespace đó; Prometheus scrape
  cũng vậy (module 13).

Kiểm tay nhanh từ một pod: `kubectl exec deploy/intruder -- python -c "import socket; socket.create_connection(('<ClusterIP postgres>',
5432), timeout=3)"` phải `timed out`.
