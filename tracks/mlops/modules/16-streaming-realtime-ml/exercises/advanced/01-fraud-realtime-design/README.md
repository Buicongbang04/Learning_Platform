---
title: Thiết kế pipeline chống gian lận thẻ realtime dưới 100 ms
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Thiết kế trọn đường đi của một quyết định chống gian lận: từ lúc cổng thanh toán nhận giao dịch tới lúc trả "cho qua / chặn / xác
thực thêm" trong ngân sách 100 ms p99, cùng đường offline để huấn luyện lại. Bài tập đặt mọi mảnh của module vào một bản thiết kế có
số: feature cửa sổ từ stream, freshness, online store, model, feedback loop do chính việc chặn gây ra.

## Đề bài

**Bối cảnh.** Một ví điện tử: 1 500 giao dịch mỗi giây lúc thường, 6 000 lúc đỉnh (ngày sale). Mỗi giao dịch phải có quyết định trong
100 ms p99 tính từ cổng thanh toán, nếu không cổng mặc định cho qua. Tỉ lệ gian lận khoảng 0.2%; chargeback về sau 30–90 ngày; khách
khiếu nại bị chặn nhầm trong vài giờ. Hiện có bộ luật tĩnh (hạn mức số tiền, danh sách đen) chặn khoảng 40% gian lận với 1% chặn nhầm.

Feature quan trọng theo phân tích: số giao dịch và tổng tiền của thẻ trong 1 phút, 10 phút, 1 giờ; số thiết bị khác nhau của tài
khoản trong 24 giờ; khoảng cách tới giao dịch trước; điểm rủi ro của merchant cập nhật hằng ngày.

Nộp `DESIGN.md` (tối đa 4 trang) gồm:

1. Sơ đồ kiến trúc đường online và offline (mermaid), ghi rõ thành phần nào đồng bộ trên đường nóng, thành phần nào bất đồng bộ.
2. Ngân sách độ trễ chia theo từng chặng, cộng lại không quá 100 ms p99, và cách đo từng chặng.
3. Cách tính từng nhóm feature (stream cửa sổ, batch, tính lúc request), engine chọn và lý do, cấu hình cửa sổ và watermark, chỗ ghi
   (online store nào, khoá nào), SLO freshness cho từng nhóm và đo ở đâu.
4. Feature của chính giao dịch đang chấm (chưa kịp vào stream): xử lý thế nào để không lệch giữa train và serve.
5. Model và ngưỡng: chỉ số offline, cách chọn ngưỡng theo chi phí (gian lận lọt so với chặn nhầm), có dùng online learning không.
6. Nhãn và feedback loop: nhãn đến từ đâu, độ trễ nhãn, giao dịch bị chặn không có nhãn thì xử lý ra sao (exploration, IPW).
7. Fallback khi online store chậm hoặc model chết, và khi stream bị trễ (feature cũ quá ngưỡng).
8. Rollout và giám sát: shadow, canary, chỉ số cảnh báo (consumer lag, freshness, tỉ lệ chặn, phân phối điểm).

Không có test tự động. Tự chấm bằng rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Đạt ít nhất 70/100 điểm rubric.
- Ngân sách độ trễ có số cho từng chặng, cộng không quá 100 ms, và nói rõ chặng nào tốn nhiều nhất ở p99.
- Có ít nhất một chế độ hỏng của stream (lag, watermark kẹt, partition lệch) được nói cách phát hiện và cách giảm thiểu.
- Bạn nói được giới hạn: chỗ nào là giả định cần đo trên dữ liệu thật trước khi chốt.

## Gợi ý

### Gợi ý 1

Tách ba loại feature theo độ tươi cần thiết: theo ngày (batch, materialize), theo phút (stream, push), và của chính request (tính lúc
gọi). Mỗi loại có SLO freshness riêng và một câu trả lời cho "nếu nó cũ thì sao".

### Gợi ý 2

100 ms nghe nhiều nhưng không: mạng tới service 5–10 ms, đọc online store vài ms nếu một lần gọi gom mọi khoá, model cây vài ms. Thứ
hay phá ngân sách là gọi tuần tự nhiều store và đuôi p99 của GC hay của store dùng chung.
