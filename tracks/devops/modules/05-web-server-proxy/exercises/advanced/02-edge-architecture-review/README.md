---
title: Thiết kế lớp edge cho Olist Shop - load balancer, Nginx, firewall và egress
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung tài liệu thiết kế, điền mọi TODO
  - path: tests/test_design.py
    note: Không sửa; kiểm khung và rule firewall, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/advanced/02-edge-architecture-review -q
---

## Mục tiêu

Thiết kế toàn bộ đường đi của request vào và ra cho Olist Shop production như một senior trình bày trong buổi review kiến
trúc: mỗi lựa chọn có phương án bị loại và lý do, IP client và header được tin đúng chỗ, firewall chỉ mở đúng những gì cần,
và có giới hạn cụ thể cho health check, timeout, rate limit.

## Đề bài

Olist Shop lên cloud (một region, hai availability zone). Yêu cầu và ràng buộc:

- Lưu lượng thường 300 request/giây, Black Friday dự kiến gấp 10 trong 6 giờ. 70% là đọc catalog và
  `/stats/revenue-by-state`, 25% là đơn hàng, còn lại là `/jobs/recompute` và webhook.
- API (4 bản, có thể tăng lên 12) và worker chạy trong subnet private; Postgres (primary + 1 replica) và Redis trong subnet
  dữ liệu.
- Cổng thanh toán gọi webhook `POST /api/webhooks/payment` từ một dải IP công bố sẵn, và yêu cầu Olist Shop gọi API của họ
  từ một IP cố định để họ đưa vào allowlist.
- Worker gọi ra ngoài tới đúng hai tên miền: API cổng thanh toán và API của đối tác vận chuyển. Bảo mật muốn mọi kết nối ra
  Internet khác bị chặn và có log.
- Team 4 người vận hành, không có đội network riêng. Cert do Let's Encrypt cấp. Truy cập quản trị qua bastion hoặc SSM, không
  SSH từ Internet.
- Đối tác cũ gọi API qua một thiết bị không hỗ trợ SNI.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 7.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh và giả định | Ít nhất 300 ký tự (không tính bảng và khối code) |
| 2. Luồng request | Một khối ` ```mermaid ` có ít nhất 6 cạnh (`-->`, `->>` hoặc `---`) |
| 3. Quyết định | Bảng ít nhất 6 dòng đủ 4 cột (`Quyết định`, `Lựa chọn`, `Phương án bị loại`, `Lý do và đánh đổi`) |
| 4. Firewall và security group | Bảng ít nhất 6 rule đủ 5 cột (`Nguồn`, `Đích`, `Cổng`, `Giao thức`, `Lý do`); rule có nguồn là Internet (`0.0.0.0/0`, `::/0`, `Internet`, `any`, `*`) chỉ được mở cổng 80 và 443; có ít nhất một rule cổng 5432 với nguồn cụ thể (không phải Internet) |
| 5. IP client và header tin cậy | Ít nhất 3 gạch đầu dòng, có nhắc `set_real_ip_from` và `X-Forwarded-For` |
| 6. Health check, timeout và giới hạn | Ít nhất 4 gạch đầu dòng |
| 7. Rủi ro và việc còn mở | Ít nhất 3 gạch đầu dòng |

Test chỉ kiểm khung và các rule firewall nêu trên; một test khác đưa một bảng firewall mở Postgres và SSH ra Internet vào
cùng phép kiểm và đòi nó bị bắt. Nội dung được chấm bằng rubric trong
`solutions/advanced/02-edge-architecture-review/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/advanced/02-edge-architecture-review -q` pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi giá trị trong phần 6 (timeout, rate, `max_fails`, ngưỡng health check) có lý do gắn với số liệu ở đề, không phải
  "mặc định".
- Chỉ ra được với từng header (`X-Forwarded-For`, `X-Forwarded-Proto`, `X-Request-ID`) tầng nào đặt, tầng nào tin.

## Gợi ý

### Gợi ý 1

Đi từ ngoài vào: DNS, load balancer (L4 hay L7, ai giữ cert), Nginx (còn cần không khi đã có ALB, nếu cần thì làm gì mà ALB
không làm), API. Rồi đi từ trong ra: worker gọi ra ngoài qua đâu, IP nguồn là gì. Mỗi chặng ghi ai kết thúc TLS và ai thấy IP
client thật.

### Gợi ý 2

Security group có trạng thái và tham chiếu được security group khác làm nguồn (`sg-alb` thay cho dải IP), NACL không trạng
thái. Forward proxy cho egress (Squid, Envoy) cho phép allowlist theo tên miền, thứ mà security group chỉ làm được theo IP.
Thiết bị không SNI chỉ nhận được cert của server mặc định trên cặp IP:cổng nó gọi.
