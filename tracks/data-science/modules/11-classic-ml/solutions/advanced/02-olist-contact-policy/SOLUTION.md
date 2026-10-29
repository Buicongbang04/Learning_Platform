# Hướng làm: chính sách liên hệ chủ động trên Olist

Bài Advanced không có một đáp án duy nhất. Dưới đây là một lời giải tham chiếu, các quyết định cần cân nhắc,
và rubric.

## Ma trận chi phí

Với thiệt hại L = 30, chi phí gọi c = 5, xác suất cứu được s:

$$
C_{TP} = c + (1 - s)L, \quad C_{FP} = c, \quad C_{FN} = L, \quad C_{TN} = 0,
\qquad t^* = \frac{c}{sL}
$$

Công thức chỉ có nghĩa khi $$sL > c$$; nếu không thì không gọi ai. s = 0.5 cho $$t^* = 1/3$$; s = 0.3 cho $$t^* = 5/9 \approx 0.556$$. Gọi chỉ đáng khi xác suất review xấu đủ
cao để phần thiệt hại kỳ vọng tránh được ($$p\,s\,L$$) lớn hơn chi phí gọi.

## Kết quả tham chiếu

Random forest (300 cây), `min_samples_leaf` chọn trên validation theo PR-AUC trong {5, 20, 50, 100}: chọn 50
(validation PR-AUC 0.614, ROC-AUC 0.810). Test: ROC-AUC 0.689, PR-AUC 0.339, Brier 0.0806. Xác suất trung bình
trên test 0.110 so với tỉ lệ thật 0.104: gần calibrated; isotonic fit trên validation không cải thiện (Brier
0.0810) vì tỉ lệ nền ở validation (18%) cao hơn test.

Tập test: 31 994 đơn trong 21.4 tuần, khoảng 1 493 đơn mỗi tuần; 100 cuộc gọi mỗi tuần là 6.7%.

| s | Năng lực | Ngưỡng (chọn trên val) | Tỉ lệ gọi ở test | Cuộc gọi/tuần | Tiết kiệm/đơn (R$), CI 95% | Tổng trên test (R$) |
| --- | --- | --- | --- | --- | --- | --- |
| 0.5 | không giới hạn | 0.262 | 5.9% | 88 | 0.158 [0.135, 0.180] | 5 050 |
| 0.5 | 6.7% | 0.674 | 1.2% | 18 | 0.070 [0.059, 0.081] | 2 225 |
| 0.3 | không giới hạn | 0.393 | 4.0% | 60 | 0.012 [0.002, 0.022] | 379 |
| 0.3 | 6.7% | 0.676 | 1.2% | 18 | 0.017 [0.012, 0.023] | 551 |

Đọc bảng:

- **Kết luận phụ thuộc hoàn toàn vào s.** Với s = 0.5 chương trình có lãi rõ; với s = 0.3 tiết kiệm gần 0 (CI
  gần chạm 0). s là con số chưa ai đo: phải đo bằng thí nghiệm trước khi mở rộng.
- **Ngưỡng cố định chuyển kém qua drift.** Ràng buộc 6.7% được thoả ở validation (nhiều đơn rủi ro) bằng
  ngưỡng 0.67, nhưng ở test ngưỡng đó chỉ dùng 1.2% năng lực (18 cuộc gọi mỗi tuần thay vì 100). Chính sách tốt
  hơn khi năng lực cố định: **mỗi tuần gọi top 100 đơn có điểm cao nhất**, miễn điểm vẫn trên ngưỡng hoà vốn
  $$t^*$$.
- Ở s = 0.5, ngưỡng không giới hạn chỉ cần 88 cuộc gọi mỗi tuần trên test: năng lực 100 gần như không ràng
  buộc trong giai đoạn này, nhưng sẽ ràng buộc trong mùa nhiều đơn trễ (như Q1/2018).

## Các quyết định cần cân nhắc

1. **Thời điểm dự đoán**: lúc đơn vừa giao như module 10 (dùng được `late_days`, mọi cột review là leakage) hay sớm hơn: lúc mua / lúc giao cho hãng vận chuyển là một bài toán khác, phải bỏ mọi kết quả giao hàng (can thiệp trước khi khách bực, nhưng
   mất feature mạnh nhất). Một phần review được viết trước khi giao; nêu rõ phạm vi.
2. **Calibration**: công thức $$t^*$$ cần xác suất đúng. Kiểm tra trên test; calibrate trên dữ liệu gần nhất.
3. **Ngưỡng cố định hay top-N theo tuần**, như trên.
4. **Độ không chắc chắn**: CI bootstrap chỉ phản ánh nhiễu lấy mẫu; độ không chắc của giả định (s, L) lớn hơn
   nhiều, xử lý bằng phân tích độ nhạy.
5. **Feedback loop**: sau khi triển khai, đơn được gọi có nhãn bị can thiệp; train lại ngây thơ sẽ học rằng
   đơn rủi ro cao "ít bị review xấu". Giữ một nhóm holdout không bị gọi (random) để vừa đo tác động vừa có
   nhãn sạch.
6. **Thí nghiệm**: random trong nhóm điểm cao: gọi / không gọi. Đo review xấu, tỉ lệ có review (guardrail:
   cuộc gọi có thể làm khách không review thay vì review tốt), mua lại trong 90 ngày (module 03).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm chấm điểm | 10 | Test pass |
| Giả định chi phí | 15 | Ma trận chi phí suy ra từ giả định rõ ràng, có ngưỡng hoà vốn |
| Model và đánh giá | 15 | Chia theo thời gian, chọn trên validation, chấm test một lần, có baseline |
| Calibration | 10 | Kiểm tra trên test, quyết định có/không recalibrate có lý do |
| Năng lực và drift | 20 | Nhận ra ngưỡng cố định chuyển kém giữa các giai đoạn; đề xuất top-N hoặc tương đương |
| Độ không chắc chắn và độ nhạy | 15 | CI bootstrap + kết luận theo s, L; nói rõ cái nào là nhiễu, cái nào là giả định |
| Triển khai | 15 | Thí nghiệm để đo s, holdout chống feedback loop, theo dõi drift |

Từ 70 điểm: đủ để đưa vào review với quản lý vận hành.
