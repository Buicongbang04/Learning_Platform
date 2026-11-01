---
title: NetworkPolicy - chỉ API được nói chuyện với Postgres và Redis, DNS vẫn chạy
level: intermediate
services: []
files:
  - path: starter/k8s/networkpolicies.yaml
    note: Bản nháp của đồng nghiệp, chưa đủ
  - path: tests/fixtures/app.yaml
    note: api, analytics, intruder do test cài; không sửa
  - path: tests/fixtures/deps.yaml
    note: Postgres, Redis, Secret olist-db
  - path: tests/fixtures/deny-without-dns.yaml
    note: Policy mẫu thiếu DNS, test dùng để tái hiện bẫy
  - path: tests/test_networkpolicy.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/11-kubernetes-production/exercises/intermediate/01-networkpolicy-api-only -q -rs
---

## Mục tiêu

Khoá mạng của một namespace production theo mô hình default-deny: chỉ đúng những luồng cần thiết được mở, DNS không bị cắt, và chứng
minh bằng kết nối thật từ trong pod rằng luồng được phép thông còn luồng bị cấm bị chặn.

## Đề bài

Namespace có năm workload (test cài từ `tests/fixtures/`, nhãn `app.kubernetes.io/name`): `postgres` (5432), `redis` (6379), `api`
(Olist Shop, 8000), `analytics` (notebook của team dữ liệu) và `intruder` (đại diện cho một pod bất kỳ khác, ví dụ pod bị chiếm quyền).
Viết `starter/k8s/networkpolicies.yaml` để chỉ có các luồng sau:

| Từ | Tới | Cổng |
| --- | --- | --- |
| Mọi pod trong namespace | CoreDNS (`k8s-app: kube-dns` ở `kube-system`) | UDP và TCP 53 |
| `api` | `postgres` | TCP 5432 |
| `api` | `redis` | TCP 6379 |
| `analytics` | `api` | TCP 8000 |

Mọi luồng khác, cả vào lẫn ra, bị chặn: `analytics` không chạm Postgres, Redis; `intruder` không chạm gì; `api` không gọi được ra ngoài
namespace, kể cả API server của cluster. Không sửa workload hay nhãn của chúng.

**Cách test chấm.** `KubeLab` cài stack, chờ `/readyz` của api trả 200 và ghi một lần đối chứng (trước khi có policy, `analytics` nối được
Postgres và API server), apply `k8s/`, chờ 5 giây, **restart** `api` (kết nối cũ trong pool có thể sống qua policy mới; pod mới mới phản
ánh đúng), rồi `kubectl exec` một script Python vào từng pod: mở TCP với timeout 3 giây, phân giải tên, gọi HTTP.

| Kiểm | Từ pod | Mong đợi |
| --- | --- | --- |
| Đối chứng | analytics, trước policy | Postgres và API server đều nối được |
| `/readyz` | api | `200 {"db":"ok","redis":"ok"}` (cần DNS, Postgres, Redis), chờ tối đa 40 giây |
| Dữ liệu | api | Nối được `postgres:5432`, `redis:6379` theo tên và theo ClusterIP |
| analytics | analytics | `http://api:8000/healthz` trả 200; phân giải được `postgres`; ClusterIP của Postgres, Redis bị chặn (timeout hay từ chối) |
| intruder | intruder | ClusterIP của api, Postgres, Redis đều bị chặn |
| Egress | api, analytics | ClusterIP của Service `kubernetes` cổng 443 bị chặn |
| Bẫy DNS | api, lab riêng với `tests/fixtures/deny-without-dns.yaml` | Nối Postgres theo IP được, phân giải `postgres` thì lỗi, `/readyz` không còn 200 |

Ca cuối không chấm bài của bạn; nó chứng minh cluster thực thi NetworkPolicy và bẫy trong đề là thật. Khoảng 2 phút khi đúng, gần 4 phút
trên starter.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao `api` gọi Postgres cần cả egress của `api` lẫn ingress của `postgres`, và vì sao không cần luật cho gói trả lời.
- Chỉ ra được sự khác nhau giữa `namespaceSelector` và `podSelector` nằm chung một phần tử `to` với nằm ở hai phần tử riêng.

## Gợi ý

### Gợi ý 1

Bắt đầu từ một policy `podSelector: {}` có cả `Ingress` và `Egress` trong `policyTypes`, không có luật nào: đó là chặn hết. Rồi mỗi
luồng trong bảng là một cặp: egress ở pod gọi, ingress ở pod nhận. Namespace nào cũng có sẵn nhãn `kubernetes.io/metadata.name`.

### Gợi ý 2

Thử tay trong namespace riêng: `kubectl exec deploy/analytics -- python -c "import socket; socket.create_connection(('postgres', 5432),
timeout=3)"`. Lỗi `Temporary failure in name resolution` sau khoảng 20 giây là DNS bị chặn; `timed out` sau 3 giây là luồng bị chặn.
