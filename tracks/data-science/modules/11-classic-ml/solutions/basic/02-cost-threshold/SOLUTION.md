# Lời giải: chọn ngưỡng theo ma trận chi phí

## Cách làm

Dự đoán dương khi chi phí kỳ vọng của hành động không lớn hơn của không hành động:

$$
p\,C_{TP} + (1 - p)\,C_{FP} \le p\,C_{FN} + (1 - p)\,C_{TN}
\iff
p \ge t^* = \frac{C_{FP} - C_{TN}}{(C_{FP} - C_{TN}) + (C_{FN} - C_{TP})}
$$

Với Olist: $$t^* = 5/35 \approx 0.143$$. Nếu liên hệ một đơn có vấn đề cũng tốn 5 R$ (TP = 5), lợi ích ròng của
một lần bắt đúng giảm còn 25, nên $$t^* = 5/30$$. Khi mẫu số âm hoặc $$t^* > 1$$, không có p nào đáng hành động.

`best_threshold` trong lời giải là bản vector hoá: sắp p giảm dần, TP và FP khi lấy mọi ca có `p >= ` giá trị
thứ k là `cumsum`, chỉ đánh giá tại cuối mỗi nhóm p bằng nhau. O(n log n), chạy tức thì trên vài trăm nghìn đơn.

## Kết quả trên Olist thật

Random forest của bài Intermediate 01, ngưỡng chọn trên validation rồi chấm trên test:

| Ngưỡng | Chi phí mỗi đơn (R$) | Tỉ lệ liên hệ |
| --- | --- | --- |
| Không liên hệ ai | 3.114 | 0% |
| 0.5 | 2.627 | 2.8% |
| 5/35 = 0.143 | 2.279 | 15.2% |
| Chọn trên validation (0.175) | 2.263 | 10.7% |

Ngưỡng chọn trên validation gần ngưỡng lý thuyết vì random forest gần calibrated. Khi model không calibrated
(class_weight, SVM), hai con số tách xa nhau, và ngưỡng quét trên validation là cái đáng tin.

## Sai lầm hay gặp

- Chọn ngưỡng trên test: con số báo cáo lạc quan.
- Tối ưu F1 hay accuracy khi đã biết chi phí: F1 ngầm định một tỉ lệ đánh đổi khác.
- Quên ứng viên "không liên hệ ai": có những bài mà không hành động là tối ưu.
- Coi chi phí là hằng số đúng: 30 R$ cho một review xấu là giả định. Báo cáo kèm độ nhạy.
