# Lời giải: xác suất từ Binomial, Poisson và Lognormal

## Binomial: seller có tệ bất thường không?

Với p = 8.1% (tỉ lệ giao trễ thật trên đơn giao xong của Olist) và n = 20 đơn:

| Câu hỏi | Kết quả |
| --- | --- |
| P(không đơn nào trễ) | 0.185 |
| P(ít nhất 3 đơn trễ) | 0.217 |

Một seller có 3/20 đơn trễ (15%, gần gấp đôi trung bình) vẫn xảy ra với 1/5 seller **hoàn toàn bình
thường**. Đây là lý do không xếp hạng seller theo tỉ lệ thô khi có ít đơn: bài Intermediate 03 dùng
Beta-Binomial để xử lý. Giả định ẩn: các đơn độc lập và cùng p. Trong thực tế đơn của cùng một seller
trong cùng tuần thường trễ cùng nhau (một chuyến xe hỏng), nên phân phối thật còn phân tán hơn
Binomial.

`prob_at_least` cộng trực tiếp phần đuôi thay vì `1 − cdf`: khi kết quả rất nhỏ (1e-12), phép trừ
`1 − 0.999999999999` mất gần hết chữ số có nghĩa.

## Poisson: làm trên log

`250**300` vượt `1.8e308` (giới hạn float64) và `300!` cũng vậy, nhưng tỉ số của chúng là một số
bình thường. Tính `k log λ − λ − log k!` rồi mới `exp`. Đây là thói quen chung: likelihood, xác suất
của chuỗi dài, softmax đều tính trên log.

## Lognormal từ mean và median

`mu = log(median)`, `sigma = sqrt(2 (log(mean) − mu))`. Với giá trị đơn Olist (mean 159.83, median
105.28): `mu ≈ 4.657`, `sigma ≈ 0.914`. MLE trên log giá trị đơn thật (bài Basic 02) cho
`mu ≈ 4.691`, `sigma ≈ 0.808`. Hai cách khác nhau vì dữ liệu không đúng Lognormal: đuôi phải nặng hơn
Lognormal với sigma 0.808, nên mean bị kéo lên và cách khớp-mean phải tăng sigma. Bài học: "khớp hai
moment" và "khớp likelihood" cho cùng một họ phân phối có thể cho tham số khác nhau, và chênh lệch đó
là tín hiệu mô hình chưa đúng.

## Overdispersion trên số đơn mỗi giờ

Số đơn giao xong theo giờ mua trong tháng 3/2018: mean 9.41, variance 51.08, dispersion index ≈ 5.4.
Poisson(9.41) dự đoán giờ có ít nhất 20 đơn chiếm 0.18%; thực tế là 7.4%. Lý do: λ không cố định,
ban ngày đông, 3 giờ sáng gần như không có đơn. Hỗn hợp nhiều Poisson với λ khác nhau luôn có
variance lớn hơn mean. Cách xử lý: mô hình λ theo giờ trong ngày, ngày trong tuần (Poisson regression),
hoặc dùng Negative Binomial. Dùng Poisson thẳng để đặt ngưỡng cảnh báo "lượng đơn bất thường" sẽ báo
động liên tục.
