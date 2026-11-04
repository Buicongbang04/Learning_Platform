# Lời giải: burn rate cho SLO chất lượng và freshness

`ml_slo.rules.yml` cạnh tệp này là bản mẫu đã qua test.

## Ý chính

- **Cửa sổ theo nhịp của SLI.** Nhãn ETA về theo lô (ở đây mỗi 5 phút, ngoài đời có khi mỗi giờ hay mỗi ngày). Cửa sổ `5m` trên
  một SLI cập nhật mỗi 5 phút chứa một hai mẫu, `rate` nhảy loạn. Vì vậy tầng nhanh nhất cho chất lượng là `6h/30m` (burn 6, tiêu
  5% budget trong 6 giờ), tầng chậm là `1d/2h` (burn 3, tiêu 10% budget trong một ngày). Tỉ lệ cửa sổ ngắn bằng 1/12 cửa sổ dài
  giữ nguyên như module 09. Freshness đo được mỗi phút nên dùng được tầng `1h/5m` như khả dụng.
- **Hai cửa sổ để tự tắt.** Sau 12 giờ 20% tệ rồi về 0%: ở giờ 13 cửa sổ 6h vẫn còn khoảng 16.7% tệ (trên ngưỡng 12%), chỉ cửa
  sổ 30m sạch. Bỏ `and` thì alert kêu thêm năm tiếng sau khi đã hết sự cố.
- **Freshness là SLI theo thời gian.** "Tuổi feature" không có mẫu số là số request. Mỗi phút là một sự kiện: tươi hay cũ.
  `(time() - gauge) > bool 900` ghi thành recording rule `eta:feature_stale` rồi `avg_over_time` cho tỉ lệ thời gian cũ. Một lần
  chậm 18 phút chỉ cũ quá ngưỡng 2 phút, tỉ lệ 1h là 3%, không đáng đánh thức ai; ngừng 40 phút thì có.
- **"Không đo được" khác "đạt".** Khi nhãn ngừng về, tỉ lệ chất lượng là `NaN` (0/0), alert burn rate im lặng, dashboard vẫn xanh.
  `ETAQualityLabelsMissing` phụ trách mode hỏng này. `or vector(0)` cần cho trường hợp series biến mất hẳn (job join chết, target
  bị gỡ): `sum` của vector rỗng là rỗng chứ không phải 0.
- **Lọc đúng series.** `feature_view="trip_stats"` và `job` trong mọi selector; view khác cũ không thuộc SLO này.

## Lỗi hay gặp

- Chép nguyên tầng `1h/5m` của khả dụng cho chất lượng: với nhãn theo lô, `5m` có lúc không có mẫu (tỉ lệ rỗng), có lúc nhảy 0 sang 100%.
- Chia recording rule và alert vào hai group rồi đánh giá với `evaluation_interval` bằng chu kỳ cập nhật của dữ liệu: thứ tự giữa
  các group không đảm bảo, alert có thể đọc mẫu của vòng trước nằm đúng mép cửa sổ lookback và thấy rỗng. Đánh giá thường xuyên
  hơn chu kỳ dữ liệu, hoặc để alert phụ thuộc recording rule chung group.
- `absent(eta_quality_checks_total)` thay cho `increase(...) == 0`: không bắt được counter vẫn còn nhưng đứng yên.
- Quên `bool`: `(time() - gauge) > 900` lọc bỏ series khi tươi thay vì trả 0, `avg_over_time` khi đó chỉ tính các phút cũ và ra 1.
