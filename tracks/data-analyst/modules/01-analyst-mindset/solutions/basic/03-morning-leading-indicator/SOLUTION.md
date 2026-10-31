# Lời giải: lượt thuê trước 10h làm chỉ số dẫn trước

## Cách làm

1. **`daily_signal`**: đổi `dteday` sang ngày; `hour["cnt"].where(hour["hr"] < cutoff, 0)` giữ lượt của giờ buổi
   sáng, đặt 0 cho giờ còn lại, rồi `groupby(ngày).sum()`. Cách này tự cho `morning = 0` với ngày không có giờ
   buổi sáng nào (lọc dòng trước rồi nhóm thì những ngày đó biến mất, phải `reindex`). `workingday` lấy
   `first()` theo ngày.
2. **`morning_share`**: tổng `morning` chia tổng `total` theo `workingday`. Tỉ lệ của tổng là đúng cho dự báo vì
   nó là tỉ lệ của toàn bộ lượt thuê; trung bình các tỉ lệ từng ngày cho ngày vắng trọng số bằng ngày đông.
3. **`nowcast`**: `daily["morning"] / daily["workingday"].map(share)`.
4. **`median_ape`**: bỏ ngày `actual == 0`, lấy trung vị của `|forecast - actual| / actual`.

## Vì sao như vậy

- **Leading indicator phải được kiểm**, không được giả định. Tương quan buổi sáng–cả ngày gộp mọi ngày là 0.788;
  tách loại ngày là 0.943 (ngày làm việc) và 0.889 (cuối tuần/lễ). Hai loại ngày có **hình dạng** khác nhau:
  trước 10h chiếm 26.14% lượt ngày làm việc (người đi làm lúc 8h) nhưng chỉ 13.70% lượt cuối tuần (đi chơi
  buổi trưa). Gộp hai đám mây điểm nằm trên hai đường dốc khác nhau làm tương quan giảm.
- **Dùng tỉ lệ đúng phân khúc**: sai số trung vị 8.86% khi tách loại ngày, 25.04% khi dùng một tỉ lệ chung
  22.36%. Với tỉ lệ chung, ngày cuối tuần bị dự báo **thấp** hơn thực tế (sai lệch trung vị −40%, 96% ngày cuối
  tuần bị dự báo thấp), ngày làm việc bị dự báo cao (+17%): một chỉ số "trung bình đúng" nhưng sai có hệ thống
  ở từng nhóm.
- **Kiểm ngoài mẫu**: tỉ lệ ước từ 2011 (13.45%, 26.02%) dự báo 2012 với sai số trung vị 8.00%. Tỉ lệ ổn định
  giữa hai năm dù lượt thuê tăng 65%: chỉ số dùng được cho năm sau mà không phải ước lại liên tục.
- **Ngày chỉ số không thấy trước**: 27/08/2011 (bão Irene: buổi sáng 610 lượt, 10h–17h chỉ thêm 505 và không có
  dòng nào từ 18h, dự báo 4 453, thực tế 1 115) và 22/04/2012 (mưa cả ngày, cuối tuần). Sự kiện xảy ra **sau**
  10h thì tín hiệu trước 10h không thể biết. Cần thêm tín hiệu khác: dự báo thời tiết buổi chiều.
- **Ngày sai do dữ liệu, không do chỉ số**: 29/10/2012 (bão Sandy) đứng thứ hai về sai số (283%), nhưng `hour.csv`
  chỉ có **một dòng** cho ngày này (giờ 0, 22 lượt): hệ thống chỉ ghi giờ 0, các giờ còn lại thiếu. "Buổi sáng"
  và "cả ngày" đều là 22, dự báo 22 / 0.2614 ≈ 84. Ngày 30/10/2012 chỉ có các giờ 13–23 (một trong 3 ngày
  `morning = 0`). Bài học: **kiểm độ phủ giờ trước khi tin vào sai số**. Bộ dữ liệu có 76 ngày thiếu ít nhất một
  giờ, 3 ngày có dưới 12 giờ; một bảng "số giờ có dữ liệu mỗi ngày" cạnh bảng sai số giúp tách lỗi chỉ số khỏi
  lỗi ghi nhận.
- **Đánh đổi sớm và chính xác**: trước 8h sai số 11.5%, trước 10h 8.9%, trước 12h 6.8%. Chọn mốc là quyết định
  của đội vận hành (xe tải cần bao lâu để điều xe), không phải của DA; DA đưa bảng đánh đổi.
- **Trung vị** vì phân phối sai số lệch: 79.8% ngày sai trong ±20%, nhưng đuôi dài kéo trung bình lên 14.9%.
  Chỉ 3 ngày sai trên 200%: 27/08/2011 (bão Irene, 299%), 29/10/2012 (283%, lỗi dữ liệu: chỉ có giờ 0) và
  22/04/2012 (mưa cả ngày, 231%); 5 ngày sai trên 100%, 35 ngày trên 50%.

Câu trả lời cho trưởng ca: "Lúc 10h, lấy lượt thuê từ đầu ngày chia 0.26 (ngày làm việc) hoặc 0.14 (cuối
tuần) là ra tổng cả ngày, sai khoảng 9% trong ngày điển hình. Không dùng được ngày có bão hay mưa lớn buổi
chiều: những ngày đó xem dự báo thời tiết."

## Con số tham chiếu

| Đại lượng | Giá trị |
| --- | --- |
| Ngày, tổng lượt | 731 ngày, 3 292 679 lượt |
| Ngày có `morning = 0` | 3 (thiếu dữ liệu giờ buổi sáng) |
| Tỉ lệ trước 10h: cuối tuần/lễ, ngày làm việc, chung | 13.70%, 26.14%, 22.36% |
| Tương quan gộp; ngày làm việc; cuối tuần | 0.788; 0.943; 0.889 |
| Sai số trung vị: theo loại ngày / tỉ lệ chung | 8.86% / 25.04% |
| Ngoài mẫu (tỉ lệ 2011 → 2012) | 8.00% |
| Cutoff 8h / 10h / 12h | 11.5% / 8.9% / 6.8% |
| Ngày sai trong ±20% | 79.8% |

## Đáp án trắc nghiệm

- `lagging-kpi` (b) **tổng lượt cả ngày**: kết quả đo sau khi ngày kết thúc. (a) là leading indicator; (c) là
  tín hiệu bổ sung; (d) là tham số của dự báo.
- `workday-share` (c) **khoảng 26%** (26.14%). 14% là cuối tuần, 22% là tỉ lệ chung.
- `segmented-vs-pooled` (a) **9% so với 25%**. 11% (b) là sai số khi cutoff 8h, 15% (c) là sai số trung **bình**.
- `pooled-weekend` (c) **thấp hơn thực tế**: sáng cuối tuần chỉ chiếm 13.7% lượt cả ngày, chia cho 22% thì ra
  tổng quá nhỏ. (a) và (d) sai hướng; (b) bỏ qua sai lệch có hệ thống.
- `worst-day` (c) **27/08/2011, bão Irene**: dự báo 4 453, thực tế 1 115 (sai 299%). 29/10/2012 (a) đứng thứ hai
  (283%), nhưng sai số đó do dữ liệu chỉ có giờ 0 (xem trên); 25/12/2012 (b) không nằm trong top 5.
- `storm-signal` (b): thêm tín hiệu thấy được chuyện xảy ra sau 10h. Bỏ chỉ số (a) là bỏ thứ đúng 80% số ngày;
  (c) chỉ đổi cách đo; dời sang 8h (d) làm sai số tăng và vẫn không thấy bão buổi chiều.
- `cutoff-tradeoff` (a): **khoảng 7%** (6.8%), đổi lại biết muộn hai giờ.
- `median-not-mean` (c): vài ngày sai hàng trăm phần trăm kéo trung bình. (b) sai vì hàm đã bỏ ngày tổng bằng 0
  (và bộ thật không có ngày nào tổng bằng 0).
