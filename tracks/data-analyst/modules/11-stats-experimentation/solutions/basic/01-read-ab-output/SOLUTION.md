# Lời giải: đọc output A/B và chọn kiểm định, chọn công cụ

Các con số trong câu hỏi là ví dụ giả định. Mỗi câu dưới đây giải thích vì sao đáp án đúng và vì sao các
phương án còn lại không hợp.

## Chọn kiểm định

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `test-for-rate` | c | Metric 0/1, hai nhóm độc lập chia ngẫu nhiên: z-test hai tỉ lệ (bình phương thống kê z bằng chi-square của bảng 2×2 không hiệu chỉnh Yates). Paired t-test theo ngày (a) bỏ phí thông tin cấp người và giả định ghép cặp không có; correlation (b) không cho chênh lệch và khoảng tin cậy theo đơn vị business; Mann-Whitney trên thời gian ở lại (d) trả lời một câu hỏi khác |
| `test-for-revenue` | b | CFO hỏi tổng doanh thu, tức **trung bình** × số người. Với 40 nghìn người mỗi nhóm, trung bình mẫu có phân phối gần chuẩn (CLT) dù dữ liệu lệch, nên Welch t-test dùng được; cắt đuôi (winsorize/cap) ở ngưỡng **đặt trước** giảm phương sai rất mạnh (bài Advanced 01: độ lệch chuẩn doanh thu 30 ngày giảm hơn 4 lần khi cắt ở p99). Mann-Whitney (a) so thứ hạng, không so trung bình: có thể "có ý nghĩa" khi tổng doanh thu không đổi. Chi-square trên người có mua (c) bỏ mất độ lớn đơn. So trung vị bằng mắt (d) không có độ bất định |
| `p-value-meaning` | d | p là xác suất thấy chênh lệch ít nhất cỡ này **nếu H0 đúng** (A và B như nhau). Không phải P(B tốt hơn) (a, đó là câu hỏi Bayesian), không phải xác suất lỗi đo (b), không đo độ lớn hiệu ứng (c) |

## Đọc output

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `ci-vs-mde` | a | Khoảng [−0.2; +1.4] vừa chứa 0 (có thể không có hiệu ứng) vừa chứa 0.5 (có thể hiệu ứng đáng làm). Thí nghiệm thiếu power cho câu hỏi này. "Không có hiệu ứng" (b) là đọc sai: không bác bỏ H0 không chứng minh H0. Ước lượng điểm (c) không đủ khi khoảng rộng. "Chắc chắn nhỏ hơn MDE" (d) cần cả khoảng nằm dưới 0.5 |
| `srm` | c | Chi-square: (600² / 50 000) × 2 = 14.4, p ≈ 0.00015. Lệch 1.2% nghe nhỏ nhưng với 100 nghìn người là rất khó xảy ra do ngẫu nhiên: có lỗi ở chia nhóm, ghi log, lọc bot hoặc redirect. Lỗi đó thường liên quan tới hành vi (ví dụ trang B tải chậm làm người dùng chậm rời đi trước khi được ghi nhận), nên hiệu ứng đo được không tin được. Bỏ bớt người (b) không sửa được nguyên nhân; Welch (d) không liên quan |
| `guardrail` | b | Guardrail là điều kiện đặt trước: vượt ngưỡng thì không ship, dù metric chính tốt. Thời gian tải trang thường ảnh hưởng tới doanh thu dài hạn mà thí nghiệm ngắn không thấy. Ship một nửa (c) vẫn gây hại cho nửa đó; bỏ guardrail (d) là đổi luật sau khi thấy kết quả |
| `peeking` | a | Nhìn p-value mỗi ngày và dừng ngay khi p < 0.05 làm false positive tăng mạnh: mô phỏng 28 lần nhìn (mỗi ngày) khi A và B như nhau cho khoảng **27%** số thí nghiệm "có ý nghĩa" ở một thời điểm nào đó, so với 5% nếu chỉ nhìn ở cuối. Kiểm định một phía (c) chỉ đổi ngưỡng; chờ p < 0.01 (d) vẫn là peeking. Muốn được dừng sớm thì phải thiết kế trước (sequential testing) |
| `novelty` | d | Lift giảm dần theo tuần là dấu hiệu novelty effect (người dùng tò mò với cái mới). Hiệu ứng dài hạn gần với các tuần sau. Lấy tuần đầu (a) hoặc trung bình (b) đều phóng đại; thí nghiệm không "hỏng" (c), chỉ cần chạy đủ lâu và đọc theo tuần (hoặc chỉ tính người dùng mới) |
| `relative-absolute` | b | 2.0% → 2.3% là +0.3 **điểm phần trăm**, +15% tương đối. Báo cả hai, kèm số đơn tăng thêm (chênh lệch × số người), vì số tuyệt đối mới đổi ra tiền. "Tăng 0.3%" (a) nhầm điểm % với %; "tăng 115%" (d) nhầm tỉ số với phần tăng |
| `post-hoc-segments` | c | Với 10 phân khúc ở alpha 0.05, xác suất có ít nhất một p < 0.05 do may là khoảng 40% (1 − 0.95¹⁰). Một phân khúc tìm ra sau khi xem dữ liệu chỉ là giả thuyết: kiểm bằng thí nghiệm mới, phân khúc khai báo trước (hoặc hiệu chỉnh nhiều kiểm định). Ship riêng (a) hay báo "chỉ hiệu quả với iOS" (b) là kết luận từ nhiễu |

## Chọn công cụ

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `tool-platform` | a | 40 thí nghiệm/tháng cần chia nhóm ổn định theo người dùng, log exposure, cảnh báo SRM, scorecard có guardrail: đó là việc của nền tảng experimentation (mua như Optimizely, Statsig, Eppo hoặc tự host như GrowthBook). DA vẫn cần notebook cho phân tích sâu, nhưng mỗi thí nghiệm một notebook (b) không mở rộng được và mỗi người tính một kiểu; Excel dùng chung (c) không tái lập; dashboard không kiểm định (d) dẫn tới đọc nhiễu thành kết quả |
| `tool-calculator` | d | Người nhận muốn tự đổi giả định: sheet (hoặc calculator như của Evan Miller) với ô baseline, MDE, alpha, power là đúng nhu cầu, miễn đã đối chiếu số với cách tính chuẩn của team (bài Basic 02). Code trong repo (a) người nhận không chạy được; một con số cố định (b) không trả lời được câu "nếu..."; tạo thí nghiệm nháp (c) là quá sớm |

## Ghi nhớ

Thứ tự đọc một readout: **độ tin cậy** (SRM, log đủ, thời lượng đủ chu kỳ tuần, không peeking) → **guardrail**
→ **hiệu ứng và khoảng tin cậy** (tuyệt đối, tương đối, quy ra số đơn/tiền) → **so với MDE** → quyết định. Phân
khúc và theo dõi theo thời gian dùng để hiểu và tạo giả thuyết, không để đổi quyết định sau khi đã thấy số.
