---
title: Ingress cho host cũ, HTTPRoute chia 90/10 và match header trên Gateway dùng chung
level: intermediate
services: []
files:
  - path: starter/k8s/10-api.yaml
    note: Hai Deployment và Service api-stable (1.4), api-canary (1.5), hoàn chỉnh
  - path: starter/k8s/20-ingress.yaml
    note: Ingress cần viết
  - path: starter/k8s/30-httproute.yaml
    note: HTTPRoute cần viết
  - path: tests/fixtures/deps.yaml
    note: Postgres, Redis, ConfigMap, Secret do test dựng
  - path: tests/test_ingress_gateway_routing.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/10-kubernetes-core/exercises/intermediate/04-ingress-gateway-routing -q -rs
---

## Mục tiêu

Đưa traffic từ ngoài vào Olist Shop bằng cả hai API: một Ingress cho host cũ (cách các cluster hiện có đang làm) và một HTTPRoute trên
Gateway do platform giữ (cách nên làm từ nay), với canary 10% theo trọng số và một header ép vào bản canary để QA thử trước.

## Đề bài

Cluster có sẵn controller dùng chung (mục 0 của module): IngressClass `devops-traefik` và Gateway `devops-gateway/public` (listener HTTP,
chỉ nhận HTTPRoute từ namespace của lab). Bạn chỉ viết route, không tạo Gateway hay GatewayClass.

`starter/k8s/10-api.yaml` đã có hai Deployment và hai Service: `api-stable` (`APP_VERSION=1.4`, 2 replica) và `api-canary`
(`APP_VERSION=1.5`, 1 replica); `/healthz` trả `version`. Viết:

1. `20-ingress.yaml`: Ingress `olist-legacy`, `ingressClassName: devops-traefik`, host `legacy.lab.olist.test`, mọi path (`/`, Prefix) tới
   Service `api-stable`.
2. `30-httproute.yaml`: HTTPRoute `olist`, `parentRefs` là Gateway `public` ở namespace `devops-gateway`, `hostnames: [lab.olist.test]`.
   Request có header `X-Canary: always` luôn tới `api-canary`; mọi request khác chia 90% `api-stable`, 10% `api-canary`.

**Tên host.** Mỗi lab có tên miền riêng `<namespace của lab>.olist.test` để route của lab này không chiếm host của lab khác (policy của
lab từ chối host khác, Ingress thiếu class hay có `defaultBackend`, HTTPRoute gắn vào Gateway khác). Bạn viết `lab.olist.test`; test
chép thư mục `k8s/` ra thư mục tạm, thay chuỗi `lab.olist.test` bằng tên miền của lab, rồi mới apply. Đừng dùng chuỗi đó cho việc khác.

**Cách test chấm.** Test dựng Postgres, Redis, ConfigMap, Secret từ `tests/fixtures/deps.yaml`, apply `k8s/` (đã thay host), chờ rollout
của `api-stable`, `api-canary`, chờ tối đa 60 giây cho tới khi route có hiệu lực, rồi gọi Service
`traefik.devops-gateway.svc.cluster.local` cổng 80 **từ trong pod** `api-stable` (`kubectl exec`, Python) với header `Host`. Không dùng
cổng nào trên máy bạn.

| Kiểm | Cách |
| --- | --- |
| Apply | `k8s/` apply được, hai Deployment rollout xong |
| Ingress | Có Ingress `olist-legacy`; 10 request `Host: legacy.<lab>` tới `/healthz` đều trả `1.4`; `/readyz` trả `{"db":"ok","redis":"ok"}` |
| HTTPRoute | Có HTTPRoute `olist`, điều kiện `Accepted` của mọi parent là `True` |
| Trọng số | 200 request `Host: <lab>`: không request nào lỗi, `1.5` từ 5 tới 45 lần (kỳ vọng 20), `1.4` ít nhất 155 lần |
| Header | 20 request kèm `X-Canary: always` đều trả `1.5` |

Khoảng 40 giây khi đã làm xong.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao bạn không tạo được Gateway trong namespace của mình, và ai trong công ty nên giữ GatewayClass, Gateway,
  HTTPRoute.
- Viết được lại phần trọng số bằng Ingress của ingress-nginx (annotation `canary-weight` trên một Ingress thứ hai) và nói vì sao cách
  đó không mang sang controller khác được.

## Gợi ý

### Gợi ý 1

`kubectl explain httproute.spec.rules` (sau khi cài CRD) hay trang API reference của Gateway API. Một rule có `matches` (path, header,
query, method) và `backendRefs` có `weight`. Khi nhiều rule cùng khớp, rule có match cụ thể hơn (có header) thắng rule chỉ có path.

### Gợi ý 2

Route không chạy thì xem `kubectl get httproute olist -o yaml` phần `status.parents[].conditions` (`Accepted`, `ResolvedRefs`) và
`kubectl describe ingress olist-legacy`. Gọi thử từ trong pod: lệnh `kubectl exec` ở mục 4 của module, thay host bằng tên miền của
namespace bạn đang thử.
