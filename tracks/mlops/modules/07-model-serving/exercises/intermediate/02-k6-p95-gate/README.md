---
title: Cổng tải k6 với ngưỡng p95 trên service trong container
level: intermediate
services: []
files:
  - path: starter/loadtest.js
    note: Viết kịch bản k6, đang chỉ gọi /healthz
  - path: tests/test_k6.py
    note: Không sửa, build image và chạy k6
  - path: tests/fixtures/service/app.py
    note: Service được đo, chỉ đọc
run:
  - docker pull grafana/k6:1.8.1
  - nice -n 15 uv run pytest tracks/mlops/modules/07-model-serving/exercises/intermediate/02-k6-p95-gate -q
---

## Mục tiêu

Viết một cổng tải chạy được trong CI: có giai đoạn warmup, đo ở nhịp cố định, ngưỡng p95 lấy từ SLO, và thật sự chặn khi service chậm.

## Đề bài

Cần Docker. Test build image service ETA (sklearn, FastAPI; build lần đầu vài phút), chạy hai container (một khoẻ, một cố tình chậm thêm ~450 ms mỗi request), rồi chạy kịch bản của bạn bằng `mlopskit.k6_run` (k6 trong container, `--network host`). Biến môi trường k6 nhận: `TARGET` (URL gốc của service) và `P95_MS` (ngưỡng, test đặt 300). Viết `starter/loadtest.js` với:

- Hai scenario dùng executor `constant-arrival-rate`, cùng `exec` một hàm gửi `POST {TARGET}/predict` body `{"rows": [[5, 8, 1], [12, 17, 2]]}` (header `Content-Type: application/json`): **`warmup`** 10 request/giây trong 3 giây (bắt đầu ngay), và **`measure`** 30 request/giây trong 8 giây, bắt đầu sau warmup (`startTime: "4s"`). Cho mỗi scenario `preAllocatedVUs: 20` và `maxVUs: 100`. Tổng khoảng 270 request (test cho phép 255 tới 285).
- Ba `check` cho mỗi response: mã 200; có `model_version`; `predictions` có đúng 2 phần tử. Test đòi `checks` có ít nhất 600 lượt đạt và không có lượt hỏng.
- Ngưỡng (`thresholds`) **chỉ trên giai đoạn đo**: `http_req_duration{scenario:measure}` với `p(95)<${P95_MS}` (đọc `P95_MS` từ `__ENV`, mặc định 300), và `http_req_failed{scenario:measure}` với `rate<0.01`; cộng thêm `checks` với `rate>0.99`.

Service khoẻ phải cho k6 thoát mã 0; service chậm phải cho mã 99 (ngưỡng p95 bị vi phạm). Số đo trên laptop chạy k6 cùng máy với service là tương đối: đừng đặt ngưỡng sát.

## Tiêu chí đạt

- `nice -n 15 uv run pytest tracks/mlops/modules/07-model-serving/exercises/intermediate/02-k6-p95-gate -q` pass.
- Giải thích được vì sao `constant-arrival-rate` đo trung thực hơn VU cố định khi service chậm, và vì sao ngưỡng không áp lên warmup.
- Đọc được trong phần tóm tắt k6: p95, số request thật sự gửi, tỉ lệ lỗi, và biết `dropped_iterations` báo điều gì.

## Gợi ý

### Gợi ý 1

`export const options = { scenarios: { warmup: {...}, measure: {...} }, thresholds: {...} }`. Tên scenario là thứ tạo ra tag `scenario:warmup` và `scenario:measure`.

### Gợi ý 2

Hàm `predict` được export tên riêng và `exec: "predict"` trỏ tới nó; `r.json("model_version")` đọc một trường trong `check`. Nếu k6 thoát mã khác 0 và 99, đọc stderr: thường là lỗi cú pháp kịch bản.
