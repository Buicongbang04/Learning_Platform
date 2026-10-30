# Lời giải: có ý nghĩa thống kê chưa phải là đáng kể

## Cách làm

1. **`to_business_units`**: `day.assign(temp_c=temp * 41, hum_pct=hum * 100, wind_kmh=windspeed * 67)`.
   `assign` trả bản sao, không sửa đầu vào. Báo cáo cho vận hành bằng °C, %, km/h chứ không bằng giá trị chuẩn
   hoá 0-1.
2. **`corr_with_ci`**: bỏ cặp thiếu, r Pearson, khoảng tin cậy bằng Fisher z (r không có phân phối chuẩn khi gần
   ±1, còn artanh(r) thì xấp xỉ chuẩn với sai số chuẩn 1/√(n−3)), p từ thống kê t bậc tự do n−2. Kết quả trùng
   `scipy.stats.pearsonr(...).confidence_interval()`.
3. **`welch_compare`**: Welch t-test không giả định hai nhóm cùng phương sai. Ở đây 21 ngày lễ và 500 ngày làm
   việc có độ phân tán rất khác nhau, nên t-test phương sai gộp sẽ cho p sai. Mặc định nên dùng Welch.
4. **`matched_holiday_gap`**: mốc của mỗi ngày lễ là trung bình ngày làm việc **cùng năm, cùng tháng**. Đây là
   cách khử nhiễu mùa vụ đơn giản nhất, cùng ý tưởng với "so cùng kỳ" của module 08 và với biến kiểm soát trong
   regression (Intermediate 02).

## Số liệu trên bộ thật

| Biến | r | Khoảng tin cậy 95% | p | r² |
| --- | --- | --- | --- | --- |
| Nhiệt độ (°C) | 0.627 | [0.581; 0.670] | 2.8e-81 | 39.4% |
| Độ ẩm (%) | −0.101 | [−0.172; −0.028] | 0.0065 | **1.0%** |
| Gió (km/h) | −0.235 | [−0.302; −0.165] | 1.4e-10 | 5.5% |

Ngày lễ (21 ngày, 15 ngày là thứ Hai) so với ngày làm việc:

| Chỉ số | So thẳng: chênh lệch [CI 95%], p | So cùng năm-tháng: chênh lệch TB [CI 95%], p |
| --- | --- | --- |
| `cnt` | −850 [−1 819; +120], p = 0.083 | −595 [−1 168; −21], p = 0.043; 16/21 ngày thấp hơn |
| `casual` | +458 [+65; +851], p = 0.024 | +562 [+278; +845], p = 0.0005; **21/21** ngày cao hơn |
| `registered` | −1 308 [−1 999; −617], p = 0.0007 | −1 156 [−1 641; −672], p = 0.00007; 18/21 ngày thấp hơn |

Ngày lễ rơi nhiều vào tháng lạnh (tháng 1, 2, 11, 12 có 11/21 ngày), nên so thẳng với mọi ngày làm việc trộn
hiệu ứng "ngày lễ" với hiệu ứng "mùa đông": phương sai lớn, khoảng tin cậy rộng. So cùng tháng loại phần mùa vụ,
khoảng tin cậy hẹp lại và kết luận rõ hơn. Ngày lễ giảm nhiều nhất: Giáng sinh 2012 (−3 414), Lễ Tạ ơn 2012
(−2 842), 2011 (−1 936); tăng nhiều nhất: 4/7/2011 (+1 622).

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `humidity-r2` | a. Khoảng 1% | r² = 0.101² = 0.010. 39% là của nhiệt độ |
| `significance-meaning` | c | Với 731 ngày, một quan hệ rất yếu vẫn đủ để p nhỏ. p không đo độ lớn, cũng không nói nhân quả; quyết định điều xe cần độ lớn (và thường là regression có kiểm soát nhiệt độ, mùa) |
| `temp-ci` | b. [0.58; 0.67] | [0.03; 0.17] gần với khoảng của độ ẩm (đổi dấu), [0.16; 0.30] với gió |
| `holiday-raw` | a. −850, p ≈ 0.08 | −595 là so cùng tháng; +458 là `casual`; −1 308 là `registered` |
| `why-matched` | d | Ghép theo tháng bỏ phần biến động do mùa khỏi phép so, nên sai số nhỏ hơn. Số ngày lễ vẫn là 21; ghép cặp không "luôn" cho p nhỏ hơn |
| `casual-holidays` | a. 21 ngày | Mọi ngày lễ đều có `casual` cao hơn ngày làm việc cùng tháng; 16 là số ngày lễ có `cnt` thấp hơn |
| `marketing-answer` | b | Tổng lượt giảm che hai chiều ngược nhau: thành viên (đi làm) giảm khoảng 1 160, vãng lai (đi chơi) tăng khoảng 560 mỗi ngày lễ. Khuyến mãi ngày lễ nên nhắm khách vãng lai; p = 0.08 của tổng không có nghĩa "không ảnh hưởng" |
| `multiple-tests` | c | Với 6 kiểm định độc lập ở alpha 0.05, xác suất có ít nhất một p < 0.05 do ngẫu nhiên là khoảng 26%. Bonferroni (nhân p với 6) là một cách hiệu chỉnh, nhưng 0.24 không có nghĩa "ảnh hưởng thật nhưng nhỏ" |

## Trả lời mẫu

- **Trưởng vận hành**: "Độ ẩm có liên quan nhưng rất yếu: một mình nó giải thích khoảng 1% chênh lệch lượt thuê
  giữa các ngày. Nhiệt độ (39%) và gió (5.5%) quan trọng hơn nhiều. Chưa nên điều xe theo độ ẩm; bài regression sẽ
  ước lượng ảnh hưởng của từng yếu tố khi giữ các yếu tố khác cố định."
- **Trưởng marketing**: "Ngày lễ không làm giảm khách đều: thành viên giảm khoảng 1 160 lượt/ngày, khách vãng lai
  tăng khoảng 560 so với ngày làm việc cùng tháng, ngày lễ nào cũng vậy. Khuyến mãi ngày lễ nên nhắm khách vãng
  lai. Mẫu chỉ có 21 ngày lễ nên con số cụ thể còn rộng (vãng lai +280 tới +850)."
