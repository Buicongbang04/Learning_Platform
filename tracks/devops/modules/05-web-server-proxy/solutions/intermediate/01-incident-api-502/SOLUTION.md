# Lời giải: sự cố API trả 502 sau khi đổi cấu hình Nginx

Có ba lỗi chồng nhau. Hai lỗi đầu làm sập API, lỗi thứ ba làm không ai biết API đã sập.

## Chẩn đoán theo thứ tự một on-call sẽ đi

**1. Khoanh vùng.** `/` 200 còn `/api/...` 502 trả về ngay: Nginx sống, frontend tĩnh sống, hỏng ở chặng Nginx → API. 502
trả về ngay (không phải sau 60 giây) nghĩa là kết nối bị từ chối, không phải treo. Log API không có request nào: request
không tới được API, nên rollback API là vô ích.

**2. Đọc error log Nginx.**

```text
connect() failed (111: Connection refused) while connecting to upstream, ... upstream: "http://172.20.0.3:8080/api/healthz"
upstream server temporarily disabled while connecting to upstream
no live upstreams while connecting to upstream
```

`111: Connection refused` tới cổng **8080**, trong khi API nghe **8000** (hợp đồng trong `sample-app/README.md`, `EXPOSE
8000` trong Dockerfile). Cấu hình được chép từ staging, nơi API chạy cổng khác. Sau vài lần lỗi, `max_fails` rút cả hai
backend, rồi `no live upstreams`: mọi request bị trả 502 mà không thử kết nối nữa trong 30 giây.

**Lỗi 1**: `server olist-api-1:8080` → `server olist-api-1:8000` (cả hai dòng).

**3. Sau khi sửa cổng.** 502 hết, nhưng `/api/orders/...` và `/api/healthz` trả **404**, lần này do API sinh ra (có trong
log API). Trường `path` của backend giả (hoặc log API) cho thấy API nhận `/api/healthz`, mà API không có route nào bắt đầu
bằng `/api/`. Chính dòng `upstream: "http://...:8080/api/healthz"` ở bước 2 đã báo trước điều này.

**Lỗi 2**: `proxy_pass http://olist_api;` (không có phần URI) chuyển **nguyên** URI gốc. Cần `proxy_pass http://olist_api/;`
(có `/`): khi `proxy_pass` có phần URI, Nginx thay phần khớp với `location` (`/api/`) bằng URI đó (`/`), nên
`/api/orders/x?expand=items` thành `/orders/x?expand=items`.

| `location` | `proxy_pass` | Request | Backend nhận |
| --- | --- | --- | --- |
| `/api/` | `http://olist_api` | `/api/orders/1` | `/api/orders/1` |
| `/api/` | `http://olist_api/` | `/api/orders/1` | `/orders/1` |
| `/api` | `http://olist_api/` | `/api/orders/1` | `//orders/1` (hai dấu `/`) |
| `/api/` | `http://olist_api/v1/` | `/api/orders/1` | `/v1/orders/1` |

Cách khác là `rewrite ^/api/(.*)$ /$1 break;` rồi `proxy_pass http://olist_api;`, rõ ý hơn khi quy tắc phức tạp. Lưu ý:
`proxy_pass` có URI và `rewrite` trong cùng location hoặc location regex có luật riêng; đọc kỹ tài liệu trước khi kết hợp.

**Lỗi 3 (vì sao không ai biết)**: `location = /healthz { return 200 "ok\n"; }` trả 200 ngay tại Nginx, không hỏi API. Health
check của load balancer chỉ chứng minh "tiến trình Nginx còn sống". Sửa thành proxy tới `/healthz` của API (đề yêu cầu vậy);
tốt hơn nữa là LB gọi `/readyz` của API qua Nginx để rút node khi API hoặc DB của node đó hỏng. Cân nhắc: nếu mọi node cùng
fail health check (DB chết), LB cloud thường "fail open" (gửi tới mọi node) hoặc trả 503; hiểu hành vi đó trước khi gắn
readiness phụ thuộc DB vào health check của LB.

## Vì sao các tầng phòng thủ không chặn

- `nginx -t` chỉ kiểm cú pháp và resolve được tên upstream; nó không kết nối tới upstream và không biết route của API.
- Staging chạy API ở cổng khác nên cấu hình "đúng ở staging". Cấu hình phụ thuộc môi trường phải là biến (template), không
  phải bản sao tay.
- Không có smoke test sau deploy: một `curl -fsS https://.../api/healthz` sau reload là bắt được trong 1 giây.
- Health check của LB không đi tới API (lỗi 3), và cảnh báo 5xx chỉ đo lỗi của chính LB.

## Kiểm sau khi sửa

```bash
for p in /api/healthz '/api/orders/e481f51cbdc5?expand=items' /healthz /; do
  curl -s -o /dev/null -w "%{http_code} $p\n" -H 'Host: shop.olist.test' "localhost:18085$p" || break
done
```

Trong lab ở mục 0 của lý thuyết, sau khi sửa tệp chạy `docker exec devops-ex-lab-nginx nginx -t && docker exec
devops-ex-lab-nginx nginx -s reload`.
