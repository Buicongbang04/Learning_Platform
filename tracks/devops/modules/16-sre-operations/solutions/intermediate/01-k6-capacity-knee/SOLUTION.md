# Lời giải: load test bậc thang và capacity

## load.js

- `constant-arrival-rate` là mô hình tải **mở**: k6 bắt đầu iteration theo nhịp cố định, không chờ response trước. Server chậm đi thì
  VU tăng lên (tới `maxVUs`) chứ tốc độ đến không giảm, giống người dùng thật, nên điểm gãy hiện rõ ở latency của từng bậc.
- Mỗi bước là một scenario có `startTime` nối tiếp, nên submetric `{scenario:step_<r>}` tách số liệu từng bước. k6 chỉ ghi submetric
  vào tóm tắt khi có threshold cho nó; threshold luôn đúng (`max>=0`) là cách thông dụng để "bật" submetric mà không đổi mã thoát.

## capacity.py

- `step_metrics` đọc p95, trung bình (`avg`), `rate` của `http_req_failed` và `count` của `http_reqs`. `rate` của `http_reqs` trong tóm
  tắt chia cho **cả** thời gian chạy, nên tự chia `count` cho thời gian của bước.
- `knee` dừng ở bước gãy đầu tiên, không lấy bước khoẻ lẻ sau đó (bước sau thường khoẻ giả vì k6 bỏ iteration khi hết VU).
- `replicas(300, 40)`: 300 nhân 1,3 chia 40 là 9,75, làm tròn 10, cộng 1 dự phòng là 11.

## Kết quả mẫu

| Bước | Đạt được | p95 | Trung bình |
| --- | --- | --- | --- |
| 10 tới 40 | đúng tốc độ | khoảng 41 ms | khoảng 41 ms |
| 60 | khoảng 55 | khoảng 640 ms | khoảng 390 ms |
| 80 | khoảng 63 | khoảng 1900 ms | khoảng 1240 ms |

Service xử lý 2 request cùng lúc, mỗi request 40 ms, nên công suất lý thuyết 2 / 0,04 = 50 rps. Dưới 50 rps, request đến đều nên không
phải chờ: latency bằng thời gian xử lý. Trên 50 rps, mỗi giây dư 10 request vào hàng đợi, latency tăng tuyến tính theo thời gian bước. Knee
đo được là 40 vì bậc thang nhảy từ 40 lên 60; bậc mịn hơn (45, 50) sẽ cho số sát 50 hơn, nhưng không ai chạy production ở 100% công suất.
Little ở knee: 40 nhân 0,041 = 1,64 request đang xử lý, dưới 2 slot.

## Rubric tự kiểm (không chấm tự động)

- Đề xuất capacity ghi rõ: knee đo trên một replica, đỉnh dự báo, headroom và lý do chọn, N+1, và điều kiện đo (máy, cpuset, dữ liệu).
- Không dùng throughput cao nhất (63 rps ở bước 80) làm công suất: ở đó p95 gần 2 giây, SLO đã vỡ.
- Biết số đo trên laptop là tương đối: chạy lại vài lần, lấy knee thấp nhất; production cần đo trên môi trường giống thật.
