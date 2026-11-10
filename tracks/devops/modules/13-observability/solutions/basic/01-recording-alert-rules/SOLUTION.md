# Lời giải: recording rule và alert rule cho API Olist Shop

## Recording rule

```yaml
- record: job:http_requests:rate5m
  expr: sum by (job) (rate(http_requests_total[5m]))
- record: job:http_requests_errors:ratio_rate5m
  expr: |
    sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
    /
    sum by (job) (rate(http_requests_total[5m]))
- record: job_path:http_request_duration_seconds:p95_5m
  expr: histogram_quantile(0.95, sum by (job, path, le) (rate(http_request_duration_seconds_bucket[5m])))
```

- Tên theo quy ước `level:metric:operations`: `job:` nói kết quả chỉ còn nhãn `job`, phần cuối nói phép tính (`rate5m`,
  `ratio_rate5m`, `p95_5m`). Người đọc dashboard biết ngay nhãn nào còn và cửa sổ bao nhiêu.
- `rate` trước, `sum` sau. `rate` xử lý counter reset trên **từng series**; `sum` trước rồi mới `rate` thì một instance restart làm tổng
  tụt về thấp và `rate` hiểu đó là reset, cho ra đỉnh giả.
- Tỉ lệ lỗi: hai vế cùng `sum by (job)` để nhãn khớp nhau khi chia. Khi không có request nào, phép chia là `0/0 = NaN`; `NaN > 0.05`
  là false, nên alert im lặng đúng như mong muốn.
- p95: `histogram_quantile` cần nhãn `le` để biết biên bucket, nên `sum by (job, path, le)`. Bỏ `le` thì hàm không có gì để nội suy.
  Kết quả là ước lượng tuyến tính trong bucket, độ chính xác phụ thuộc cách chia bucket (xem README mục 2).
- `interval: 15s` cho group recording: không bắt buộc. Rule tính lại mỗi 15 giây thay vì theo `evaluation_interval` toàn cục.

## Alert

- `OlistApiHighErrorRate`: `job:http_requests_errors:ratio_rate5m{job="olist-api"} > 0.05`, `for: 5m`, `severity: page`. Đây là
  triệu chứng người dùng thấy (request lỗi), nên đáng đánh thức người trực.
- `OlistApiSlowOrders`: p95 của `/orders/{order_id}` quá 0,5 giây trong 10 phút, `severity: ticket`. Chậm nhưng vẫn chạy được, nên mở
  ticket trong giờ làm việc thay vì page.
- `for` lọc nhiễu ngắn. Đổi lại, alert bắn trễ ít nhất bằng `for` cộng thời gian để `rate` có đủ mẫu.
- `annotations.summary` dùng `{{ $value | humanizePercentage }}`, `humanizeDuration` để người trực đọc được ngay con số.

## Unit test của bạn

`rules.test.yml` mẫu có ba nhóm:

1. Lỗi 20% (48 request 200 và 12 request 503 mỗi phút): `rate5m` là 1, `ratio` là 0,2; ở phút 3 alert chưa bắn (đang pending), ở phút
   10 đã bắn. Ca phút 3 bắt được `for` quá ngắn.
2. Lỗi 2%: không bắn. Ca này bắt được ngưỡng sai hay biểu thức luôn đúng.
3. Histogram: `/orders/{order_id}` có mọi request trong bucket `le="1"`, nên p95 là 0,95 và alert bắn; `/stats/revenue-by-state` nằm
   trong bucket `le="0.25"`, p95 là 0,2375. Nhóm thứ tư cho `/orders/{order_id}` nhanh: không bắn.

Test của bài còn "đột biến" rule của bạn (nhân đôi giá trị, alert không bao giờ bắn, alert luôn bắn) và đòi `rules.test.yml` phải fail.
Một bộ test chỉ có ca "không bắn" khi không có dữ liệu sẽ qua với mọi rule, kể cả rule hỏng: đó là kiểu test im lặng sinh ra alert im lặng.

## Kiểm bằng dữ liệu thật

`promtool test rules` chỉ chứng minh rule đúng với dữ liệu **bạn tự viết**. Nếu bạn đoán sai tên label (ví dụ `code` thay vì
`status`), cả rule lẫn test đều sai theo cùng một cách và vẫn pass. Test cuối dựng Olist Shop thật, gửi request (có 503 khi Redis bị dừng)
rồi hỏi Prometheus: rule nạp không lỗi, và cả ba recording rule ra số. Trong dự án thật, chạy truy vấn đó trên Prometheus staging trong
CI trước khi merge rule.

Lưu ý khi tự kiểm trên stack: counter mới xuất hiện có giá trị đầu là số đã đếm, nên `rate` cần ít nhất hai lần scrape **sau** khi series
xuất hiện mới ra số khác 0. Test gửi traffic hai đợt cách nhau một lần scrape vì lẽ đó.
