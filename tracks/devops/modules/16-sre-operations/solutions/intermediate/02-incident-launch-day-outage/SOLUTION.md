# Lời giải: load test xanh, ngày ra mắt đỏ

## Nguyên nhân

Bản 2.4.0 đổi cách xử lý khi quá tải: thay vì xếp hàng, nó trả **503 ngay lập tức** cho request vượt 2 slot. Kịch bản gốc có hai lỗi
khiến cổng không thấy:

1. **Không đo lỗi.** Chỉ có threshold `http_req_duration: p(95)<300`, không `check` mã trả về, không threshold trên `http_req_failed`.
   `http_req_duration` mặc định tính **mọi** response, kể cả 503. Response lỗi trả ngay trong vài trăm micro giây nên kéo p95 xuống rất
   thấp: bản hỏng trông nhanh hơn bản tốt. Trong tóm tắt, `http_req_failed` của bản 2.4.0 khoảng 90% mà không ai nhìn.
2. **Mô hình tải đóng.** `vus: 20` nghĩa là 20 người dùng ảo, mỗi người gửi request tiếp theo ngay khi nhận response. Server trả lỗi nhanh
   thì VU lặp nhanh hơn, "throughput" tăng vọt (hàng nghìn request/giây toàn 503), đó là con số "cao hơn mọi bản trước". Với 2.3.0, 20 VU
   chỉ đạt khoảng 100 rps và latency tự giãn ra; kịch bản không bao giờ tạo đúng 80 rps đến đều như ngày ra mắt. Bản 2.4.1 (xếp
   hàng, không trả lỗi) vẫn bị cổng cũ chặn vì 20 VU chờ nhau làm latency lên khoảng 400 ms; cổng cũ chỉ thấy được bản chậm, không thấy
   bản hỏng nhanh.

## Sửa

```javascript
scenarios: { launch: { executor: "constant-arrival-rate", rate: 80, timeUnit: "1s", duration: "6s", preAllocatedVUs: 20, maxVUs: 200 } },
thresholds: {
  "http_req_duration{expected_response:true}": ["p(95)<300"],
  http_req_failed: ["rate<0.01"],
  checks: ["rate>0.99"],
},
```

- `constant-arrival-rate` (mô hình mở): 80 request/giây đến đều bất kể server nhanh hay chậm, đúng như traffic thật.
- Latency chỉ tính request thành công (`expected_response:true`), đúng định nghĩa SLO. Lỗi được đo riêng bằng `http_req_failed` và
  `check` mã 200.
- Kết quả: 2.3.0 qua (p95 khoảng 41 ms, 0% lỗi); 2.4.0 bị chặn vì khoảng một nửa request là 503; 2.4.1 bị chặn vì hàng đợi dài ra (công
  suất 50 rps dưới 80 rps dự báo), p95 lên hàng giây.

## Bài học cho postmortem

- Cổng chất lượng phải mã hoá đúng SLO: thành công **và** latency, đo ở traffic dự báo. Một cổng chỉ nhìn latency sẽ thưởng cho bản
  fail nhanh.
- "Throughput cao bất thường" là tín hiệu đáng ngờ chứ không phải tin tốt.
- Action item: mẫu kịch bản chuẩn của công ty (arrival-rate, threshold lỗi và latency theo SLO), review threshold như review code, và
  một test của chính cổng (chạy với bản cố ý hỏng, phải đỏ), giống `test_original_script_reproduces_launch_day` của bài.
