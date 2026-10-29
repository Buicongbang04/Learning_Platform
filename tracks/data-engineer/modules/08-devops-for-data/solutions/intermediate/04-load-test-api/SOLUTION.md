# Lời giải: Load test API serving

Mã đầy đủ ở `loadtest.py`.

## Cách làm

**Worker pool thay vì một task cho mỗi request.** `run_load` tạo đúng `concurrency` coroutine, cùng lấy
"vé" từ một iterator chung `iter(range(total_requests))`. Event loop asyncio chạy một luồng nên không có
race khi hai worker cùng gọi `next`. Mỗi worker chỉ `await` một request tại một thời điểm, nên số request
đang chờ không bao giờ vượt `concurrency`. Đây là mô hình **closed-loop** (số client cố định, client gửi
request tiếp khi nhận xong request trước), giống "virtual users" của k6 và Locust.

**Lỗi là dữ liệu, không phải exception.** Mọi `httpx.HTTPError` (timeout, không kết nối được, server đóng
kết nối) thành `Result(status=None, error=...)`. Một load test dừng ở lỗi đầu tiên vô dụng đúng lúc cần
nó nhất: khi hệ thống bắt đầu quá tải.

**Latency trên mọi request.** Request lỗi vẫn có latency. Nếu chỉ tính request thành công, một API timeout
50% số request vẫn có p95 đẹp. Ngược lại, lỗi trả nhanh (400 trong 2 ms) kéo p50 xuống; vì vậy luôn đọc
latency cùng với error rate, không đọc riêng.

**Nearest-rank percentile** luôn trả một giá trị đã đo thật, dễ giải thích ("95% request nhanh hơn hoặc
bằng 190 ms"). numpy mặc định nội suy tuyến tính, cho số hơi khác với mẫu nhỏ; với hàng nghìn mẫu hai cách
gần như bằng nhau. Không lấy trung bình các p95 của nhiều lần chạy hay nhiều máy: percentile không cộng
trung bình được, phải gộp mẫu (hoặc histogram) rồi tính lại.

**Throughput = số request / wall time**, không phải tổng latency. Với 5 worker và request 100 ms,
throughput khoảng 50 request/giây dù mỗi request mất 100 ms.

## Đọc kết quả với API module 09

API metric của module 09 với cache TTL: request đầu xuống DuckDB, các request sau cùng tham số trúng cache,
nên p95 vài mili giây. Đó là **cache nóng**. Một load test trung thực phải tách:

- Cache lạnh: mỗi request một bộ tham số khác (đổi `state`, khoảng ngày), đo tầng database.
- Cache nóng: lặp tham số phổ biến, đo đường nhanh.
- Tỉ lệ trộn giống production (đọc access log để biết 20% tham số chiếm bao nhiêu % request).

Request `limit=abc` trả 400 rất nhanh nhưng `error_rate = 1.0`: kịch bản tải sai thì đo nhanh cũng vô
nghĩa. Kiểm tra error rate trước khi tin con số latency.

## Những điều bài này chưa làm (và công cụ thật làm)

- **Open-loop** (tốc độ đến cố định, vd. 200 request/giây bất kể server trả chậm): bắt được hiện tượng xếp
  hàng mà closed-loop che mất (coordinated omission). k6 có executor `constant-arrival-rate`.
- **Ramp-up** tăng dần tải để tìm điểm gãy, **soak test** chạy hàng giờ để thấy rò bộ nhớ.
- **Máy bắn tải tách khỏi máy bị đo**: bắn tải từ cùng laptop thì CPU của client cũng là nút cổ chai.
- Kịch bản nhiều bước có think time, xác thực, dữ liệu tham số hoá từ CSV.

Công cụ: **k6** (kịch bản JavaScript, ngưỡng SLO bằng `thresholds`, chạy tốt trong CI), **Locust**
(kịch bản Python), **Vegeta**/**wrk** (CLI, open-loop). Trong CI/CD: chạy load test ngắn trên staging sau
deploy, fail pipeline khi `passed` là `False`, giống `sys.exit(1)` ở cuối `loadtest.py`.
