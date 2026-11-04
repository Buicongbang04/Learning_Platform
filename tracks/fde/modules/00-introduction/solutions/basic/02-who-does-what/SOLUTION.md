# Lời giải: Ai làm việc này?

Ranh giới giữa các vai khác nhau tuỳ công ty (công ty nhỏ có khi một người kiêm cả FDE lẫn SE). Đáp án dưới đây theo
bảng trách nhiệm ở phần 2 của lý thuyết module: công ty có đủ bốn vai.

| Câu | Đáp án | Vì sao | Vai gần nhất vì sao vẫn sai |
| --- | --- | --- | --- |
| `demo-before-contract` | SE (presales) | Chưa ký hợp đồng, mục tiêu là qua vòng mua hàng: demo trên dữ liệu mẫu và bộ questionnaire chuẩn là việc presales | FDE có thể được kéo vào khi khách đòi chạy thử trên dữ liệu thật, nhưng ở đây dữ liệu mẫu và câu trả lời chuẩn đủ dùng |
| `pilot-ca-rotated` | FDE | Pilot đang do bạn triển khai, cấu hình riêng của khách, chưa có runbook: người triển khai sửa tại chỗ rồi ghi lại cách sửa | Support nhận sự cố của hệ thống đã vào vận hành theo quy trình; pilot chưa bàn giao thì chưa phải ca của họ |
| `known-issue` | Support | Production ổn định, lỗi đã biết, cách sửa đã có runbook: đúng quy trình hỗ trợ, không cần kỹ sư ra hiện trường | FDE xử lý được nhưng tốn thời gian của người đang triển khai cho khách khác; đó là lý do phải bàn giao runbook |
| `three-customers-same-ask` | Product (PM) | Quyết định tính năng chung cho nhiều khách và thứ tự trên roadmap là việc của product | FDE cung cấp bằng chứng (ai cần, vì sao, workaround hiện tại) nhưng không tự đưa vào sản phẩm chung |
| `legacy-connector` | FDE | Một khách, một hệ thống cũ, cần ngay cho pilot, chưa biết có tái dùng không: FDE viết connector tại khách, giữ nó tách khỏi lõi | Product chỉ nên nhận khi nhiều khách cần; làm ngay thành tính năng chung là quá sớm |
| `noexec-reports` | Product (PM) | Lỗi lặp ở nhiều khách, cần quyết định bản phát hành và thông báo cho mọi khách: việc của product (cùng engineering) | FDE đã làm đúng phần của mình: thu bằng chứng từ hiện trường và báo về |
| `demo-not-our-workflow` | FDE | Quan sát workflow thật và dựng lại prototype trên dữ liệu của một khách là đúng việc "một khách, nhiều năng lực" | SE có thể dựng lại demo, nhưng hai ngày ngồi cùng đội vận hành và prototype trên dữ liệu thật thuộc về FDE |

**`bring-back-to-product`: a và c.** Lỗi cài đặt kèm cách tái hiện ở lab giúp sửa sản phẩm cho mọi khách; yêu cầu tính
năng đã gộp (bao nhiêu khách, vì sao, workaround) giúp product ưu tiên. **b** sai: fork riêng của khách merge nguyên vào
main kéo theo giả định của một khách vào mọi bản cài (module 10 nói về fork tối thiểu). **d** sai: dữ liệu thật của khách
không rời môi trường của họ khi không có thoả thuận; tái hiện lỗi bằng dữ liệu tổng hợp hay dữ liệu đã được khách đồng
ý chia sẻ (module 07, 08).
