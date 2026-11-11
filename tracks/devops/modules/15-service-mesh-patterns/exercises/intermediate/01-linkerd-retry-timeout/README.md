---
title: Retry và timeout bằng HTTPRoute của Linkerd cho dịch vụ báo giá vận chuyển chập chờn
level: intermediate
services: []
files:
  - path: starter/k8s/freight-routes.yaml
    note: Bản nháp, 2 TODO
  - path: tests/fixtures/freight_quote.py
    note: Dịch vụ báo giá giả, lỗi và chậm ngẫu nhiên có seed
  - path: tests/fixtures/freight.yaml
    note: freight, checkout; không sửa
  - path: tests/test_retry_timeout.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/15-service-mesh-patterns/exercises/intermediate/01-linkerd-retry-timeout -q -rs
---

## Mục tiêu

Dùng mesh để làm một dependency chập chờn trở nên dùng được mà không sửa dòng code nào: retry có giới hạn, timeout cho từng lần thử và
cho cả request, chỉ retry đúng thứ được retry, rồi đo bằng số liệu thật rằng tỉ lệ thành công tăng mà lượng tải đổ vào backend vẫn
trong giới hạn.

## Đề bài

`freight` (dịch vụ báo giá vận chuyển của đối tác, `tests/fixtures/freight_quote.py`) nghe cổng 8080:

- `GET /quote`: với seed cố định, khoảng 20% request trả `503`, khoảng 10% treo 2,5 giây rồi mới trả `200`, còn lại trả `200` ngay.
- `POST /reserve`: giữ chỗ vận chuyển cho một đơn, cùng tỉ lệ lỗi và chậm. Mỗi lần gọi là một lần giữ chỗ: **không được** gọi lặp.

`checkout` gọi `freight`. Cả hai nằm trong namespace có inject (`KubeLab(mesh=True)`), nên đã có proxy và mTLS. Viết
`starter/k8s/freight-routes.yaml` gồm các `HTTPRoute` của `policy.linkerd.io/v1beta3`, `parentRefs` là Service `freight` cổng 8080
(`group: core`, `kind: Service`), sao cho:

| Luồng | Yêu cầu |
| --- | --- |
| `GET /quote` | Retry khi `5xx`, tối đa 3 lần thử lại (`retry.linkerd.io/limit` từ 1 tới 3); timeout mỗi lần thử (`retry.linkerd.io/timeout`) không quá 1 s; timeout cả request (`timeout.linkerd.io/request`) không quá 2 s |
| `POST /reserve` | Vẫn tới được `freight`; không có annotation `retry.linkerd.io/*` nào trên route khớp nó |

Retry và timeout của Linkerd đặt bằng annotation trên HTTPRoute (ví dụ `retry.linkerd.io/http: 5xx`, `retry.linkerd.io/limit: "2"`,
`retry.linkerd.io/timeout: 500ms`, `timeout.linkerd.io/request: 3s`), áp cho mọi rule của route đó. Bản nháp trong `starter/` dùng
một route bắt mọi path: đọc kỹ xem nó làm gì với `POST /reserve`.

**Cách test chấm.** Cài `freight` và `checkout`, rồi:

| Kiểm | Cách | Mong đợi |
| --- | --- | --- |
| Đối chứng | 60 `GET /quote` từ checkout trước khi có route | Ít nhất 5 request không phải 200 và có request chậm từ 2 s (chứng minh backend lỗi thật) |
| Route được nhận | `status.parents[].conditions` của mọi HTTPRoute | `Accepted=True` (chờ tối đa 40 giây) |
| Tỉ lệ thành công | 200 `GET /quote` tuần tự | Ít nhất 97% trả 200 |
| Độ trễ | Cùng 200 request | Request chậm nhất dưới 2,3 s |
| Tải lên backend | Đếm request `freight` nhận (endpoint `/stats` trong pod) | Nhiều hơn 200 (có retry) nhưng không quá 1,6 lần |
| POST | 40 `POST /reserve` | Không có `404`; `freight` nhận đúng 40 lần |
| Metric của mesh | `lab.mesh_status("deployment/checkout")` | `retries > 0` |
| Cấu hình | Annotation của route khớp `GET /quote` và `POST /reserve` | Như bảng yêu cầu |

Khoảng 2 phút. Cần cluster `devops-lab` có Linkerd dùng chung (mục 0 của README module).

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao chỉ có `retry.linkerd.io/http: 5xx` mà không có timeout cho từng lần thử thì request treo 2,5 giây vẫn không
  được cứu.
- Tính được số request tối đa `freight` có thể nhận cho một `GET /quote` với cấu hình của bạn, và nói vì sao giới hạn đó quan trọng khi
  `freight` sập hẳn.
- Nói được vì sao `POST /reserve` không được retry ở mesh, và cần gì ở phía ứng dụng để retry nó an toàn.

## Gợi ý

### Gợi ý 1

Theo Gateway API, khi một Service đã có HTTPRoute thì request không khớp rule nào của mọi route bị proxy trả 404. Một route có thể có
nhiều rule nhưng annotation áp cho cả route, nên cần hai route: một cho `GET /quote` (`matches` có `path` và `method`), một cho
`POST /reserve`.

### Gợi ý 2

Xem route đã được nhận chưa: `kubectl --kubeconfig ~/.kube/devops-lab.yaml -n <ns> get httproutes.policy.linkerd.io -o yaml`.
Xem retry trong metrics của proxy client: `linkerd --kubeconfig ~/.kube/devops-lab.yaml diagnostics proxy-metrics -n <ns>
deploy/checkout | grep outbound_http_route_retry`.
