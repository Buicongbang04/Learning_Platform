# Hướng làm: ML hay bảng trung bình cho dự báo nhu cầu theo giờ

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết ba hàm, các con số tham chiếu, các quyết định cần cân
nhắc và rubric chấm memo.

## Ba hàm

- **`time_split`**: so `dteday` với `pd.Timestamp(cutoff)`, giữ index gốc, `ValueError` khi một phần rỗng. Chia theo thời
  gian vì dự báo luôn dùng quá khứ đoán tương lai; chia ngẫu nhiên giờ sẽ cho model "nhìn" giờ trước và sau của cùng ngày.
- **`profile_baseline`**: chọn phần train (toàn bộ hoặc `dteday > max − weeks tuần`), `groupby(["workingday", "hr"]).cnt.mean()`,
  tra cho từng dòng test bằng `reindex` trên `MultiIndex`, cặp thiếu điền mean của phần train đã chọn.
- **`mae`**: `np.asarray(..., float)`, kiểm cùng `shape`, không rỗng, không NaN; `float(np.mean(np.abs(a - b)))`.

## Con số tham chiếu (test 01/10–31/12/2012, 2 168 giờ, trung bình 219.2 lượt/giờ)

| Cách dự báo | MAE (lượt/giờ) | So với baseline đang dùng |
| --- | --- | --- |
| Bảng trung bình (ngày làm việc, giờ), toàn bộ train | 79.95 | mốc |
| Bảng trung bình, 8 tuần cuối (06/08–30/09/2012) | 94.13 | tệ hơn 18% |
| Gradient boosting, chỉ lịch | 87.51 | tệ hơn 9% |
| Gradient boosting, lịch + thời tiết **đo thực tế** | 44.34 | tốt hơn 45% |
| Gradient boosting, lịch + thời tiết cùng giờ hôm trước | 71.09 | tốt hơn 11% |

- Baseline theo tháng: tháng 10 thực tế 280.8 lượt/giờ, dự báo 185.2, MAE 111.2; tháng 11 MAE 59.3; tháng 12 MAE 70.1. Bảng
  trộn năm 2011 (nhu cầu thấp hơn) nên lệch thấp khi 2012 đã tăng; tới tháng 12 lại lệch cao vì nhu cầu mùa đông giảm.
- Baseline 8 tuần cuối tệ hơn vì 8 tuần đó là cuối hè, nhu cầu cao, áp lên quý 4 lạnh dần: "gần đây hơn" không tự động tốt
  hơn khi có mùa vụ.
- Model chỉ dùng lịch không hơn baseline: cây không ngoại suy được xu hướng tăng theo năm (`yr` chỉ có 0 và 1 trong train).
- Độ phủ: 2012-10-29 chỉ còn 1 giờ, 2012-10-30 còn 11 giờ (bão Sandy đóng hệ thống). Không có dòng thì không có sai số để
  đo, nhưng trong vận hành thật đó là ngày dự báo sai nặng nhất.
- Thời tiết dịch 24 giờ để thiếu 28 dòng test (giờ trước đó bị thiếu); gradient boosting của sklearn tự xử lý NaN.

**Câu chuyện mẫu**: "giảm một nửa" là thật nhưng chỉ khi biết trước thời tiết thật. Với dự báo ngây thơ còn khoảng 11%. Giá
trị thật nằm giữa, phụ thuộc chất lượng dự báo thời tiết; đo bằng cách chạy song song vài tuần với dự báo thật.

## Các quyết định cần cân nhắc

- **Dữ liệu có sẵn lúc dự báo** là điểm chính của bài. Thời tiết đo thực tế là leakage theo thời điểm: hợp lệ để giải thích
  nhu cầu, không hợp lệ để đánh giá một dự báo ngày mai. Bài làm tốt nêu điều này và ước lượng bằng một proxy (dịch 24 giờ,
  hoặc thêm nhiễu có kiểm soát và ghi rõ là mô phỏng).
- **Cải tiến baseline trước khi mua**: bảng chỉ dùng năm gần nhất, nhân hệ số tăng trưởng, thêm điều chỉnh theo
  `weathersit` (một bảng nhỏ "ngày mưa giảm x%") thường lấy được một phần lợi ích của model mà không cần vận hành ML.
- **Metric theo vận hành**: MAE trung bình cả ngày che sai số ở giờ cao điểm (7–9 giờ, 16–19 giờ ngày làm việc), nơi thiếu xe
  tốn nhất. Có thể đề xuất MAE giờ cao điểm hoặc sai số theo trạm (dữ liệu này không có trạm: nêu là giới hạn).
- **Một quý kiểm tra**: một mốc chia duy nhất là ít; backtest nhiều mốc (cuối mỗi tháng của 2012) cho khoảng sai số đáng tin
  hơn.
- **Chi phí vận hành**: nguồn dự báo thời tiết, chạy hằng ngày, theo dõi khi model hỏng, phụ thuộc vendor.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm và số đúng | 10 | Test pass; số trong memo khớp notebook |
| So sánh công bằng | 15 | Cùng tập test chia theo thời gian; có baseline đang dùng, model chỉ lịch và model có thời tiết; quy về % so với baseline hoặc mức trung bình |
| Dữ liệu có sẵn lúc dự báo | 25 | Chỉ ra thời tiết đo thực tế không có lúc lên lịch; ước lượng lại bằng proxy hợp lý và nói rõ đó là cận dưới hay mô phỏng |
| Sai số ở đâu | 15 | Phân tích ít nhất hai chiều (tháng, giờ cao điểm, thời tiết); nhắc ngày thiếu dữ liệu và xu hướng theo năm |
| Cải tiến baseline | 10 | Ít nhất một cải tiến rẻ được thử hoặc đề xuất có lý do |
| Khuyến nghị | 15 | Quyết định rõ (mua, không mua, chạy song song) kèm tiêu chí đo được và thời hạn |
| Viết cho Ops | 10 | Headline có con số; không thuật ngữ không giải thích; nói sai số bằng lượt/giờ |

Từ 70 điểm trở lên là memo có thể gửi Operations Manager.

## Sai lầm hay gặp

- Chia train/test ngẫu nhiên theo giờ: model "đoán" giờ 9 khi đã thấy giờ 8 và 10 của cùng ngày, MAE đẹp giả.
- Báo "model giảm sai số 45%" mà không nói nó dùng thời tiết đo sau khi sự việc xảy ra.
- Dịch thời tiết 24 dòng thay vì 24 giờ: các giờ bị thiếu làm lệch thời điểm.
- So model với một baseline yếu do chính mình chọn (ví dụ 8 tuần cuối) để làm model trông tốt hơn.
- Bỏ qua 29–30/10/2012 hoặc diễn giải sai số thấp của những ngày đó là "model dự báo tốt".
