# Lời giải: CLT trên giá trị đơn Olist

Notebook lời giải: `clt.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Hiểu dữ liệu

96 470 đơn giao xong: mean 159.83 BRL, median 105.28, max 13 664, skewness 9.37. 1% đơn lớn nhất chiếm
10.4% doanh thu. Trung bình chạy (LLN) dao động mạnh trong vài trăm đơn đầu, mỗi lần gặp một đơn
lớn lại nhảy lên; sau vài nghìn đơn mới ổn định quanh 159.83. LLN đúng, nhưng "đủ lớn" phụ thuộc vào
đuôi.

## Vector hoá

Một ma trận chỉ số `n_sims × n` thay cho vòng lặp Python: 2 000 mẫu × 2 000 phần tử là 4 triệu số,
tính trong một phần giây. Dùng `rng.integers` trên chỉ số thay vì `rng.choice(x, ...)` để cùng một
cách lấy mẫu dùng được cho mọi hàm và dễ tái lập.

## Kết quả coverage của khoảng t 95% (4 000 lần mô phỏng, seed 0)

| n | 5 | 30 | 100 | 500 | 2000 |
| --- | --- | --- | --- | --- | --- |
| coverage | 81.1% | 83.8% | 88.6% | 92.8% | 94.4% |

`min_n_for_coverage(value, [5, 10, 30, 100, 300, 1000, 3000])` trả 1000; trên `log(value)` trả 5.

## Vì sao khoảng t hụt, và hụt về phía nào

Ở mẫu nhỏ, trung bình mẫu và độ lệch chuẩn mẫu tương quan dương: mẫu nào "trúng" một đơn lớn thì có
mean cao **và** s lớn (khoảng rộng, vẫn chứa μ); mẫu không có đơn lớn có mean thấp **và** s nhỏ
(khoảng hẹp, nằm dưới μ). Kết quả: 57% trung bình mẫu n = 30 nằm dưới μ, và gần như mọi lần trượt
đều trượt về phía dưới. Báo cáo "doanh thu trung bình mỗi đơn" từ mẫu nhỏ sẽ **thường xuyên đánh
giá thấp**.

## Khi nào dùng gì

| Tình huống | Cách làm |
| --- | --- |
| Hàng nghìn quan sát mỗi nhóm, đuôi vừa phải | CI t / Welch t-test như bình thường |
| Mẫu nhỏ, metric lệch | Bootstrap (kiểm tra lại cả bootstrap bằng mô phỏng), hoặc báo cáo median |
| Quan tâm "đơn điển hình" | Phân tích trên log, nói rõ là trung bình hình học |
| Có "cá voi" | Winsorize ở p99.9 (ghi rõ), hoặc tách metric: tỉ lệ có mua × giá trị khi mua |

## Rubric cho phần kết luận

| Tiêu chí | Đạt khi |
| --- | --- |
| Định lượng | Nói được coverage thật ở n = 30 và n cần để đạt mức chấp nhận được |
| Cơ chế | Giải thích bằng skewness / đơn lớn, không chỉ "dữ liệu không chuẩn" |
| Hành động | Đề xuất cách làm cho mẫu nhỏ |
| Liên hệ | Nói được vì sao A/B test cỡ lớn vẫn dùng t-test |
