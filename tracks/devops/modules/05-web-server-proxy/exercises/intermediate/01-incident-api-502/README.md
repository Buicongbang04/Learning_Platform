---
title: Sự cố - API trả 502 sau khi đổi cấu hình Nginx
level: intermediate
services: []
files:
  - path: starter/nginx.conf
    note: Cấu hình production lúc sự cố, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/fixtures/backend.py
    note: Backend giả của Olist Shop
run:
  - docker pull nginx:1.30.6-alpine && docker pull python:3.12.16-alpine3.24
  - uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/intermediate/01-incident-api-502 -q
---

## Mục tiêu

Chẩn đoán một sự cố proxy từ triệu chứng và log, theo đúng thứ tự một on-call làm lúc 2 giờ chiều có khách đang phàn nàn:
khoanh vùng, đọc bằng chứng, sửa tối thiểu, xác nhận, và nhận ra vì sao giám sát không kêu.

## Đề bài

Thứ Tư, 14:02, change "Frontend v2: API chuyển về `/api/`, đồng bộ cấu hình Nginx từ staging" được rollout lên Nginx của
Olist Shop. Frontend v2 là SPA tĩnh do chính Nginx phục vụ ở `/`, gọi API qua `/api/...` (ví dụ `/api/orders/<id>`,
`/api/jobs/recompute`). API không đổi gì: nó vẫn có các route `/healthz`, `/orders/{id}`, `/stats/revenue-by-state`,
`POST /jobs/recompute` như trước. `starter/nginx.conf` là cấu hình đang chạy trên production.

Triệu chứng ghi nhận được:

- Mọi request tới `/api/...` nhận `502 Bad Gateway`, trả về ngay chứ không phải sau một lúc chờ.
- Trang chủ `/` và các trang của SPA vẫn 200.
- Health check của load balancer (gọi `GET /healthz` trên Nginx) báo xanh suốt sự cố, không ai bị page.
- Pipeline chạy `nginx -t` trước khi deploy: `syntax is ok`, `test is successful`.
- Team API khẳng định không deploy gì; container API vẫn chạy và log của API không có request nào từ 14:02.

Tìm nguyên nhân và sửa `starter/nginx.conf`. Có thể có nhiều hơn một lỗi; sửa xong lỗi này có thể lộ ra lỗi khác. Chỉ
sửa cấu hình Nginx: không đổi backend, không đổi cách frontend gọi API.

**Môi trường test.** Docker network riêng, hai backend giả `olist-api-1`, `olist-api-2` (`tests/fixtures/backend.py`, route
giống API thật, trả 404 cho route không có), `nginx -t` rồi Nginx `1.30.6` với bản sao cấu hình của bạn. Khi một phép kiểm
fail, thông báo kèm 8 dòng log cuối của Nginx: đó là bằng chứng bạn đọc để chẩn đoán. Muốn tự dựng lại môi trường lỗi để
gõ `curl` và xem log, dùng lab ở mục 0 của lý thuyết.

Test kiểm (mọi request có `Host: shop.olist.test`):

| Request | Phải trả | Backend phải nhận |
| --- | --- | --- |
| `GET /api/healthz` | 200 | `/healthz` |
| `GET /api/orders/e481f51cbdc5?expand=items` | 200 | `/orders/e481f51cbdc5?expand=items` |
| `GET /api/stats/revenue-by-state` | 200 | `/stats/revenue-by-state` |
| `POST /api/jobs/recompute` | 202 | `/jobs/recompute` |

Thêm vào đó:

- 10 request `GET /api/healthz` đều 200 và tới được cả hai backend.
- `GET /` và `GET /checkout/cart` vẫn 200 `text/html` (SPA).
- `GET /healthz` trả 200 **do API trả lời** (JSON `status: ok` từ backend), để health check của load balancer phản ánh
  được API.
- Một test chạy cấu hình lúc sự cố (`tests/fixtures/nginx.incident.conf`) và đòi nó tái hiện đúng triệu chứng: `/api/healthz`
  502, `/` 200, `/healthz` 200; đồng thời các phép kiểm trên phải bắt được nó.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/intermediate/01-incident-api-502 -q` pass.
- Với mỗi lỗi bạn sửa, chỉ ra được dòng log hoặc output `curl` đã dẫn bạn tới nó.
- Giải thích được vì sao `nginx -t` pass dù cấu hình làm sập API, và một bước kiểm nào trong pipeline sẽ chặn được.
- Ghi lại thời điểm bạn hiểu ra từng lỗi: bạn sẽ dùng nó cho postmortem ở bài Advanced 01.

## Gợi ý

### Gợi ý 1

Phân biệt "Nginx không nói chuyện được với upstream" (502 ngay, có dòng `[error]` trong error log) với "upstream trả lời
nhưng trả lỗi" (mã lỗi do backend sinh, có trong log của backend). Trường `upstream:` trong error log cho biết chính xác
Nginx đã gọi tới đâu, kể cả path.

### Gợi ý 2

Đặt cấu hình cạnh hợp đồng của API trong `tracks/devops/sample-app/README.md` (cổng, route) và so từng giá trị. Hết 502
mà vẫn lỗi thì đừng đoán: backend giả trả về trường `path` là đúng cái nó nhận được, so với cái bạn nghĩ nó nhận.
