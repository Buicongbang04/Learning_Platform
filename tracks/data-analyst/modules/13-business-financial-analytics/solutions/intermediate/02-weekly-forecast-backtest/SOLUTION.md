# Lời giải: dự báo doanh số 8 tuần và backtest

## Cách làm

- **`comparable_stores`**: đếm số ngày khác nhau của mỗi cửa hàng, giữ cửa hàng có đủ `(max − min).days + 1` ngày.
  Ở Rossmann, ngày đóng cửa vẫn có dòng (`Open = 0`, `Sales = 0`), nên thiếu dòng nghĩa là thiếu dữ liệu, không phải
  đóng cửa. Tập cửa hàng được chọn **một lần trên toàn khoảng `train`** (kể cả các tuần nằm sau mỗi điểm cắt của
  backtest). Việc này không làm lộ doanh số tương lai cho phương pháp dự báo, vì tiêu chí chỉ là "có dòng mọi ngày",
  và nó chỉ loại các cửa hàng có dữ liệu bị gián đoạn (180 cửa hàng thiếu 7-12/2014, cửa hàng 988 thiếu một ngày).
  Nhưng cần nói rõ: trong vận hành thật, tập so sánh được phải chọn bằng thông tin có tại thời điểm dự báo (cửa hàng
  đang mở, không có lịch đóng cửa đã biết).
- **`weekly_sales`**: gán thứ Hai của tuần, `groupby` với tổng `Sales`, `max` của `Promo`, số ngày khác nhau; bỏ
  tuần dưới 7 ngày (tuần đầu 31/12/2012 và tuần cuối 27/07/2015 dở dang).
- **Ba phương pháp**: đều không cần fit. `seasonal_naive` dùng vị trí `len − m + (i % m)` để đúng pha cả khi
  `h > m`. `promo_average` dùng lịch khuyến mãi tương lai (biết trước) làm biến giải thích, không dùng doanh số
  tương lai.
- **`backtest`**: mỗi điểm cắt chỉ đưa lịch sử trước điểm cắt cho phương pháp; MAPE đo độ lớn sai số, bias đo
  hướng (dự báo cao hay thấp có hệ thống). Điểm cắt mỗi 4 tuần với horizon 8 tuần thì các cửa sổ chồng nhau: 6 điểm
  cắt không phải 6 phép đo độc lập.

## Kết quả trên bộ thật

- 934 cửa hàng đủ mọi ngày; 180 cửa hàng chỉ có 758 ngày (thiếu 01/07 tới 31/12/2014), cửa hàng 988 thiếu một ngày.
- Tổng mọi cửa hàng: trung bình tuần 6/2014 là 44.1 triệu, 7/2014 là 37.9 triệu (**−14.0%**); cửa hàng so sánh
  được: 37.3 → 37.9 triệu (**+1.5%**). Dùng tổng mọi cửa hàng thì seasonal naive cho nửa sau 2015 sẽ thấp hơn thật
  khoảng 14%, còn model có xu hướng sẽ "học" một cú sụt không có thật.
- 133 tuần, 71 tuần có khuyến mãi (trung bình 43.47 triệu) và 62 tuần không (31.92 triệu). Lịch khuyến mãi xen kẽ
  tuần, nhưng có 13 chỗ hai tuần liền cùng trạng thái (quanh lễ), nên tuần t − 52 chỉ cùng trạng thái khuyến mãi
  với tuần t ở 70% số tuần.

| Phương pháp | MAPE TB | MAPE tệ nhất | Bias TB |
| --- | --- | --- | --- |
| promo_average | 6.26% | 14.65% (2015-01-05) | +2.0% |
| seasonal_naive | 6.31% | 12.71% (2015-01-05) | −2.8% |
| ets (explore) | 10.3% | 16.3% (2015-03-30) | −4.5% |
| moving_average | 14.82% | 17.73% (2015-03-30) | +0.5% |

Điểm cắt 2015-03-02: lễ Phục sinh 2015 (05/04) sớm hơn 2014 (20/04) hai tuần, nên seasonal naive dự báo tuần
06/04/2015 là 33.2 triệu (thực tế 29.4, tuần có thứ Hai Phục sinh) và tuần 20/04 là 26.7 (thực tế 31.7).

**Câu cho FP&A**: "Doanh số tuần của 934 cửa hàng so sánh được dự báo khoảng 45 triệu cho tuần có khuyến mãi và 34
triệu cho tuần không có, 8 tuần từ 27/07/2015; sai số thường gặp khoảng ±6% (tới ±15% quanh lễ). Giả định: lịch
khuyến mãi tiếp tục xen kẽ; cửa hàng mở mới hoặc đóng cửa tính riêng." Promo average và seasonal naive ngang nhau
(chênh 0.05 điểm qua 6 điểm cắt chồng nhau là nhiễu); có thể chọn seasonal naive vì dễ giải thích, nhưng phải chỉnh
tay các tuần lễ di động (Phục sinh, Pentecost) và cân nhắc nhân tỉ lệ tăng trưởng gần đây để bỏ bias âm.

## Đáp án trắc nghiệm

- `all-stores-drop` **b**: 180 cửa hàng không có dữ liệu 7-12/2014; +1.5% là của chuỗi so sánh được.
- `comparable-count` **c**: 934. 1 115 là tổng số cửa hàng; 935 là nếu quên cửa hàng 988 thiếu một ngày.
- `promo-gap` **a**: 43.47 so với 31.92 triệu (+36%). Đây là chênh lệch giữa hai loại tuần, chưa phải tác động thật
  của khuyến mãi (xem bài Advanced 02).
- `best-method` **d**: 6.26% và 6.31%. Moving average 14.8%.
- `ets-result` **a**: khoảng 10.3%. ETS mùa vụ 52 tuần trên chỉ hơn hai năm dữ liệu phải ước lượng 52 hệ số mùa vụ
  từ hai quan sát mỗi tuần; phức tạp hơn không có nghĩa là tốt hơn, nên backtest so với baseline là bắt buộc.
- `hardest-cutoff` **b**: 2015-01-05, cửa sổ 8 tuần ngay sau lễ cuối năm (lịch khuyến mãi lệch quanh lễ, doanh số
  tháng 1 tụt). Moving average tệ nhất ở 2015-03-30.
- `ma-why` **c**: doanh số xen kẽ khoảng 32 và 43 triệu; trung bình 4 tuần ra khoảng 38 triệu cho mọi tuần, sai
  khoảng 15% ở cả tuần cao lẫn tuần thấp. Bias của nó gần 0 chính vì sai hai chiều triệt tiêu: bias nhỏ không có
  nghĩa là chính xác.
- `snaive-bias` **b**: chuỗi so sánh được tăng vài phần trăm mỗi năm; cùng tuần năm trước luôn hơi thấp. Cách DA:
  nhân thêm tỉ lệ tăng của 8 tuần gần nhất so với cùng kỳ (README phần 5), rồi backtest lại xem có thật tốt hơn.

## Lỗi hay gặp

- Dự báo trên tổng mọi cửa hàng mà không kiểm số cửa hàng có dữ liệu mỗi tuần.
- Giữ tuần dở dang ở đầu hoặc cuối chuỗi: tuần cuối có 5 ngày trông như cú rơi.
- Backtest một điểm cắt duy nhất rồi chọn phương pháp "thắng".
- Báo FP&A một con số không có khoảng và không có giả định về lịch khuyến mãi.
