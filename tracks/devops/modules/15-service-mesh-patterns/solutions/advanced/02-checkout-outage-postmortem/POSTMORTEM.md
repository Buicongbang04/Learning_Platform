# Postmortem: checkout lỗi hàng loạt ngày 2026-11-27

## 1. Tóm tắt

- Ngày Black Friday 2026-11-27, payments lỗi từ 5% trở lên trong 25 phút (14:10 tới 14:34, giờ São Paulo); ở đỉnh, 9 trên 10 lần thanh toán thất bại.
- Kích hoạt: payments 2.14.0 (14:05) thêm lời gọi fraud-score đồng bộ không có timeout, đẩy p99 của payments từ khoảng 290 ms lên gần 1 giây, đúng ngưỡng timeout 1 giây của api.
- Nguyên nhân gốc: retry chồng tầng không backoff (storefront 4 lần thử, api 4 lần thử) nhân mỗi lần thanh toán thành tối đa 16 request tới payments; payments quá tải, chậm thêm, gây thêm timeout và retry. Vòng lặp tự duy trì cả sau khi rollback.
- Hồi phục khi tắt retry của storefront và giảm retry của api (14:31); scale và rollback trước đó không đủ.

## 2. Tác động

- 87 756 đơn thất bại (cộng cột `orders_failed`), trong đó phần lớn ở 14:11 tới 14:31.
- Phút đỉnh 14:19: checkout nhận 87 request mỗi giây, payments nhận 1376 request mỗi giây, khoảng 15,8 lần.
- p99 của payments chạm 5000 ms (timeout của server) từ 14:12 tới 14:25.
- Không có trừ tiền hai lần: api gửi Idempotency-Key nên các lần retry của cùng một đơn không tạo giao dịch mới.

## 3. Timeline

| Thời điểm | Sự kiện |
| --- | --- |
| 14:05 | Deploy payments 2.14.0, thêm gọi fraud-score đồng bộ; p99 bắt đầu tăng (420 ms) |
| 14:09 | p99 payments 990 ms, sát timeout 1 s của api; storefront bắt đầu log upstream timeout |
| 14:10 | Lỗi payments vượt 5% (22,5%), payments nhận 322 request mỗi giây cho 86 request vào checkout |
| 14:11 | Alert CheckoutErrorRate gọi on-call |
| 14:15 | Alert PaymentsErrorRate; CPU payments 100%, p99 5000 ms |
| 14:18 | Scale payments 4 lên 8 pod; lỗi giảm một phút rồi quay lại vì pool Postgres 200/200 |
| 14:24 | Rollback payments về 2.13.2; lỗi chỉ giảm nhẹ |
| 14:31 | Tắt retry của storefront, api retry 3 xuống 1; payments nhận 612 rồi 341 request mỗi giây |
| 14:35 | Lỗi payments dưới 5% (3,1%) |
| 14:38 | Chỉ số về như 14:00 |

## 4. Nguyên nhân

### Vì sao

1. Vì sao checkout lỗi? payments trả lỗi hay quá timeout cho gần 90% request.
2. Vì sao payments quá tải? Nó nhận gấp khoảng 16 lần lượng thanh toán thật, vì mỗi lần thử của storefront tới api lại thành 4 lần thử của api tới payments, không backoff.
3. Vì sao retry bùng lên? p99 của payments vượt timeout 1 s của api sau khi 2.14.0 thêm lời gọi fraud-score đồng bộ không timeout; mỗi request chậm thành một timeout, mỗi timeout thành thêm request.
4. Vì sao rollback không cứu được? Lúc đó payments đã bão hoà bởi chính lượng retry (CPU, pool Postgres), nên chậm dù không còn fraud-score: hệ thống ở trạng thái quá tải tự duy trì (metastable).
5. Vì sao scale không cứu được? 8 pod x 25 kết nối chạm `max_connections` 200 của Postgres; thêm pod chỉ thêm người chờ cùng một nút cổ chai.

### Yếu tố góp phần

- Không có circuit breaker hay retry budget ở api; storefront và api đều retry cả timeout.
- payments nhận mọi request, không giới hạn đồng thời, không trả 503 sớm khi quá tải.
- Dashboard không đặt cạnh nhau request vào storefront và request vào payments, nên mất 18 phút mới thấy hệ số khuếch đại.
- Deploy payments sát giờ cao điểm Black Friday, không canary.

## 5. Review theo pattern

| Pattern | Nhóm | Hiện trạng | Đề xuất |
| --- | --- | --- | --- |
| Retry | Availability | Retry ở hai tầng, 3 lần mỗi tầng, không backoff, retry cả timeout | Chỉ retry ở một tầng (api), backoff có jitter, retry budget 10% request; storefront không retry POST |
| Circuit Breaker | Availability | Không có | Breaker trong api cho payments, mở khi lỗi trên 50% trong 10 giây, trả lỗi nhanh cho storefront |
| Throttling | Availability | payments nhận không giới hạn | Giới hạn đồng thời mỗi pod theo pool, quá thì 503 kèm Retry-After |
| Bulkhead | Availability | Lời gọi fraud-score dùng chung worker và pool với ghi ledger | Pool riêng cho fraud-score, timeout 300 ms, có fallback cho đơn nhỏ |
| Queue-Based Load Leveling | Availability | Chấm điểm fraud đồng bộ trong request | Chấm điểm sau authorize qua hàng đợi, giữ đơn ở trạng thái chờ duyệt |
| Saga | Data Management | Không có cách huỷ khi fraud trả kết quả muộn | Saga authorize, fraud, capture; bước bù là void authorization |
| Sidecar | Design & Implementation | Retry, timeout viết rải rác trong code từng service | Đưa retry, timeout vào HTTPRoute của mesh, một chỗ cấu hình và có metric retry |
| Health Endpoint Monitoring | Management & Monitoring | /readyz không phản ánh pool cạn | /readyz báo lỗi khi pool đầy liên tục, cộng probe tổng hợp cho checkout |
| External Configuration Store | Management & Monitoring | Chỉ storefront có cờ tắt retry | Mọi cấu hình retry, timeout ở một store chung, đổi được không cần deploy |

## 6. Action items

| Việc | Loại | Người phụ trách | Hạn |
| --- | --- | --- | --- |
| Bỏ retry POST ở storefront, api retry có backoff, jitter và budget | Phòng ngừa | Team checkout | 2026-12-04 |
| Timeout 300 ms và bulkhead cho lời gọi fraud-score | Phòng ngừa | Team payments | 2026-12-04 |
| Giới hạn đồng thời và trả 503 sớm ở payments | Phòng ngừa | Team payments | 2026-12-11 |
| Alert theo tỉ số request vào payments trên request vào checkout (> 2 trong 3 phút) | Phát hiện | Team platform | 2026-12-04 |
| Dashboard đặt cạnh nhau lưu lượng các tầng và số retry của proxy | Phát hiện | Team platform | 2026-12-04 |
| Cờ tắt retry cho mọi tầng, ghi vào runbook SEV-1 | Giảm thiểu | Team platform | 2026-12-11 |
| Đóng băng deploy 48 giờ quanh Black Friday, deploy khác qua canary | Phòng ngừa | Engineering manager | 2026-12-18 |

## 7. Bài học

- Retry là tải thêm: chồng tầng thì nhân lên, và khi hệ thống đã chậm thì retry làm nó chậm hơn.
- Rollback chỉ gỡ nguyên nhân kích hoạt; hệ thống quá tải tự duy trì cần cắt tải (tắt retry, load shedding) mới thoát.
- Scale ngang không giúp khi nút cổ chai là tài nguyên dùng chung (pool Postgres).
- Idempotency-Key đã cứu khách khỏi bị trừ tiền hai lần; giữ nó cho mọi lời gọi có tác dụng phụ.
