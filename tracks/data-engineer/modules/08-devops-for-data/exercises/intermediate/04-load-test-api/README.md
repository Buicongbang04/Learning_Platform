---
title: Load test API serving với httpx + asyncio, đo p50/p95 và so với SLO
level: intermediate
services: []
files:
  - path: starter/loadtest.py
    note: 5 TODO
  - path: tests/test_load_test_api.py
    note: Không sửa, test tự dựng server giả và API metric của module 09 trên 127.0.0.1
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/intermediate/04-load-test-api -q
---

## Mục tiêu

Tự viết một load generator nhỏ để trả lời câu hỏi "API này có chịu được tải mục tiêu không?" bằng con số:
p50/p95/p99 latency, throughput, error rate, rồi so với SLO để ra kết luận đạt/không đạt, như một bước
trong CI/CD trước khi deploy. Bài này là bản tối giản của k6/Locust, đủ để hiểu chúng đo cái gì.

## Đề bài

Hoàn thành `starter/loadtest.py` (dùng `httpx` và `asyncio`, đã có trong venv):

1. **`percentile(values, q)`** theo phương pháp nearest-rank: sắp xếp tăng dần, lấy phần tử thứ
   `ceil(q / 100 * n)` (đếm từ 1); `q = 0` lấy phần tử nhỏ nhất. Rỗng hoặc `q` ngoài [0, 100]: `ValueError`.
2. **`summarize(results, wall_time_s)`** trả dict `requests`, `errors`, `error_rate`, `throughput_rps`,
   `p50_ms`, `p95_ms`, `p99_ms`, `max_ms`. Request lỗi là request không `ok` (không có response, hoặc status
   ngoài 200–399). Latency tính trên **mọi** request.
3. **`check_slo(summary, slo)`** trả danh sách chỉ tiêu vi phạm theo thứ tự `p95_ms`, `error_rate`,
   `throughput_rps`. Bằng đúng ngưỡng là đạt.
4. **`run_load(url, *, total_requests, concurrency, timeout_s)`** (async): gửi đủ `total_requests` request
   GET, **không bao giờ** quá `concurrency` request đang chờ cùng lúc. Timeout và lỗi kết nối được ghi
   thành `Result(status=None, error=<tên exception>)`, không làm dừng lần chạy. Trả `(results, wall_time_s)`.
5. **`load_test(...)`**: chạy `run_load` bằng `asyncio.run`, gộp `summarize` + `check_slo`, thêm khoá
   `violations` và `passed`.

Test dựng hai loại server trên 127.0.0.1: server giả có endpoint nhanh, chậm (`/slow?ms=100`), lỗi định kỳ
(`/flaky`, cứ request thứ 4 trả 500) và treo (`/hang`); và **API metric của module 09** (lời giải bài
`09-serving-bi/intermediate/03-metrics-api-cache`) trên DuckDB in-memory, để chạy một load test thật có SLO.

## Tiêu chí đạt

- `percentile` đúng nearest-rank, `summarize` ra đúng số trên bộ kết quả biết trước (p50 = 100 ms,
  p95 = 190 ms, error rate 10%, throughput 10 request/giây).
- `run_load` gửi đủ số request; server không bao giờ thấy quá `concurrency` request cùng lúc; 20 request
  100 ms với 5 luồng xong dưới 1,2 giây (chạy tuần tự sẽ mất 2 giây).
- 500, timeout và lỗi kết nối đều được đếm là lỗi, có latency, không làm crash.
- Load test API module 09 với SLO p95 không quá 1000 ms, không lỗi: `passed is True`, và phần lớn request
  trúng cache. Request sai tham số (`limit=abc`, trả 400) làm `error_rate = 1.0` và `passed is False`.
- `uv run pytest … -q` pass 12 test trong vài giây.

## Gợi ý

### Gợi ý 1

Có hai cách giới hạn đồng thời: `asyncio.Semaphore(concurrency)` bọc quanh mỗi request (tạo
`total_requests` task), hoặc tạo đúng `concurrency` worker cùng lấy việc từ một iterator chung
(`remaining = iter(range(total_requests))`, mỗi worker `for _ in remaining:`). Cách worker không tạo hàng
nghìn task một lúc, hợp với tải lớn. Chạy chúng bằng `asyncio.gather`.

### Gợi ý 2

```python
start = time.perf_counter()
try:
    resp = await client.get(url)
    return Result(resp.status_code, time.perf_counter() - start)
except httpx.HTTPError as exc:          # gồm TimeoutException, ConnectError
    return Result(None, time.perf_counter() - start, type(exc).__name__)
```

Dùng `time.perf_counter()` chứ không dùng `time.time()`: đồng hồ hệ thống có thể bị NTP chỉnh giữa chừng.
Đặt `httpx.Limits(max_connections=concurrency)` để connection pool không thành nút cổ chai.
