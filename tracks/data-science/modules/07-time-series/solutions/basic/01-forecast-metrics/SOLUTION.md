# Lời giải: metric dự báo

## Mỗi metric phạt điều gì

| Metric | Phạt | Hỏng khi | Dùng khi |
| --- | --- | --- | --- |
| MAE | Sai số tuyệt đối, tuyến tính | So nhiều chuỗi khác đơn vị/quy mô | Một chuỗi, cần con số dễ giải thích ("lệch trung bình 40 đơn/ngày") |
| RMSE | Sai số lớn bị phạt nặng (bình phương) | Có ngày bất thường (Black Friday) chi phối cả metric | Sai số lớn thật sự đắt (thiếu kho trầm trọng) |
| MAPE | Sai số tương đối | Có giá trị 0 hoặc gần 0 (chia cho 0, phình vô hạn); bất đối xứng | Báo cáo kinh doanh, chuỗi luôn dương và xa 0 |
| sMAPE | Sai số tương đối "đối xứng" | Cả hai gần 0; thực ra vẫn bất đối xứng theo hướng khác | Khi buộc phải so với kết quả các cuộc thi M3 |
| MASE | Sai số so với seasonal naive in-sample | Chuỗi hằng (mẫu số 0) | **Mặc định** khi so model trên nhiều chuỗi |

MAE được tối ưu bởi **median** của phân phối dự báo, RMSE bởi **mean**. Model tối ưu RMSE trên doanh
thu lệch phải sẽ dự báo cao hơn model tối ưu MAE; chọn metric là chọn đại lượng bạn muốn dự báo.

## Vì sao MAPE bất đối xứng

Với y = 100: dự báo 50 cho MAPE 50%, dự báo 150 cũng 50%. Nhưng với y = 50 và dự báo 100 thì MAPE là
100%. Dự báo thấp bị chặn ở 100% (không thể dự báo âm), dự báo cao không có trần, nên model tối ưu
MAPE có xu hướng **dự báo thấp**. Với kế hoạch tồn kho, đó là lỗi có hệ thống.

## MASE

Mẫu số là MAE in-sample của seasonal naive bậc m trên tập train. Hệ quả:

- MASE < 1: tốt hơn seasonal naive *một bước* trong lịch sử. MASE > 1 không có nghĩa model thua
  seasonal naive trên tập test, vì dự báo nhiều bước khó hơn một bước. Muốn biết model có thắng
  baseline không thì chạy baseline trong cùng backtest (bài Intermediate 02).
- Không phụ thuộc đơn vị: so được cửa hàng 1 000 €/ngày với cửa hàng 20 000 €/ngày.
- Không chia cho từng y, nên dùng được khi có ngày bằng 0 (Chủ nhật đóng cửa).

Test `test_in_sample_seasonal_naive_has_mase_one` là định nghĩa của MASE nhìn từ phía ngược lại.

## Sai lầm hay gặp

- Trừ hai `pd.Series` có index khác nhau: pandas căn theo index, ra NaN. Chuyển về numpy trước.
- Tính mẫu số MASE trên tập test thay vì train: đó là dùng thông tin tương lai, và con số không còn so
  được giữa các origin.
- Báo cáo MAPE trung bình qua nhiều chuỗi khi một chuỗi có giá trị nhỏ: một chuỗi chi phối cả trung
  bình. Dùng WAPE (tổng |sai số| / tổng y) nếu cần con số phần trăm.
