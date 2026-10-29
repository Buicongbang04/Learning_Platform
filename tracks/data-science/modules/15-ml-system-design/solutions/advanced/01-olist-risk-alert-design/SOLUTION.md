# Hướng làm: design doc hệ thống cảnh báo đơn rủi ro

Bài Advanced không có đáp án duy nhất. Dưới đây là số liệu tham chiếu trên Olist thật (bản cài đặt
tham chiếu của người soạn), các quyết định cần cân nhắc và rubric.

## Số liệu tham chiếu

| Con số | Giá trị | Nguồn |
| --- | --- | --- |
| Đơn giao xong, tỉ lệ trễ | 96 470, 8.1% | Basic 03, Intermediate 01 |
| Review xấu ở đơn trễ / đúng hẹn | 54.1% / 9.2% | Lý thuyết mục 3 |
| Đơn trễ mỗi tuần (06/2017 – 07/2018) | trung vị 61, phân vị 90 là 289, tối đa 565; 18/61 tuần trên 100 | `weekly_late_volume` |
| PR-AUC test lúc đặt hàng / lúc giao vận chuyển | 0.120 / 0.378 | Intermediate 01 |
| Luật "còn dưới 5 ngày" | precision 0.427, recall 0.352, khoảng 99 R$/tuần | Lý thuyết mục 3 |
| 95% nhãn trễ có sau | 25.4 ngày kể từ lúc mua | Basic 03 |
| Holdout 20% đủ power | khoảng 39 tuần (70 cảnh báo/tuần) | Lý thuyết mục 5 |
| Recall top 5% theo vùng | N/NE 31.7%, SP 43.6%, khác 17.9% | Intermediate 03 |

Chính sách chọn trên validation (model lúc giao vận chuyển, lưới ngưỡng 0.1–0.5, trần 25–1 000, tin
nhắn 0.5 R$, V = 30 R$, Δ = 0.15), chấm trên test (23 tuần):

| Chính sách | Cảnh báo | Precision | R$/tuần | Cảnh báo mỗi tuần (min / trung vị / max) |
| --- | --- | --- | --- | --- |
| Validation chọn: ngưỡng 0.1, không trần thực tế | 5 505 | 0.200 | 96.1 | 8 / 216 / 656 |
| Ngưỡng 0.2, trần 75 | 1 096 | 0.453 | 73.4 | 2 / 52 / 75 |
| Chỉ trần 70 (k cố định) | 1 610 | 0.331 | 69.3 | 70 / 70 / 70 |

Điều đáng viết vào doc: validation (có khủng hoảng 02–03/2018) chọn "cảnh báo mọi đơn trên 0.1" vì giá
trị tuyến tính theo số cảnh báo khi precision còn trên break-even. Nhưng đội CSKH không xử lý được 656
cảnh báo một tuần nếu là gọi điện; với tin nhắn tự động thì được. **Kênh hành động quyết định có cần
trần không.** Chỉ trần cố định (k = 70) có precision thấp hơn ngưỡng + trần vì phải lấp đầy cả tuần
yên ả.

## Các quyết định cần cân nhắc

- **Thời điểm dự đoán**: lúc giao vận chuyển (PR-AUC gấp ba, vẫn còn trung vị 20.3 ngày). Nêu rõ khác
  model "lúc đơn vừa giao" của module 10/11 vì hành động khác.
- **Baseline**: luật "còn dưới 5 ngày" ngang model về tiền. Doc tốt đề xuất ra mắt luật trước (pha 1),
  model thay khi thắng luật trên holdout (pha 2).
- **Giá trị**: khoảng 100 R$/tuần dưới giả định cơ sở. Doc tốt nói thẳng con số nhỏ, chỉ ra V và Δ là
  giả định quyết định, đề xuất cách đo (thí nghiệm, bài Advanced 02).
- **Serving**: batch theo giờ trên sự kiện giao vận chuyển; fallback về luật.
- **Monitoring**: số đơn quá hẹn chưa giao (có ngay), phân phối điểm, số cảnh báo / trần; metric chất
  lượng chỉ trên cohort đã chín (30 ngày).
- **Retrain**: trên đơn không can thiệp với trọng số holdout (Intermediate 02).
- **Fairness**: equal opportunity theo vùng; bang khác có recall thấp nhất.
- **Phương án đã loại** (ví dụ): model lúc đặt hàng (PR-AUC 0.120, dựa vào vùng); online serving
  (không cần latency); gọi điện CSKH (break-even 111%); dùng model review xấu lúc đơn đã giao (quá muộn
  để hành động).

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Đóng khung | 15 | Quyết định, người hành động, hành động, thời điểm dự đoán có lý do; giải thích khác module 10/11; có baseline không ML |
| Metric và tiền | 15 | Cây metric; break-even precision; giả định C, V, Δ tách bạch và có độ nhạy |
| Dữ liệu và nhãn | 10 | Bảng feature theo thời điểm có mặt; label delay có số; nêu rủi ro leak và skew |
| Model | 10 | Thang baseline, đánh giá theo thời gian, so với luật trên giá trị tiền |
| Chính sách và năng lực | 10 | Dùng phân phối số đơn trễ theo tuần; ngưỡng + trần chọn trên validation, báo cáo trên test; kế hoạch khi chạm trần |
| Serving, monitoring, retrain | 15 | Batch có lý do, fallback, log quyết định; monitoring với nhãn chậm; retrain tránh feedback loop |
| Thí nghiệm | 10 | Holdout, cỡ mẫu và thời lượng tính đúng, quy tắc quyết định viết trước |
| Fairness và rủi ro | 10 | Metric theo vùng có số, chọn định nghĩa có lý do, ít nhất 2 rủi ro khác |
| Phương án đã loại, câu hỏi mở | 5 | Ít nhất 2 phương án kèm lý do; câu hỏi mở có cách trả lời |

Từ 70 điểm: đủ đưa vào design review. Từ 85 điểm: doc mà một DS senior ký tên được.

## Sai lầm hay gặp

- Viết như báo cáo model (dữ liệu → model → AUC) thay vì như thiết kế hệ thống.
- Không có số năng lực vận hành; giả định CSKH làm được mọi cảnh báo.
- Chọn ngưỡng trên test.
- Không nhắc label delay, nên kế hoạch monitoring đo sai trong 3–4 tuần đầu của mỗi cohort.
