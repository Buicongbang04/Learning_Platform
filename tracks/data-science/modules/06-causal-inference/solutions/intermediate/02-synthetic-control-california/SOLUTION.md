# Lời giải: synthetic control cho California

Notebook lời giải: `synth.ipynb` (chạy được toàn bộ khi đã tải `prop99`).

## Trọng số bằng NNLS có ràng buộc tổng

Bài toán là least squares với $$w \ge 0$$ và $$\sum_j w_j = 1$$. Nối thêm vào ma trận donor một
dòng toàn số M rất lớn và vào vector đích một phần tử M: phần dư của dòng này là
$$M (1 - \sum_j w_j)$$, nên NNLS buộc phải giữ tổng gần như đúng 1. Cách này dùng solver active-set
chính xác của `nnls`, không phụ thuộc điểm xuất phát.

Với SLSQP: trong lúc chuẩn bị bài, một cấu hình SLSQP (có truyền gradient, `ftol` rất nhỏ) dừng ở
nghiệm có RMSPE trước 16.0 thay vì 1.66 cho chính California, không cảnh báo gì. Đây là lỗi im lặng
nguy hiểm nhất của synthetic control tự viết. Test kiểm RMSPE trước để bắt nó.

## Kết quả

| | Giá trị |
| --- | --- |
| Donor (trọng số) | Utah 0.394, Montana 0.232, Nevada 0.205, Connecticut 0.109, New Hampshire 0.045, Colorado 0.015 |
| RMSPE 1970–1988 | 1.66 bao/người |
| Gap 1989 / 1995 / 2000 | −8.4 / −22.9 / −26.6 |
| Gap trung bình 1989–2000 | −19.5 |
| Tỉ số RMSPE sau/trước | 12.4, hạng 3/39 (p = 0.077) |
| DiD với trung bình 38 bang (Basic 02) | −27.3 |

Synthetic control cho tác động nhỏ hơn DiD vì nhóm so sánh của nó đã có xu hướng giảm giống
California trước 1989; DiD gán cả xu hướng đó cho chính sách.

## Đọc kết quả placebo

Missouri (23.9) và Virginia (19.8) có tỉ số cao hơn California. Cả hai khớp trước can thiệp cực sát
(RMSPE trước 0.44 và 0.82), nên mẫu số nhỏ thổi tỉ số lên. Theo bài báo gốc (Abadie et al. 2010),
khi khớp thêm covariate (giá bán lẻ, thu nhập, tỉ lệ dân 15–24 tuổi, tiêu thụ bia, cigsale ở vài năm
chọn lọc) thì California hạng 1/39; lời giải này không chạy lại đặc tả đó. Hai bài học:

1. Với J + 1 đơn vị, p-value hoán vị nhỏ nhất có thể là 1/(J + 1). 39 bang thì không bao giờ
   xuống dưới 0.026: "có ý nghĩa" ở đây là một phát biểu về thứ hạng.
2. Đặc tả (khớp gì, donor nào) là quyết định của người phân tích và có thể đổi kết luận biên. Ghi
   lại và báo cáo trước khi nhìn kết quả sau can thiệp.

## Kiểm tra độ bền (cell explore)

- Leave-one-out: bỏ lần lượt Utah, Montana, Nevada, Connecticut, gap năm 2000 nằm trong khoảng
  −24.9 tới −28.4. Không donor đơn lẻ nào quyết định kết quả.
- Placebo theo thời gian: giả vờ can thiệp năm 1980 (khớp 1970–1979), gap trung bình 1980–1988 là
  −3.4, nhỏ so với −19.5 sau Prop 99.

## Khi nào dùng, khi nào không

| Dùng | Không dùng |
| --- | --- |
| Một hoặc vài đơn vị treated, nhiều đơn vị donor, chuỗi trước can thiệp dài | Pre-period ngắn: khớp tốt nhờ may, không nhờ giống nhau |
| Can thiệp ở cấp tổng hợp (bang, thành phố, thị trường, kho hàng) | Đơn vị treated nằm ngoài bao lồi của donor (lớn nhất, cực đoan nhất) |
| Không có nhóm so sánh tự nhiên | Donor cũng bị ảnh hưởng (spillover: thuốc lá mua lậu từ Nevada) |

Biến thể đáng biết: synthetic DiD (Arkhangelsky et al. 2021), augmented synthetic control
(Ben-Michael et al. 2021) khi khớp trước không hoàn hảo, và CausalImpact (Bayesian structural time
series) mà nhiều công ty dùng cho đo lường marketing theo vùng.

## Rubric cho phần kết luận

| Tiêu chí | Đạt khi |
| --- | --- |
| Tác động | Nêu gap 2000 và gap trung bình, có đơn vị |
| Độ khớp | Nhắc RMSPE trước và vì sao nó quan trọng |
| Placebo | Diễn giải đúng hạng và p-value hoán vị, nêu giới hạn 1/39 |
| So sánh DiD | Giải thích vì sao khác con số DiD |
