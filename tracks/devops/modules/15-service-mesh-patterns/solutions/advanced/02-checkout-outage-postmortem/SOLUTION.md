# Lời giải: postmortem checkout lỗi hàng loạt ngày Black Friday

`POSTMORTEM.md` trong thư mục này là một lời giải qua test. Rubric dưới đây chấm lập luận.

## Đọc bằng chứng

- **Thời lượng**: 25 phút có `payments_error_pct` từ 5 trở lên, 14:10 tới 14:34. Tổng `orders_failed` là 87 756.
- **Hình dạng lưu lượng**: `checkout_rps` gần như phẳng (80 tới 88) suốt sự cố, còn `payments_rps` từ 82 lên 1376 (14:19), khoảng 15,8
  lần. Lượng khách không đổi; thứ tăng là số request mỗi khách sinh ra.
- **Cấu hình giải thích hệ số**: storefront retry 3 (4 lần thử), api retry 3 (4 lần thử), không backoff, retry cả timeout. Mỗi lần thanh
  toán thành tối đa 4 x 4 = 16 request tới payments. Số đo gần 16 lần là dấu vân tay của retry chồng tầng.
- **Thứ kích hoạt**: deploy payments 2.14.0 lúc 14:05 thêm lời gọi fraud-score đồng bộ không timeout; p99 từ khoảng 290 ms lên 990 ms
  lúc 14:09, sát timeout 1 s của api. Phút 14:10 p99 vượt 1 s, timeout bắt đầu, retry bắt đầu, `payments_rps` gấp 4 trong một phút.
- **Vòng lặp**: payments quá tải nên chậm hơn, chậm hơn nên nhiều timeout hơn, nhiều timeout nên nhiều retry hơn. Đây là metastable
  failure: hệ thống ở trạng thái xấu tự duy trì sau khi thứ kích hoạt đã mất.
- **Scale 14:18**: 8 pod x 25 kết nối = 200, đúng `max_connections` của Postgres. Thêm pod không thêm năng lực ở nút cổ chai (pool
  Postgres, fraud-score 2 replica); lỗi giảm một phút (73,5% lúc 14:19) rồi quay lại, còn tải vào payments đạt đỉnh đúng phút đó.
- **Rollback 14:24**: gỡ thứ kích hoạt, nhưng tải 15 lần vẫn đó; lỗi chỉ giảm từ khoảng 90% xuống 77%.
- **Tắt retry 14:31**: cắt hệ số khuếch đại, `payments_rps` từ 1236 xuống 612 rồi 341, lỗi về dưới 5% sau 4 phút.
- **Không trừ tiền hai lần**: api gửi Idempotency-Key, nên retry không tạo giao dịch trùng. Đáng ghi nhận trong postmortem.

## Pattern đáng có trong phần 5

- Availability: Retry (một tầng, backoff, jitter, budget), Circuit Breaker (api trước payments), Throttling hay load shedding ở payments,
  Bulkhead cho fraud-score, Queue-Based Load Leveling cho chấm điểm fraud bất đồng bộ.
- Data Management: Saga hay Compensating Transaction nếu chấm điểm fraud sau authorize; Transactional Outbox cho event ledger.
- Design & Implementation: Sidecar (đưa retry, timeout vào mesh để có một chỗ cấu hình và metric retry), Gateway Offloading.
- Management & Monitoring: External Configuration Store (cờ tắt retry đã cứu sự cố, cần cho mọi tầng), Health Endpoint Monitoring.

## Rubric (10 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Tác động bằng số | 1 | Thời lượng, số đơn, đỉnh lưu lượng đúng với dữ liệu; nói không có trừ tiền hai lần và vì sao |
| Timeline | 1 | Có cả mốc kích hoạt (14:05), mốc vượt ngưỡng, các hành động và hiệu quả của từng hành động |
| Thứ kích hoạt và nguyên nhân gốc | 2 | Phân biệt deploy 2.14.0 (kích hoạt) với retry chồng tầng không backoff (gốc); tính được hệ số 16 từ cấu hình và khớp với số đo |
| Vì sao khắc phục đầu tiên không hiệu quả | 2 | Scale không giúp vì nút cổ chai dùng chung (pool Postgres); rollback không đủ vì trạng thái quá tải tự duy trì |
| Review theo pattern | 2 | Mỗi pattern gắn với một điểm cụ thể trong sự cố; không liệt kê cho đủ nhóm; nói đánh đổi (breaker trả lỗi nhanh cho khách, queue làm thanh toán chậm xác nhận) |
| Action items | 1 | Đo được, có người và hạn, đủ phòng ngừa, phát hiện, giảm thiểu; ưu tiên rõ |
| Blameless | 1 | Không quy lỗi cho cá nhân (người deploy, người trực); nói về hệ thống và quy trình |

Dưới 7 điểm: thường là dừng ở "deploy 2.14.0 làm chậm payments", hay coi scale và rollback là "làm sai" thay vì giải thích vì sao chúng
không chạm nút cổ chai.

## Lỗi hay gặp

- Đếm thời lượng từ alert đầu tiên tới lúc đóng incident thay vì từ số liệu.
- Kết luận "payments không đủ pod": số liệu lúc 14:19 cho thấy thêm pod chỉ thêm tải.
- Action item "cẩn thận hơn khi deploy": không đo được, không có người phụ trách.
- Pattern đặt sai nhóm hay chỉ có tên, không nói hiện trạng và đề xuất cụ thể cho Olist Shop.
