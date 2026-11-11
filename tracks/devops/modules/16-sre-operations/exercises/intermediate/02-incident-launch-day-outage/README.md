---
title: Sự cố - load test xanh, ngày ra mắt đỏ
level: intermediate
services: []
files:
  - path: starter/load.js
    note: Kịch bản load test đang dùng làm cổng trước release
  - path: tests/test_launch_day.py
    note: Không sửa
run:
  - nice -n 15 docker pull grafana/k6:1.8.1@sha256:23f2279054c3e01535455c4d92914a625df12aeb631ea0e3ea7a43f96bcbc843
  - uv run pytest tracks/devops/modules/16-sre-operations/exercises/intermediate/02-incident-launch-day-outage -q -rs
---

## Mục tiêu

Điều tra vì sao cổng load test trước release báo đạt cho một bản làm khách không đặt được hàng, và sửa kịch bản để cổng nói đúng sự
thật ở traffic dự báo.

## Đề bài

Cần Docker và image k6 (xem `## 0. Cài đặt` của module).

Bối cảnh, ngày 2026-11-11 (đợt khuyến mãi 11/11 của Olist):

- Mọi release của service tra đơn hàng phải qua cổng load test `starter/load.js` (chạy bằng k6 trên staging) trước khi lên production.
- Bản 2.4.0 qua cổng ngày 2026-11-09: k6 thoát mã 0, không threshold nào vỡ, p95 rất thấp, throughput cao hơn mọi bản trước.
- 20:00 ngày 11/11 traffic lên khoảng 80 request/giây đều đặn, đúng dự báo của team marketing. Khách liên tục báo không xem được đơn
  hàng, ticket hỗ trợ tăng gấp 12 lần. 20:41 rollback về 2.3.0, mọi thứ bình thường lại.
- Bản vá 2.4.1 bị cổng chặn ngày 2026-11-12 (p95 vượt 300 ms), nên team vẫn chạy 2.3.0. Cổng có chặn được bản chậm, vậy vì sao
  nó để lọt 2.4.0?
- SLO của service (tài liệu của team): 99% request thành công, và p95 latency của request thành công dưới 300 ms, đo ở traffic dự báo.

Test dựng `tests/fixtures/orders.py` với từng bản release (biến `RELEASE`) trong `DockerLab` rồi chạy kịch bản của bạn bằng
`testkit.k6_run` (k6 gọi `http://api:8000`). Sửa `starter/load.js` để:

- bản 2.3.0 qua cổng (k6 thoát 0), và kịch bản tạo đúng traffic dự báo: 80 request/giây trong 6 giây (test chấp nhận lệch 10% tổng số
  request);
- bản 2.4.0 và 2.4.1 bị cổng chặn (k6 thoát 99, mã của k6 khi threshold vỡ).

Test còn chạy lại kịch bản gốc với bản 2.4.0 để chứng minh tái hiện đúng tình huống (thoát 0). Sau khi sửa, viết vào `SOLUTION` của bạn
(hay ghi chú riêng) nguyên nhân gốc và vì sao cổng cũ không thấy.

## Tiêu chí đạt

- `uv run pytest ... -q -rs` pass, không skip.
- Giải thích được bằng số liệu trong tóm tắt k6 vì sao kịch bản gốc báo đạt với bản 2.4.0, và vì sao nó báo throughput cao hơn mọi bản
  trước.

## Gợi ý

### Gợi ý 1

Chạy kịch bản gốc với bản 2.4.0 rồi đọc tóm tắt đầy đủ của k6: không chỉ `http_req_duration`, mà mọi metric k6 in ra. Khách thấy gì,
và kịch bản đo gì?

### Gợi ý 2

So số request mỗi giây kịch bản gốc tạo ra với 2.3.0 và với 2.4.0. Traffic thật ngày ra mắt có phụ thuộc vào server trả lời nhanh hay
chậm không?
