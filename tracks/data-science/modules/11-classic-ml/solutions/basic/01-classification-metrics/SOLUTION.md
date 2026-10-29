# Lời giải: tự cài metric phân loại

## Cách làm

- **ROC-AUC bằng thứ hạng.** ROC-AUC là xác suất một ca dương có score cao hơn một ca âm. Nếu xếp hạng mọi
  score, tổng hạng của các ca dương trừ đi tổng hạng nhỏ nhất có thể ($$n_+(n_+ + 1)/2$$) đúng bằng số cặp
  (dương, âm) mà ca dương thắng, đó là thống kê U của Mann-Whitney. Hạng trung bình cho tie làm mỗi cặp hoà
  được tính 1/2. Độ phức tạp O(n log n) thay vì O(n₊ · n₋) khi so từng cặp.
- **Average precision.** Sắp score giảm dần, TP tích luỹ là `cumsum(y)`. Chỉ được "dừng" ở cuối mỗi nhóm score
  bằng nhau: một ngưỡng không thể lấy một nửa số ca có cùng score. Đây là chỗ cài ngây thơ (dừng ở mọi vị trí)
  lệch sklearn khi có tie, như output của cây quyết định.
- **Log loss** cần clip: một ca dương với p = 0 cho log(0) = −∞.

## Vì sao những tính chất trong test quan trọng

- ROC-AUC chỉ phụ thuộc thứ tự: nó không nói gì về xác suất có đúng hay không. Một model có xác suất bị bình
  phương (p⁴) có cùng ROC-AUC nhưng log loss khác hẳn. Khi xác suất được dùng trực tiếp, phải đo log loss,
  Brier, calibration.
- PR-AUC của score ngẫu nhiên bằng tỉ lệ dương (10% trong test), không phải 0.5. Báo cáo "PR-AUC 0.34" phải
  kèm tỉ lệ dương (10.4% trên test Olist) mới có nghĩa.

## Sai lầm hay gặp

- Tính AP bằng hình thang (`np.trapz` trên đường PR): cho số khác, lạc quan hơn, vì nội suy tuyến tính giữa
  các điểm PR không đạt được bằng ngưỡng nào.
- So từng cặp bằng hai vòng lặp: đúng nhưng O(n²), không chạy nổi trên 100 nghìn dòng.
- Precision không xác định khi không dự đoán dương ca nào: sklearn mặc định trả 0 kèm cảnh báo; nói rõ quy ước.
