# Postmortem: ETA sai lệch khi NYC phong toả vì COVID (2020-03 tới 2020-05)

Bản postmortem không đổ lỗi, dựng lại từ phát lại 2019-07..2020-06 trên dữ liệu TLC thật (mẫu 50 000 chuyến mỗi tháng,
model champion train trên 2019-06). Số liệu lấy từ `reports/replay/summary.parquet`.

## Tóm tắt

Từ giữa tháng 3/2020 lưu lượng taxi NYC sụp, đường vắng và thời gian chuyến đi ngắn lại so với cùng quãng đường. Model
ETA train trên 2019-06 tiếp tục dự đoán theo nhịp giao thông cũ nên đánh giá quá cao thời gian: MAE từ 181 s (2020-02)
lên 207 s (2020-03) rồi 372 s (2020-04), độ lệch dự đoán từ +65 s lên +341 s. Drift của `trip_distance` gần như không
thấy (PSI 0.005 ở 2020-03, 0.016 ở 2020-04); tín hiệu sớm nằm ở phân phối giờ đón (PSI 0.177 ở 2020-04) và ở nhãn khi
nhãn về. Quyết định tại as_of 2020-04 là train lại; challenger train trên tháng 3 giảm MAE tháng 4 từ 372 s xuống 270 s.

## Dòng thời gian

- 2020-02: MAE 181 s, thấp nhất cả giai đoạn; không alert.
- 2020-03 (giữa tháng): lệnh phong toả, lưu lượng giảm mạnh; 20% chuyến cuối tháng bắt đầu từ ngày 12. Dashboard thấy
  trung vị dự đoán đổi ít vì đầu vào gần như giữ nguyên phân phối khoảng cách.
- 2020-04 (đầu tháng): nhãn tháng 3 công bố. Phát lại cho MAE 207 s (+14.3% so với tháng 2), bias +104 s. Thí nghiệm
  train challenger trên đầu tháng 3, đánh giá trên cuối tháng 3: 240.8 s so với 283.6 s của champion. Quyết định
  `retrain` (`reports/decisions/2020-03.yaml`).
- 2020-04 (trong tháng): PSI giờ đón 0.177, `EtaPredictionShift` là alert proxy duy nhất có thể bắn trước khi có nhãn.
- 2020-05 (đầu tháng): nhãn tháng 4 về, champion cũ có MAE 372 s; bản train lại trên tháng 3 cho 270 s trên cùng tháng.

## Nguyên nhân

Concept drift: quan hệ giữa khoảng cách, giờ, cặp zone và thời gian chuyến đổi đột ngột vì giao thông vắng. Feature đầu
vào không đổi nhiều nên giám sát drift theo feature (PSI `trip_distance`) không phát hiện; model không có feature nào
phản ánh tình trạng đường hiện tại. Yếu tố góp phần: nhãn về chậm một tháng, nên chất lượng thật của tháng 3 chỉ đo được
từ đầu tháng 4; quy trình chưa có bước train lại theo tín hiệu chất lượng, chỉ có train tay.

## Tác động

Tháng 4 và 5/2020 mỗi chuyến bị báo dài hơn thực tế khoảng 5 tới 6 phút (bias +341 s và +321 s), sai số tuyệt đối trung
bình gần gấp đôi bình thường (372 s và 362 s so với khoảng 195 s), chuyến sân bay sai trung bình 905 s ở 2020-04. Khách
thấy ETA bi quan, tài xế bị đánh giá sai về thời gian dự kiến. Lưu lượng thấp nên số chuyến bị ảnh hưởng ít hơn bình
thường, nhưng tỉ lệ chuyến sai trên 10 phút tăng mạnh (p90 sai số 807 s).

## Việc cần làm

- Thêm feature phản ánh giao thông gần đây (tốc độ zone/giờ của tuần trước từ Feast, M06) để model tự thích nghi.
- Đưa MAE theo tháng và bias vào dashboard ngay khi nhãn về; alert khi bias vượt 60 s hai tháng liên tiếp.
- Tự động hoá: khi MAE tháng mới xấu hơn 10% so với trung bình 3 tháng, flow CT train challenger trên tháng gần nhất và
  chạy cổng promotion; người on-call duyệt quyết định trong `reports/decisions/`.
- Giữ `EtaPredictionShift` và thêm cảnh báo PSI giờ đón trên log dự đoán hằng ngày làm tín hiệu sớm khi chưa có nhãn.
- Diễn tập rollback và train lại mỗi quý, đo thời gian từ lúc nhãn về tới lúc model mới phục vụ.
