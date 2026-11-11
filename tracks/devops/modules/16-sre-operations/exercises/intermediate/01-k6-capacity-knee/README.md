---
title: Load test bậc thang bằng k6, tìm điểm gãy và đề xuất capacity
level: intermediate
services: []
files:
  - path: starter/load.js
    note: 2 TODO
  - path: starter/capacity.py
    note: 5 TODO
  - path: tests/test_capacity.py
    note: Không sửa
  - path: tests/fixtures/server.py
    note: Service giả của bài, không sửa
  - path: tests/fixtures/summary-sample.json
    note: Tóm tắt k6 mẫu cho test không cần Docker
run:
  - nice -n 15 docker pull grafana/k6:1.8.1@sha256:23f2279054c3e01535455c4d92914a625df12aeb631ea0e3ea7a43f96bcbc843
  - uv run pytest tracks/devops/modules/16-sre-operations/exercises/intermediate/01-k6-capacity-knee -q -rs
---

## Mục tiêu

Chạy load test bậc thang (step load) bằng k6 với mô hình tải mở, đọc tóm tắt của k6 để tìm điểm gãy (knee) của một service, rồi
dùng định luật Little và headroom để ra số replica cho đỉnh traffic. Mọi con số trong đề xuất phải lấy từ đúng lần chạy k6.

## Đề bài

Cần Docker và image k6 (lệnh `docker pull` ở trên, xem `## 0. Cài đặt` của module). Test dựng `tests/fixtures/server.py` (service
tra đơn hàng giả: mỗi request mất khoảng 40 ms, xử lý tối đa 2 request cùng lúc, request thừa phải xếp hàng) trong `DockerLab`, rồi
chạy kịch bản của bạn bằng `testkit.k6_run` trong cùng network: k6 gọi service ở `http://api:8000`.

**1. `starter/load.js`.** Kịch bản nhận ba biến `__ENV`: `TARGET`, `STEPS` (danh sách tốc độ, ví dụ `10,20,30,40,60,80`),
`STEP_SECONDS` (test đặt 5). Với mỗi tốc độ `r` trong `STEPS` (bước thứ `i`, đếm từ 0):

- một scenario tên `step_<r>`, executor `constant-arrival-rate`, `rate: r`, `timeUnit: "1s"`, `duration` bằng `STEP_SECONDS` giây,
  `startTime` bằng `i` nhân `STEP_SECONDS` giây (các bước chạy nối tiếp), `preAllocatedVUs: 10`, `maxVUs: 150`;
- ba threshold **luôn đúng** để k6 ghi submetric của scenario đó vào tóm tắt: `http_req_duration{scenario:step_<r>}` với `max>=0`,
  `http_req_failed{scenario:step_<r>}` với `rate>=0`, `http_reqs{scenario:step_<r>}` với `count>=0`. k6 phải thoát mã 0: kết luận
  đạt hay gãy do `capacity.py` tính, không do threshold.

Hàm `default` gửi `GET ${TARGET}/orders/<số ngẫu nhiên>` và `check` mã 200.

**2. `starter/capacity.py`.** `summary` là dict tóm tắt k6 (`summary["metrics"]["http_req_duration{scenario:step_40}"]["values"]["p(95)"]`,
thời gian tính bằng ms):

1. `step_metrics(summary, steps, step_seconds)`: list theo `rps` tăng dần, mỗi phần tử `{"rps", "achieved_rps", "p95_ms", "avg_ms",
   "error_rate"}`; `achieved_rps` là `count` của `http_reqs` chia `step_seconds`; `error_rate` là `rate` của `http_req_failed`. Thiếu
   submetric nào thì `ValueError` (thông báo nhắc thêm threshold).
2. `knee(rows, slo_p95_ms=200, max_error_rate=0.01, min_achieved=0.9)`: duyệt bước theo `rps` tăng dần; bước khoẻ khi p95 không quá
   `slo_p95_ms`, tỉ lệ lỗi không quá `max_error_rate` và `achieved_rps` ít nhất `min_achieved` nhân `rps`. Trả `rps` của bước khoẻ
   cuối cùng trước bước gãy đầu tiên; bước đầu đã gãy thì `None`.
3. `littles_law(rps, avg_ms)`: số request đang xử lý cùng lúc theo định luật Little.
4. `replicas(peak_rps, knee_rps, headroom=0.3, spare=1)`: làm tròn lên của `peak_rps` nhân (1 + headroom) chia `knee_rps`, cộng `spare`
   (N+1). `knee_rps` không dương thì `ValueError`.
5. `report(summary, steps, step_seconds, peak_rps, slo_p95_ms=200)`: markdown gồm bảng

   ```
   | Bước (rps) | Đạt được (rps) | p95 (ms) | Trung bình (ms) | Lỗi (%) |
   | --- | --- | --- | --- | --- |
   | 10 | 10.0 | 41.3 | 40.9 | 0.00 |
   ```

   (một dòng mỗi bước; rps, p95, trung bình một chữ số thập phân; lỗi tính bằng % hai chữ số), một dòng trống, rồi ba dòng
   `Điểm gãy: <knee> rps`, `Đồng thời ở điểm gãy (Little): <số, 2 chữ số>` (dùng latency trung bình ở bước knee),
   `Replica cho đỉnh <peak_rps> rps: <số>`. Không có knee thì chỉ in `Điểm gãy: không có`.

**Cách test chấm.** Phần không cần Docker dùng `tests/fixtures/summary-sample.json` (tóm tắt của một lần chạy thật). Phần cần Docker
chạy `load.js` của bạn với `STEPS=10,20,30,40,60,80`, kiểm k6 thoát 0, có đủ submetric, ba bước đầu gửi đúng tốc độ (cộng trừ 10%),
điểm gãy nằm trong khoảng hợp lý với service, rồi so **từng con số** trong `report` với tóm tắt của chính lần chạy đó, đỉnh 300 rps.

## Tiêu chí đạt

- `uv run pytest ... -q -rs` pass, không skip.
- Giải thích được: vì sao latency ở bước 40 gần như bằng bước 10 mà bước 60 vọt lên hàng trăm ms; công suất lý thuyết của service là
  bao nhiêu rps và vì sao điểm gãy đo được thấp hơn; vì sao kế hoạch capacity dùng knee chứ không dùng throughput cao nhất.

## Gợi ý

### Gợi ý 1

Dựng `scenarios` và `thresholds` bằng `STEPS.forEach((rate, index) => {...})` trước dòng `export const options`. Chạy tay để xem tóm
tắt: dựng service bằng `docker run` với `-v $PWD/tests/fixtures:/srv:ro` rồi `docker run grafana/k6 ... run -e TARGET=...`.

### Gợi ý 2

Công suất của service bằng số request xử lý cùng lúc chia thời gian mỗi request. Định luật Little: số request trong hệ thống bằng tốc
độ đến nhân thời gian ở lại. Khi tốc độ đến vượt công suất, hàng đợi dài thêm mỗi giây nên latency tăng theo thời gian của bước.
