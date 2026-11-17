---
title: "SLO cho on-prem và chính sách hỗ trợ gửi công ty luật"
level: advanced
services: []
files:
  - path: starter/slo-policy.md
    note: Khung phụ lục SLO + chính sách hỗ trợ; bạn viết vào đây
run: []
---

## Mục tiêu

Công ty luật chuẩn bị ký gia hạn và luật sư của họ muốn một phụ lục "cam kết chất lượng dịch vụ". Bộ phận kinh doanh
của bạn định chép bảng SLA 99,9% của bản SaaS. Ở on-prem, máy, mạng, điện, backup và người bấm nút nâng cấp đều là của
khách; bạn chỉ kiểm soát phần mềm và phản ứng của đội hỗ trợ. Một cam kết không đo được, hoặc đo bằng hệ thống bạn không
có quyền xem, sẽ thành tranh chấp ở lần sự cố đầu tiên.

## Đề bài

Viết `starter/slo-policy.md` (tiếng Việt, ~900–1400 từ chưa tính bảng) gồm:

1. **SLI và SLO** cho quillo tại công ty luật (quillo 1.1.0 trên k3s của khách, 300 người dùng, giờ làm việc 8:00–19:00
   thứ Hai–thứ Sáu): mỗi SLI ghi chính xác công thức tính từ tín hiệu quillo đã có (`/metrics`, `/healthz`, log; mục
   `/metrics` và `/healthz` trong [README sản phẩm](../../../../../product/README.md)), cửa sổ đo, mục tiêu, và **ai**
   chạy hệ thống đo (Prometheus của khách? script của bạn?). Ít nhất: tính sẵn sàng của hỏi đáp, độ trễ hỏi đáp, độ tươi
   của dữ liệu nạp.
2. **Ngân sách lỗi** và điều xảy ra khi tiêu hết (phía bạn và phía khách).
3. **Ranh giới trách nhiệm**: bảng việc nào của bên nào (hạ tầng, backup, nâng cấp, chứng chỉ, SSO, giám sát), và những gì
   **không** tính vào SLO (loại trừ) kèm lý do.
4. **Chính sách hỗ trợ**: mức độ sự cố (định nghĩa bằng ảnh hưởng, có ví dụ cho quillo), thời gian phản hồi và cập nhật
   theo mức, kênh, giờ hỗ trợ, quy tắc truy cập từ xa và dữ liệu (support bundle, không mang dữ liệu khách ra ngoài), bản
   phát hành được hỗ trợ và nhịp nâng cấp.
5. **Báo cáo hằng tháng**: khách nhận gì, tính từ đâu.

Không có test tự động; tự chấm theo rubric. Bài mẫu và giải thích ở `solutions/`.

## Tiêu chí đạt

Rubric 20 điểm, đạt khi ≥ 15 và không có lỗi loại trừ:

| Tiêu chí | Điểm |
| --- | --- |
| Mỗi SLI có công thức đo được bằng tín hiệu quillo thật (tên chỉ số, nhãn, phép tính), cửa sổ và nơi đo | 5 |
| Mục tiêu có lý do (giờ làm việc, CPU-only, cỡ model), không chép số SaaS; có mục tiêu cho độ trễ dưới dạng phân vị và hiểu giới hạn của histogram | 3 |
| Ngân sách lỗi và hệ quả cụ thể cho cả hai bên | 2 |
| Bảng trách nhiệm và loại trừ đủ, công bằng, không đẩy mọi thứ sang khách | 3 |
| Mức độ sự cố định nghĩa bằng ảnh hưởng, có ví dụ quillo, thời gian phản hồi khả thi với đội của bạn | 3 |
| Quy tắc dữ liệu và truy cập từ xa khớp với cách khách vận hành (không có VPN thường trực, support bundle đã che) | 2 |
| Bản phát hành được hỗ trợ, nhịp nâng cấp, và điều kiện rollback | 2 |

Lỗi loại trừ: cam kết thứ bạn không đo được hay không kiểm soát (vd. "uptime 99,9% của máy chủ"); SLI dựa trên dữ liệu
chỉ có ở hệ thống của bạn mà khách không xem được; hứa phản hồi 24/7 mà không nêu ai trực.

## Gợi ý

### Gợi ý 1

Viết công thức SLI trước khi viết con số. Nếu không viết được câu PromQL hay lệnh tính nó, SLI đó chưa tồn tại.

### Gợi ý 2

Hỏi "khi SLO bị vi phạm, ai mở ticket và bằng chứng nằm ở đâu?". Câu trả lời quyết định hệ thống đo thuộc về ai.
